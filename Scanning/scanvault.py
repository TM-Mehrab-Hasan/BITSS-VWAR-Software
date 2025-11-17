import os
import shutil
import json
import hashlib
import time
from typing import Tuple
from datetime import datetime

from config import SCANVAULT_FOLDER, MAX_CAPTURES_PER_SECOND, MAX_BURST_CAPTURES, BURST_WINDOW_SECONDS
from utils.logger import log_message, telemetry_inc
from utils.scanvault_logger import log_capture, log_duplicate, log_rate_limit
from utils.installation_detector import get_installation_detector


_recent_signatures: dict[str, float] = {}
_recent_captures: dict[str, float] = {}  # Track paths to prevent multiple captures of same file
_SIGNATURE_TTL = 15.0  # seconds window to treat repeated captures as duplicates

# 🛡️ Brute Force Attack Protection: Rate Limiting
_capture_timestamps = []  # Track all capture timestamps for rate limiting
_last_rate_limit_warning = 0  # Last time we logged a rate limit warning

def clear_file_signature(file_path: str):
    """✅ Clear file signature from duplicate tracking after restoration.
    
    This allows the same file to be re-vaulted if copied/modified again.
    NOTE: Only clears signature, NOT path - path stays blocked for 15s to prevent monitor re-captures.
    """
    try:
        sig = _make_signature(file_path)
        
        if sig in _recent_signatures:
            _recent_signatures.pop(sig, None)
            log_message(f"[SCANVAULT] Cleared signature for re-vaulting: {os.path.basename(file_path)}")
        
        # DON'T clear path from _recent_captures - that prevents immediate re-capture by monitor!
        # Path will auto-expire after 15 seconds via normal cleanup
            
    except Exception:
        pass  # File may no longer exist, which is fine

