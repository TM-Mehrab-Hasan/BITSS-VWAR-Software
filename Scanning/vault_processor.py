import os
import re
import json
import time
import threading
import shutil
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime
from config import (SCANVAULT_FOLDER, QUARANTINE_FOLDER, POST_RESTORE_RECHECK_DELAY, 
                    SCANVAULT_MODE, MAX_RESTORES_PER_MINUTE)
from Scanning.scanner_core import scan_file_for_realtime, force_scan_vaulted
from Scanning.quarantine import quarantine_file
from utils.logger import log_message, telemetry_inc
from utils.notify import notify
from utils.scanvault_logger import (
    log_scan, log_restore, log_quarantine, log_rate_limit, 
    log_mode_switch, log_error, get_scanvault_logger
)
from utils.scanvault_queue import get_next_pending, mark_processing, mark_completed
from Scanning.scanvault import vault_capture_file
from utils.installation_detector import get_installation_detector

class ScanVaultProcessor:
    """Background processor for ScanVault files using queue-based sequential processing."""
    
    def __init__(self, monitor_page_ref=None, max_workers=6):
        self.monitor_page = monitor_page_ref
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Queue-based system: ALWAYS sequential (PERFECT mode)
        self._scanning_mode = "PERFECT"
        log_message("[SCANVAULT] Mode: PERFECT (queue-based sequential processing)")
        
        self._notified_files = set()  # Track files we've already notified about to prevent duplicates
        self._recently_restored = {}  # 🔒 Track recently restored files: {path: timestamp} to prevent race condition
        self._restore_exclusion_seconds = 180  # 🔒 Exclude restored files from recapture for 180 seconds (3 minutes)
        
        # 🛡️ Brute Force Attack Protection
        self._restoration_timestamps = []  # Track restoration times for rate limiting
        
    def start(self):
        """Start the background queue processor thread."""
        if self._running:
            return
        
        # Ensure YARA rules are loaded before starting (reload from local storage only)
        from Scanning import scanner_core
        if not scanner_core.rules:
            print("[SCANVAULT] Scanner not ready. Loading threat signatures from local storage...")
            success, count = scanner_core.reload_yara_rules()
            if not success:
                print("[SCANVAULT WARNING] No threat signatures found. Files will be vaulted but not scanned until signatures are available.")
        
        # 🔧 Start installation detector
        try:
            detector = get_installation_detector()
            detector.start_monitoring()
            log_message("[SCANVAULT] Installation detector started")
        except Exception as e:
            log_message(f"[SCANVAULT] Failed to start installation detector: {e}")
        
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        
        log_message("[SCANVAULT] Queue-based processor started (PERFECT mode - sequential processing)")
        
        # ✅ AUTO-RECOVER: Scan any existing vaulted files that weren't processed (from crashes, rate limits, etc.)
        self._auto_recover_vaulted_files()
        
    def stop(self):
        """Stop the background queue processor thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        log_message("[SCANVAULT] Queue-based processor stopped")
        
    def _auto_recover_vaulted_files(self):
        """Auto-enqueue any files already in ScanVault on startup (queue-based)."""
        try:
            from utils.scanvault_queue import add_to_queue
            
            if not os.path.exists(SCANVAULT_FOLDER):
                return
            
            vaulted_files = [f for f in os.listdir(SCANVAULT_FOLDER) 
                           if f.endswith('.vaulted') and not f.endswith('.vaulted.meta')]
            
            if not vaulted_files:
                return
            
            log_message(f"[SCANVAULT] Auto-recovery: Found {len(vaulted_files)} files in vault")
            
            # Add each to queue for processing
            for vaulted_filename in vaulted_files:
                vaulted_path = os.path.join(SCANVAULT_FOLDER, vaulted_filename)
                
                # Read original path from metadata
                meta_path = vaulted_path + '.meta'
                if not os.path.exists(meta_path):
                    continue
                
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    
                    original_path = meta.get('original_path')
                    if original_path:
                        add_to_queue(vaulted_path, event_type="recovery")
                        log_message(f"[SCANVAULT] Added to queue: {os.path.basename(vaulted_path)}")
                    
                except Exception as e:
                    log_message(f"[SCANVAULT] Failed to read metadata for {vaulted_filename}: {e}")
            
            log_message(f"[SCANVAULT] Auto-recovery: Added {len(vaulted_files)} files to queue")
        except Exception as e:
            log_message(f"[SCANVAULT] Auto-recovery error: {e}")
    
    # NOTE: Old enqueue_for_scan method deprecated - queue-based system handles this now
    # Monitor adds files to queue file, processor reads from queue file
    # def enqueue_for_scan(self, vaulted_path: str, meta_path: str):
    #     """Add a vaulted file to the scan queue."""
    #     # This method is no longer used - queue file system handles everything
        
    def _process_loop(self):
        """
        Main processing loop - reads from queue file and processes one file at a time.
        
        Queue-based system eliminates race conditions from file system events.
        Flow: Monitor adds to queue → Processor captures → Scans → Restores → Next file
        """
        log_message("[SCANVAULT] 🚀 Queue processor started (PERFECT mode - sequential processing)")
        last_cleanup = time.time()
        
        while self._running:
            try:
                # Periodically clear notification tracking and restored paths
                current_time = time.time()
                if current_time - last_cleanup > 300:  # 5 minutes
                    self._notified_files.clear()
                    # 🔒 Clean up expired restored paths (older than exclusion window)
                    expired_restored = [path for path, ts in self._recently_restored.items() 
                                       if current_time - ts > self._restore_exclusion_seconds]
                    for path in expired_restored:
                        self._recently_restored.pop(path, None)
                    last_cleanup = current_time
                    log_message("[SCANVAULT] Cleared notification tracking cache")
                
                # Get next pending file from queue
                queue_item = get_next_pending()
                
                if queue_item is None:
                    # Queue empty - sleep and check again
                    time.sleep(0.5)
                    continue
                
                # Extract file info
                original_path = queue_item.get("original_path")
                event_type = queue_item.get("event_type", "created")
                
                log_message(f"[SCANVAULT] 📂 Processing from queue: {os.path.basename(original_path)}")
                
                # Mark as processing
                mark_processing(original_path)
                
                # Special handling for already-vaulted files (auto-recovery)
                if event_type == "recovery" and original_path.endswith('.vaulted'):
                    # File is already in vault - skip capture, go directly to scan
                    vaulted_path = original_path
                    meta_path = vaulted_path + '.meta'
                    
                    if not os.path.exists(vaulted_path) or not os.path.exists(meta_path):
                        log_message(f"[SCANVAULT] ⚠️ Vaulted file missing: {vaulted_path}")
                        mark_completed(original_path, success=False, result="Vaulted file missing")
                        continue
                    
                    log_message(f"[SCANVAULT] 🔄 Auto-recovery: Scanning vaulted file {os.path.basename(vaulted_path)}")
                    
                    # Directly scan and route
                    try:
                        self._scan_and_route_file(vaulted_path, meta_path)
                        mark_completed(original_path, success=True, result="Auto-recovery successful")
                    except Exception as e:
                        log_message(f"[SCANVAULT] ❌ Auto-recovery scan error: {e}")
                        mark_completed(original_path, success=False, result=f"Scan exception: {e}")
                    
                    time.sleep(0.1)
                    continue
                
                # Normal flow: Check if original file still exists
                if not os.path.exists(original_path):
                    log_message(f"[SCANVAULT] ⚠️ File no longer exists (deleted before processing): {original_path}")
                    mark_completed(original_path, success=False, result="File deleted before processing")
                    continue
                
                # 🔒 Check race condition (recently restored)
                if self.is_recently_restored(original_path):
                    log_message(f"[SCANVAULT] Skipping recently restored file: {os.path.basename(original_path)}")
                    mark_completed(original_path, success=False, result="Recently restored (race condition)")
                    continue
                
                # 🔧 Check if file is being installed (automatic installation mode)
                detector = get_installation_detector()
                is_installation = detector.is_file_being_installed(original_path)
                
                if is_installation:
                    active_installers = detector.get_active_installers()
                    installer_names = [inst['name'] for inst in active_installers]
                    log_message(f"[SCANVAULT] 🔧 Installation detected: {', '.join(installer_names)} - Scanning in-place")
                
                # 🔍 SCAN DIRECTLY: Scan file in original location (no vaulting)
                try:
                    log_message(f"[SCANVAULT] 🔍 Scanning file: {os.path.basename(original_path)}")
                    
                    # Import scan function
                    from Scanning.scanner_core import scan_file_for_realtime
                    
                    # Scan the file in its original location
                    scan_start_time = time.time()
                    result = scan_file_for_realtime(original_path)
                    scan_time_ms = int((time.time() - scan_start_time) * 1000)
                    
                    matched, rule, quarantine_path, meta_path = result[:4]
                    status = getattr(result, 'status', 'UNKNOWN')
                    
                    if matched and status == "MATCH":
                        # Malware detected and quarantined
                        log_message(f"[SCANVAULT] 🦠 THREAT QUARANTINED: {os.path.basename(original_path)} - Rule: {rule}")
                        log_scan(original_path, "THREAT", rule, scan_time_ms)
                        log_quarantine(original_path, quarantine_path, rule)
                        
                        # Log to installation.log if during installation
                        if is_installation:
                            detector.log_installation_scan(original_path, "THREAT", rule, scan_time_ms)
                            detector.log_installation_quarantine(original_path, quarantine_path, rule)
                        
                        # Update quarantine UI
                        if self.monitor_page and hasattr(self.monitor_page, 'add_to_quarantine_listbox'):
                            self.monitor_page.add_to_quarantine_listbox(original_path, meta_path, [rule])
                        
                        # Send notification
                        if original_path not in self._notified_files:
                            self._notified_files.add(original_path)
                            try:
                                file_name = os.path.basename(original_path)
                                install_msg = " (during installation)" if is_installation else ""
                                notify("🛡️ ScanVault: Threat Quarantined", f"Rule: {rule}\nFile: {file_name}{install_msg}")
                            except Exception:
                                pass
                        
                        mark_completed(original_path, success=True, result=f"QUARANTINED: {rule}")
                        
                    elif status == "CLEAN":
                        # File is clean - leave it where it is (Downloads or installation folder)
                        log_message(f"[SCANVAULT] ✅ CLEAN: {os.path.basename(original_path)}")
                        log_scan(original_path, "CLEAN", scan_time_ms=scan_time_ms)
                        
                        # Log to installation.log if during installation
                        if is_installation:
                            detector.log_installation_scan(original_path, "CLEAN", scan_time_ms=scan_time_ms)
                        
                        # Add to scan history for UI display
                        try:
                            history_dir = os.path.join(SCANVAULT_FOLDER, "history")
                            os.makedirs(history_dir, exist_ok=True)
                            
                            # Create a history entry (no vault file, just metadata)
                            timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            file_hash = hashlib.sha256(original_path.encode()).hexdigest()[:16]
                            history_meta_name = f"{os.path.basename(original_path)}__clean__{file_hash}.meta"
                            history_meta_path = os.path.join(history_dir, history_meta_name)
                            
                            history_data = {
                                'original_path': original_path,
                                'file_name': os.path.basename(original_path),
                                'timestamp': timestamp_str,
                                'final_status': 'CLEAN',
                                'scan_time_ms': scan_time_ms,
                                'action_timestamp': timestamp_str,
                                'installation_mode': is_installation
                            }
                            
                            with open(history_meta_path, 'w', encoding='utf-8') as f:
                                json.dump(history_data, f, indent=4)
                            
                            # Update UI to show scan history
                            self._schedule_ui_update(lambda: getattr(self.monitor_page, 'update_scanvault_listbox', lambda: None)())
                        except Exception as e:
                            log_message(f"[SCANVAULT] Failed to create history entry: {e}")
                        
                        # Send notification for clean file
                        if original_path not in self._notified_files:
                            self._notified_files.add(original_path)
                            try:
                                file_name = os.path.basename(original_path)
                                install_msg = " (during installation)" if is_installation else ""
                                notify("✅ File Scanned: Safe", f"File: {file_name}\nStatus: Clean - No threats detected{install_msg}")
                            except Exception:
                                pass
                        
                        mark_completed(original_path, success=True, result="CLEAN")
                        
                    else:
                        # Skipped or error
                        log_message(f"[SCANVAULT] ⚠️ {status}: {os.path.basename(original_path)}")
                        log_scan(original_path, status, scan_time_ms=scan_time_ms)
                        mark_completed(original_path, success=True, result=status)
                    
                except Exception as e:
                    log_message(f"[SCANVAULT] ❌ Scan error: {e}")
                    mark_completed(original_path, success=False, result=f"Scan exception: {e}")
                
                # Small delay between files (sequential processing)
                time.sleep(0.1)
                
            except Exception as e:
                log_message(f"[SCANVAULT] ❌ Loop error: {e}")
                time.sleep(1)
        
        log_message("[SCANVAULT] 🛑 Queue processor stopped")
    
    # Old ThreadPoolExecutor method - no longer needed with queue-based system
    # def _check_completed_futures(self, futures):
    #     """Remove completed futures from list."""
    #     # Queue-based system doesn't use futures
    
    def _scan_and_route_file(self, vaulted_path: str, meta_path: str):
        """Scan a vaulted file and route it to quarantine or restore (sequential processing)."""
        try:
            # Load metadata to get original path
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                original_path = metadata.get('original_path')
                if not original_path:
                    log_message(f"[SCANVAULT] No original path in metadata: {meta_path}")
                    return
            except Exception as e:
                log_message(f"[SCANVAULT] Failed to read metadata {meta_path}: {e}")
                return
                
            # Scan the vaulted file
            log_message(f"[SCANVAULT] Scanning: {vaulted_path}")
            # Use forced scan to avoid INTERNAL exclusion regression
            scan_start_time = time.time()
            result = force_scan_vaulted(vaulted_path)
            scan_time_ms = int((time.time() - scan_start_time) * 1000)
            
            matched, rule, _, _ = result[:4]
            status = getattr(result, 'status', 'UNKNOWN')
            
            # Log scan result to dedicated ScanVault log
            if matched:
                log_scan(vaulted_path, "THREAT", rule, scan_time_ms)
            else:
                log_scan(vaulted_path, status, scan_time_ms=scan_time_ms)
            
            # Prepare history directory for metadata archive
            history_dir = os.path.join(SCANVAULT_FOLDER, "history")
            os.makedirs(history_dir, exist_ok=True)

            if matched:
                # Malware detected - move to quarantine
                try:
                    log_message(f"[SCANVAULT] 🦠 THREAT DETECTED: {os.path.basename(vaulted_path)} - Rule: {rule}")
                    quarantine_path = quarantine_file(vaulted_path, matched_rules=[rule])
                    
                    if not quarantine_path or not os.path.exists(quarantine_path):
                        raise RuntimeError(f"Quarantine failed - file not moved: {quarantine_path}")
                    
                    # Log to dedicated ScanVault log
                    log_quarantine(vaulted_path, quarantine_path, rule)
                    log_message(f"[SCANVAULT] ✅ Quarantined: {os.path.basename(vaulted_path)} → {os.path.basename(quarantine_path)}")
                    
                    # Archive vault metadata into history with status
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                        except Exception:
                            meta = {}
                        meta.update({
                            'final_status': 'QUARANTINED',
                            'action_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'quarantine_path': quarantine_path,
                            'matched_rule': rule,
                        })
                        # Move to history directory
                        base = os.path.basename(meta_path)
                        history_meta = os.path.join(history_dir, base)
                        try:
                            with open(history_meta, 'w', encoding='utf-8') as f:
                                json.dump(meta, f, indent=4)
                        except Exception as e:
                            log_message(f"[SCANVAULT] Failed to write history meta: {e}")
                        try:
                            os.remove(meta_path)
                        except Exception:
                            pass
                    
                    # Send notification only once per original file
                    if original_path not in self._notified_files:
                        self._notified_files.add(original_path)
                        try:
                            file_name = os.path.basename(original_path)
                            notify("🛡️ ScanVault: Threat Quarantined", f"Rule: {rule}\nFile: {file_name}")
                        except Exception:
                            pass
                    
                    # Update UI
                    if self.monitor_page and hasattr(self.monitor_page, 'add_to_quarantine_listbox'):
                        quarantine_meta = quarantine_path + ".meta"
                        self.monitor_page.add_to_quarantine_listbox(original_path, quarantine_meta, [rule])
                    # Refresh vault UI (history now updated)
                    self._schedule_ui_update(lambda: getattr(self.monitor_page, 'refresh_scanvault_table', self.monitor_page.update_scanvault_listbox)())
                    
                except Exception as e:
                    log_message(f"[SCANVAULT] ❌ Quarantine FAILED for {os.path.basename(vaulted_path)}: {e}")
                    log_error("QUARANTINE_FAILED", vaulted_path, str(e))
                    # Leave file in vault for manual review
                    
            elif status in ('CLEAN', 'SKIPPED_INTERNAL', 'SKIPPED_TEMP', 'SKIPPED_TEMP_ROOT', 'SKIPPED_TEMP_FILE'):
                    # File is clean - restore to original location
                    try:
                        # 🛡️ BRUTE FORCE PROTECTION: Check restoration rate limit
                        current_time = time.time()
                        # Clean up old timestamps (older than 1 minute)
                        self._restoration_timestamps = [ts for ts in self._restoration_timestamps 
                                                       if current_time - ts < 60]
                        
                        if len(self._restoration_timestamps) >= MAX_RESTORES_PER_MINUTE:
                            log_message(f"[SCANVAULT] ⚠️ BRUTE FORCE PROTECTION: Restoration rate limit exceeded ({len(self._restoration_timestamps)}/min). Re-queuing.")
                            log_rate_limit("RESTORE_RATE", len(self._restoration_timestamps), MAX_RESTORES_PER_MINUTE)
                            telemetry_inc('restore_rate_limited')
                            
                            # Re-add to queue with delay
                            time.sleep(2)
                            
                            # Read original path from metadata and re-queue
                            try:
                                with open(meta_path, 'r', encoding='utf-8') as f:
                                    meta_data = json.load(f)
                                original_path = meta_data.get('original_path')
                                
                                if original_path:
                                    from utils.scanvault_queue import add_to_queue
                                    add_to_queue(vaulted_path, event_type="rate_limit_retry")
                            except Exception as e:
                                log_message(f"[SCANVAULT] Failed to re-queue rate limited file: {e}")
                            
                            return
                        
                        # Record this restoration
                        self._restoration_timestamps.append(current_time)
                        
                        # Compute pre-restore hash of the vaulted content
                        pre_hash = self._sha256_file(vaulted_path)
                        # Double-check: run one more scan right before restore to avoid races
                        recheck = force_scan_vaulted(vaulted_path)
                        if getattr(recheck, 'matched', False):
                            # If match now, treat like threat path
                            rule2 = recheck.rule
                            try:
                                quarantine_path = quarantine_file(vaulted_path, matched_rules=[rule2])
                                # Update history meta
                                if os.path.exists(meta_path):
                                    try:
                                        with open(meta_path, 'r', encoding='utf-8') as f:
                                            meta = json.load(f)
                                    except Exception:
                                        meta = {}
                                    meta.update({
                                        'final_status': 'QUARANTINED',
                                        'action_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'quarantine_path': quarantine_path,
                                        'matched_rule': rule2,
                                        'recheck_before_restore': True
                                    })
                                    base = os.path.basename(meta_path)
                                    history_meta = os.path.join(history_dir, base)
                                    with open(history_meta, 'w', encoding='utf-8') as f:
                                        json.dump(meta, f, indent=4)
                                    try:
                                        os.remove(meta_path)
                                    except Exception:
                                        pass
                                log_message(f"[SCANVAULT] Re-check caught threat, quarantined: {vaulted_path}")
                                
                                # Send notification only once per original file
                                if original_path not in self._notified_files:
                                    self._notified_files.add(original_path)
                                    try:
                                        file_name = os.path.basename(original_path)
                                        notify("🛡️ ScanVault: Threat Quarantined", f"Rule: {rule2}\nFile: {file_name}")
                                    except Exception:
                                        pass
                            except Exception as qe2:
                                log_message(f"[SCANVAULT] Re-check quarantine failed: {qe2}")
                            # Skip normal restore path
                            return
                        # Ensure destination directory exists
                        os.makedirs(os.path.dirname(original_path), exist_ok=True)
                        
                        # Move back to original location and capture the real restored path
                        # Note: shutil.move returns the actual destination path. We use it to
                        # handle cases where the OS/filesystem resolves duplicates or performs
                        # slight normalization, ensuring our rechecks target the right file.
                        restored_path = shutil.move(vaulted_path, original_path)
                        
                        # Log to dedicated ScanVault log
                        log_restore(vaulted_path, restored_path, success=True)
                        
                        # 🔒 FIX RACE CONDITION: Add to recently restored list to prevent immediate recapture
                        # Normalize path for consistent matching (absolute, forward slashes, lowercase)
                        restored_path_normalized = os.path.abspath(restored_path).replace("\\", "/").lower()
                        self._recently_restored[restored_path_normalized] = time.time()
                        log_message(f"[SCANVAULT] Added to restore exclusion: {restored_path_normalized} (180s cooldown)")
                        
                        # ✅ FIX: Small delay to allow OS to release file handles
                        # This prevents "save with different name" errors in applications like Word/Excel
                        time.sleep(0.2)
                        
                        # Archive vault metadata with status
                        if os.path.exists(meta_path):
                            try:
                                with open(meta_path, 'r', encoding='utf-8') as f:
                                    meta = json.load(f)
                            except Exception:
                                meta = {}
                            meta.update({
                                'final_status': 'RESTORED',
                                'action_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'restored_path': restored_path,
                                'pre_restore_hash': pre_hash,
                                'recheck_before_restore': False
                            })
                            base = os.path.basename(meta_path)
                            history_meta = os.path.join(history_dir, base)
                            try:
                                with open(history_meta, 'w', encoding='utf-8') as f:
                                    json.dump(meta, f, indent=4)
                            except Exception as e:
                                log_message(f"[SCANVAULT] Failed to write history meta: {e}")
                            try:
                                os.remove(meta_path)
                            except Exception:
                                pass
                            
                        log_message(f"[SCANVAULT] Clean file restored: {vaulted_path} -> {restored_path}")
                        
                        # ✅ Clear signature to allow re-vaulting if file is copied again
                        try:
                            from Scanning.scanvault import clear_file_signature
                            clear_file_signature(restored_path)
                        except Exception:
                            pass
                        
                        # ✅ FIX: Always send notification for restored files (user needs to know)
                        try:
                            file_name = os.path.basename(restored_path)
                            notify("✅ ScanVault: File Restored", f"Clean file returned\nFile: {file_name}")
                            self._notified_files.add(original_path)  # Track to avoid duplicates on errors
                        except Exception:
                            pass
                        
                        # ❌ DISABLED: Post-restore rechecks cause re-vaulting loops
                        # The 180-second exclusion window already protects against tampering
                        # If file is modified, it will be captured again after exclusion expires
                        # try:
                        #     self._immediate_post_restore_recheck(restored_path, pre_hash)
                        # except Exception:
                        #     pass
                        # try:
                        #     self._schedule_multi_post_restore_rechecks(restored_path, pre_hash)
                        # except Exception:
                        #     pass
                        
                        # Refresh vault UI (history now updated)
                        self._schedule_ui_update(lambda: getattr(self.monitor_page, 'refresh_scanvault_table', self.monitor_page.update_scanvault_listbox)())
                        
                    except Exception as e:
                        log_message(f"[SCANVAULT] Restore failed for {vaulted_path}: {e}")
                    
            else:
                # Scan error - leave in vault for manual review
                log_message(f"[SCANVAULT] Scan error ({status}), leaving in vault: {vaulted_path}")
                
        except Exception as e:
            log_message(f"[SCANVAULT] Processing error: {e}")
                
    def _schedule_ui_update(self, update_func):
        """Schedule a UI update in the main thread."""
        if self.monitor_page and hasattr(self.monitor_page, 'root'):
            try:
                self.monitor_page.root.after(0, update_func)
            except:
                pass
    
    def _schedule_post_restore_recheck(self, original_path: str, delay: int = POST_RESTORE_RECHECK_DELAY, pre_hash: str | None = None):
        def _worker():
            try:
                time.sleep(delay)
                if not os.path.exists(original_path):
                    # Try sibling sweep for duplicate style names like " (1)"
                    matched_via_sibling = self._sibling_sweep_and_scan(original_path, pre_hash)
                    if matched_via_sibling:
                        return
                    telemetry_inc('recheck_missing_post_restore')
                    return
                # Re-scan the original file in place (non-intrusive)
                # Hash guard: quarantine if content changed since pre-restore
                if pre_hash:
                    now_hash = self._sha256_file(original_path)
                    if now_hash and now_hash != pre_hash:
                        try:
                            quarantine_path = quarantine_file(original_path, matched_rules=['HASH_GUARD_CHANGE'])
                            log_message(f"[SCANVAULT] Hash guard quarantined (delayed): {original_path}")
                            try:
                                notify("Threat quarantined!", f"RULE: HASH_GUARD_CHANGE\nPath: {original_path}")
                            except Exception:
                                pass
                            telemetry_inc('hash_guard_quarantined_on_change')
                            if self.monitor_page and hasattr(self.monitor_page, 'add_to_quarantine_listbox'):
                                try:
                                    self.monitor_page.add_to_quarantine_listbox(original_path, quarantine_path + '.meta', ['HASH_GUARD_CHANGE'])
                                except Exception:
                                    pass
                            return
                        except Exception as qe:
                            log_message(f"[SCANVAULT] Hash guard quarantine failed (delayed): {qe}")
                            telemetry_inc('hash_guard_error')
                result = scan_file_for_realtime(original_path)
                matched, rule, quarantined_path, meta_path = result[:4]
                if matched:
                    log_message(f"[SCANVAULT] Post-restore recheck matched, quarantined: {original_path}")
                    telemetry_inc('recheck_match_post_restore')
                    # Update UI if available
                    if self.monitor_page and hasattr(self.monitor_page, 'add_to_quarantine_listbox'):
                        try:
                            self.monitor_page.add_to_quarantine_listbox(quarantined_path, meta_path, [rule])
                        except Exception:
                            pass
                else:
                    telemetry_inc('recheck_clean_post_restore')
            except Exception as e:
                log_message(f"[SCANVAULT] Post-restore recheck error for {original_path}: {e}")
                telemetry_inc('recheck_error_post_restore')
        threading.Thread(target=_worker, daemon=True).start()

    def _immediate_post_restore_recheck(self, restored_path: str, pre_hash: str | None = None):
        """Run a quick, immediate re-scan on the restored file path.

        Adds a tiny stabilization loop to avoid scanning while the file is still
        being finalized by external processes. If a match is found, the function
        relies on scan_file_for_realtime to quarantine the file.
        """
        try:
            # Quick stabilization: wait until size stops changing or 3 attempts
            if not os.path.exists(restored_path):
                # Try sibling sweep for duplicate-named variants
                matched_via_sibling = self._sibling_sweep_and_scan(restored_path, pre_hash)
                if not matched_via_sibling:
                    telemetry_inc('recheck_immediate_missing_post_restore')
                return
            last_size = -1
            delay = 0.15
            for _ in range(6):  # up to ~1.2s total wait
                try:
                    sz = os.path.getsize(restored_path)
                except OSError:
                    sz = -1
                if sz == last_size and sz > 0:
                    break
                last_size = sz
                time.sleep(delay)
                delay = min(delay * 1.6, 0.6)

            # Hash guard: if content changed vs pre-restore, quarantine immediately
            if pre_hash:
                now_hash = self._sha256_file(restored_path)
                if now_hash and now_hash != pre_hash:
                    try:
                        quarantine_path = quarantine_file(restored_path, matched_rules=['HASH_GUARD_CHANGE'])
                        log_message(f"[SCANVAULT] Hash guard quarantined (immediate): {restored_path}")
                        try:
                            notify("Threat quarantined!", f"RULE: HASH_GUARD_CHANGE\nPath: {restored_path}")
                        except Exception:
                            pass
                        telemetry_inc('hash_guard_quarantined_on_change')
                        if self.monitor_page and hasattr(self.monitor_page, 'add_to_quarantine_listbox'):
                            try:
                                self.monitor_page.add_to_quarantine_listbox(quarantine_path, quarantine_path + '.meta', ['HASH_GUARD_CHANGE'])
                            except Exception:
                                pass
                        return
                    except Exception as qe:
                        log_message(f"[SCANVAULT] Hash guard quarantine failed (immediate): {qe}")
                        telemetry_inc('hash_guard_error')

            result = scan_file_for_realtime(restored_path)
            matched, rule, quarantined_path, meta_path = result[:4]
            if matched:
                log_message(f"[SCANVAULT] Immediate post-restore recheck matched, quarantined: {restored_path}")
                telemetry_inc('recheck_immediate_match_post_restore')
                if self.monitor_page and hasattr(self.monitor_page, 'add_to_quarantine_listbox'):
                    try:
                        self.monitor_page.add_to_quarantine_listbox(quarantined_path, meta_path, [rule])
                    except Exception:
                        pass
            else:
                telemetry_inc('recheck_immediate_clean_post_restore')
        except Exception as e:
            log_message(f"[SCANVAULT] Immediate post-restore recheck error for {restored_path}: {e}")
            telemetry_inc('recheck_immediate_error_post_restore')

    def _schedule_multi_post_restore_rechecks(self, path: str, pre_hash: str | None = None):
        """Schedule multiple delayed rechecks for better coverage.

        We trigger rechecks roughly at 1s, 4s, and 10s to catch late writes
        or background modifications.
        """
        for d in (1, POST_RESTORE_RECHECK_DELAY, max(POST_RESTORE_RECHECK_DELAY * 2 + 2, 10)):
            try:
                self._schedule_post_restore_recheck(path, delay=d, pre_hash=pre_hash)
                telemetry_inc('recheck_scheduled_post_restore')
            except Exception:
                pass

    def _sibling_sweep_and_scan(self, target_path: str, pre_hash: str | None = None) -> bool:
        """Look for duplicate-named siblings like 'name (1).ext' and scan them.

        Returns True if any sibling resulted in a quarantine match, or if a clean
        scan was performed (still useful). False if nothing was scanned.
        """
        try:
            directory = os.path.dirname(target_path)
            if not directory or not os.path.isdir(directory):
                return False
            base = os.path.basename(target_path)
            name, ext = os.path.splitext(base)
            # Build a regex that matches 'name.ext' and 'name (N).ext'
            # Escape name to avoid regex surprises
            name_escaped = re.escape(name)
            pattern = re.compile(rf"^{name_escaped}( \(\d+\))?{re.escape(ext)}$", re.IGNORECASE)
            candidates = [os.path.join(directory, f) for f in os.listdir(directory) if pattern.match(f)]
            if not candidates:
                return False
            any_scanned = False
            for path in candidates:
                if not os.path.isfile(path):
                    continue
                any_scanned = True
                # Hash guard first
                if pre_hash:
                    now_hash = self._sha256_file(path)
                    if now_hash and now_hash != pre_hash:
                        try:
                            quarantine_path = quarantine_file(path, matched_rules=['HASH_GUARD_CHANGE'])
                            log_message(f"[SCANVAULT] Sibling sweep hash-guard quarantined: {path}")
                            try:
                                notify("Threat quarantined!", f"RULE: HASH_GUARD_CHANGE\nPath: {path}")
                            except Exception:
                                pass
                            telemetry_inc('hash_guard_quarantined_on_change')
                            if self.monitor_page and hasattr(self.monitor_page, 'add_to_quarantine_listbox'):
                                try:
                                    self.monitor_page.add_to_quarantine_listbox(quarantine_path, quarantine_path + '.meta', ['HASH_GUARD_CHANGE'])
                                except Exception:
                                    pass
                            return True
                        except Exception as qe:
                            log_message(f"[SCANVAULT] Hash guard quarantine failed (sibling): {qe}")
                            telemetry_inc('hash_guard_error')
                result = scan_file_for_realtime(path)
                matched, rule, quarantined_path, meta_path = result[:4]
                if matched:
                    log_message(f"[SCANVAULT] Sibling sweep matched, quarantined: {path}")
                    telemetry_inc('recheck_sibling_sweep_match_post_restore')
                    if self.monitor_page and hasattr(self.monitor_page, 'add_to_quarantine_listbox'):
                        try:
                            self.monitor_page.add_to_quarantine_listbox(quarantined_path, meta_path, [rule])
                        except Exception:
                            pass
                    return True
            if any_scanned:
                telemetry_inc('recheck_sibling_sweep_clean_post_restore')
            return False
        except Exception as e:
            log_message(f"[SCANVAULT] Sibling sweep error for {target_path}: {e}")
            telemetry_inc('recheck_sibling_sweep_error_post_restore')
            return False

    def _sha256_file(self, path: str) -> str | None:
        """Calculate SHA256 hash of a file with proper handle cleanup."""
        try:
            h = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            # File handle is automatically closed by 'with' statement
            return h.hexdigest()
        except Exception:
            return None
    
    def is_recently_restored(self, file_path: str) -> bool:
        """🔒 Check if a file was recently restored and should be excluded from recapture.
        
        Exclusion window: 180 seconds (3 minutes) after restoration.
        
        Args:
            file_path: Path to check (will be normalized internally)
        
        Returns:
            True if file was restored within exclusion window, False otherwise
        """
        try:
            # Normalize path for consistent matching
            normalized_path = os.path.abspath(file_path).replace("\\", "/").lower()
            
            if normalized_path in self._recently_restored:
                restore_time = self._recently_restored[normalized_path]
                elapsed = time.time() - restore_time
                
                if elapsed < self._restore_exclusion_seconds:
                    log_message(f"[SCANVAULT] Blocking recapture of recently restored file: {file_path} (elapsed: {elapsed:.1f}s)")
                    return True
                else:
                    # Expired - remove from tracking
                    self._recently_restored.pop(normalized_path, None)
            
            return False
        except Exception:
            return False
                
    def get_queue_size(self) -> int:
        """Get current queue size for monitoring."""
        from utils.scanvault_queue import get_queue_count
        return get_queue_count()


# Global processor instance
_vault_processor: Optional[ScanVaultProcessor] = None

def get_vault_processor() -> ScanVaultProcessor:
    """Get or create the global vault processor."""
    global _vault_processor
    if _vault_processor is None:
        _vault_processor = ScanVaultProcessor()
    return _vault_processor

def start_vault_processor(monitor_page_ref=None):
    """Start the vault processor with monitor page reference."""
    processor = get_vault_processor()
    if monitor_page_ref:
        processor.monitor_page = monitor_page_ref
    processor.start()
    
def stop_vault_processor():
    """Stop the vault processor."""
    global _vault_processor
    if _vault_processor:
        _vault_processor.stop()