def _first64k_hash(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            chunk = f.read(65536)
        h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return "0" * 16

def _make_signature(path: str) -> str:
    """Generate a richer signature to distinguish rapid repeat downloads.

    Components:
      - file size
      - high resolution mtime (ns if available)
      - first 64KB content hash (prefix)
      - stable path hash (lowercased absolute path)
    """
    try:
        st = os.stat(path)
        size = st.st_size
        # Use nanosecond mtime if available for better granularity
        mtime_ns = getattr(st, 'st_mtime_ns', int(st.st_mtime * 1e9))
    except Exception:
        size = -1
        mtime_ns = 0
    path_norm = os.path.abspath(path).replace("\\", "/").lower()
    path_hash = hashlib.sha256(path_norm.encode()).hexdigest()[:12]
    head_hash = _first64k_hash(path)
    raw = f"{size}|{mtime_ns}|{head_hash}|{path_hash}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]

def vault_capture_file(file_path: str, event: str | None = None) -> Tuple[str, str]:
    """
    Move a new/changed file into the ScanVault folder and write a .meta file.

    Returns (vaulted_path, meta_path).
    Raises RuntimeError on failure.
    """
    global _capture_timestamps, _last_rate_limit_warning
    
    if not os.path.exists(file_path):
        raise RuntimeError(f"File no longer exists: {file_path}")
    
    # 🛡️ BRUTE FORCE PROTECTION: Rate limiting check
    current_time = time.time()
    
    # Clean up old timestamps
    _capture_timestamps = [ts for ts in _capture_timestamps if current_time - ts < BURST_WINDOW_SECONDS]
    
    # Check per-second rate limit - retry with backoff instead of dropping
    recent_captures_1s = len([ts for ts in _capture_timestamps if current_time - ts < 1.0])
    retry_count = 0
    while MAX_CAPTURES_PER_SECOND > 0 and recent_captures_1s >= MAX_CAPTURES_PER_SECOND:
        if retry_count == 0 and current_time - _last_rate_limit_warning > 5:
            log_message(f"[SCANVAULT] ⚠️ BRUTE FORCE PROTECTION: Rate limit ({recent_captures_1s}/sec). Waiting for capacity...")
            log_rate_limit("CAPTURE_RATE", recent_captures_1s, MAX_CAPTURES_PER_SECOND)
            telemetry_inc('capture_rate_limited')
            _last_rate_limit_warning = current_time
        
        # Retry with exponential backoff (0.1s, 0.2s, 0.4s, 0.8s, max 1.5s)
        backoff = min(0.1 * (2 ** retry_count), 1.5)
        time.sleep(backoff)
        
        # Re-check after backoff
        current_time = time.time()
        _capture_timestamps = [ts for ts in _capture_timestamps if current_time - ts < BURST_WINDOW_SECONDS]
        recent_captures_1s = len([ts for ts in _capture_timestamps if current_time - ts < 1.0])
        retry_count += 1
        
        # Max 10 retries (total ~6s delay), then proceed anyway (file already in vault)
        if retry_count >= 10:
            log_message(f"[SCANVAULT] Rate limit retry timeout after {retry_count} attempts. Proceeding with vaulted file.")
            break  # ✅ Exit loop and continue - file is already vaulted, just delayed
    
    # Check burst protection (sustained attack detection)
    burst_captures = len(_capture_timestamps)
    if burst_captures >= MAX_BURST_CAPTURES:
        if current_time - _last_rate_limit_warning > 5:
            log_message(f"[SCANVAULT] ⚠️ BURST LIMIT REACHED: {burst_captures} captures in {BURST_WINDOW_SECONDS}s. Continuing with backlog.")
            log_rate_limit("BURST_ATTACK", burst_captures, MAX_BURST_CAPTURES)
            telemetry_inc('burst_attack_blocked')
            _last_rate_limit_warning = current_time
        # ✅ Don't raise exception - just log warning and continue (file will be vaulted and queued)
        time.sleep(0.5)  # Brief delay to slow down processing
    
    # Record this capture
    _capture_timestamps.append(current_time)
    
    # 🔧 CHECK INSTALLATION MODE: If installer is running, don't vault - add directly to queue for in-place scanning
    detector = get_installation_detector()
    if detector.is_file_being_installed(file_path):
        # File is part of an active installation - don't move it, just queue for in-place scanning
        log_message(f"[SCANVAULT] 🔧 Installation active - queuing for in-place scan: {os.path.basename(file_path)}")
        
        # Add directly to queue without vaulting
        from utils.scanvault_queue import add_to_queue
        try:
            add_to_queue(file_path)
            telemetry_inc('installation_mode_queued')
            raise RuntimeError(f"Installation mode: File queued for in-place scanning")
        except Exception as queue_error:
            raise RuntimeError(f"Installation mode queue: {queue_error}")

    os.makedirs(SCANVAULT_FOLDER, exist_ok=True)

    try:
        # Dedupe check using enhanced signature AND path
        sig = _make_signature(file_path)
        normalized_path = os.path.abspath(file_path).replace("\\", "/").lower()
        now = time.time()
        # Purge expired signatures and paths
        expired = [k for k, t in _recent_signatures.items() if now - t > _SIGNATURE_TTL]
        for k in expired:
            _recent_signatures.pop(k, None)
        expired_paths = [k for k, t in _recent_captures.items() if now - t > _SIGNATURE_TTL]
        for k in expired_paths:
            _recent_captures.pop(k, None)
        
        if sig in _recent_signatures or normalized_path in _recent_captures:
            # Instead of silent suppression, create a visible history meta entry
            os.makedirs(SCANVAULT_FOLDER, exist_ok=True)
            history_dir = os.path.join(SCANVAULT_FOLDER, 'history')
            os.makedirs(history_dir, exist_ok=True)
            timestamp_raw = datetime.now()
            timestamp_human = timestamp_raw.strftime("%Y-%m-%d %H:%M:%S")
            base_name = os.path.basename(file_path)
            meta_stub = f"duplicate__{sig[:12]}__{timestamp_raw.strftime('%Y%m%d%H%M%S')}.meta"
            history_meta = os.path.join(history_dir, meta_stub)
            try:
                meta = {
                    "original_path": os.path.abspath(file_path).replace('\\', '/'),
                    "timestamp": timestamp_human,
                    "final_status": "DUPLICATE_SUPPRESSED",
                    "signature": sig,
                    "file_name": base_name,
                    "event": event or "created"
                }
                with open(history_meta, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, indent=4)
                log_message(f"[SCANVAULT] Duplicate suppressed (visible) sig={sig} path={file_path}")
                log_duplicate(file_path, sig)
                try:
                    telemetry_inc("duplicate_suppressed")
                except Exception:
                    pass
            except Exception as de:
                log_message(f"[SCANVAULT] Failed to write duplicate meta: {de}")
            raise RuntimeError(f"Duplicate capture suppressed for signature {sig}")

        file_name = os.path.basename(file_path)
        timestamp_raw = datetime.now()
        timestamp_file = timestamp_raw.strftime("%Y%m%d%H%M%S")
        timestamp_human = timestamp_raw.strftime("%Y-%m-%d %H:%M:%S")
        # Normalize path before hashing for stability across dev/EXE
        normalized_path_for_hash = os.path.abspath(file_path).replace("\\", "/")
        path_hash = hashlib.sha256(normalized_path_for_hash.encode()).hexdigest()[:16]

        vaulted_filename = f"{file_name}__{timestamp_file}__{path_hash}.vaulted"
        vaulted_path = os.path.join(SCANVAULT_FOLDER, vaulted_filename)

        # Extended retry logic with backoff to handle transient locks (WinError 32)
        attempts = 10
        delay = 0.15
        last_err = None
        for attempt in range(1, attempts + 1):
            if not os.path.exists(file_path):
                time.sleep(0.1)
                continue
            try:
                shutil.move(file_path, vaulted_path)
                last_err = None
                break
            except Exception as e:
                last_err = e
                time.sleep(delay)
                delay = min(delay * 1.5, 1.2)
        if last_err is not None:
            raise RuntimeError(f"Move failed after {attempts} attempts: {last_err}")

        if os.path.exists(vaulted_path):
            meta_path = vaulted_path + ".meta"
            normalized_path = os.path.abspath(file_path).replace("\\", "/")
            metadata = {
                "original_path": normalized_path,
                "vaulted_path": vaulted_path,
                "timestamp": timestamp_human,
                "event": (event or "created"),
                "signature": sig,
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
            _recent_signatures[sig] = now
            _recent_captures[normalized_path] = now
            log_message(f"[SCANVAULT] {file_path} → {vaulted_path}")
            
            # Log to dedicated ScanVault log
            log_capture(file_path, vaulted_path, event_type=(event or "created"), success=True)
            
            try:
                telemetry_inc("stabilized_capture")
            except Exception:
                pass
            return vaulted_path, meta_path
        else:
            raise RuntimeError(f"Vaulted file unexpectedly missing: {vaulted_path}")

    except Exception as e:
        raise RuntimeError(f"Failed to vault {file_path}: {e}")
