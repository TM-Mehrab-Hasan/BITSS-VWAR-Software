# Scanning/scanner_core.py

import traceback
from collections import namedtuple
from Scanning.yara_engine import compile_yara_rules
from Scanning.quarantine import quarantine_file
from utils.logger import log_message, telemetry_inc
from utils.notify import notify
import yara
import os  # at the top if not already imported
from utils.exclusions import is_excluded_path

# Compile rules once at module load (unpack tuple: rules and count)
rules, rule_count = compile_yara_rules()
print(f"[INFO] {rule_count} YARA rules compiled and ready.")

# Compute normalized project base directory and internal exclude roots
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")).replace("\\", "/").lower()
_EXCLUDE_ROOTS = [
    _BASE_DIR,
    f"{_BASE_DIR}/assets/yara",
    f"{_BASE_DIR}/quarantine",
    f"{_BASE_DIR}/build",
    f"{_BASE_DIR}/__pycache__",
    f"{_BASE_DIR}/data/scan_queue",
]

# Explicit allowlist for subpaths inside project we still want to scan.
_INTERNAL_ALLOW_SUBPATHS = [f"{_BASE_DIR}/scanvault/"]

# Helper: force scan (ignoring INTERNAL) for vaulted files
def force_scan_vaulted(file_path: str):
    """Force scanning of a vaulted file by temporarily bypassing internal exclusion.

    This ignores INTERNAL exclusion results but still respects TEMP style skips
    (we assume vault never stores pure temp markers). Returns ScanResult.
    """
    if not rules:
        log_message("[ERROR] No YARA rules loaded (force vault).")
        return ScanResult(False, None, file_path, None, "NO_RULES")
    try:
        if not os.path.isfile(file_path):
            return ScanResult(False, None, file_path, None, "SKIPPED_NON_FILE")
        try:
            # Only apply temp exclusion; INTERNAL is ignored intentionally
            excluded, reason = is_excluded_path(file_path)
            if excluded and reason != 'INTERNAL':
                log_message(f"[VAULT][SKIPPED] {reason}: {file_path}")
                status = "SKIPPED_TEMP" if reason.startswith('TEMP') else f"SKIPPED_{reason}"
                return ScanResult(False, None, file_path, None, status)
            matches = rules.match(file_path, timeout=60)
        except yara.Error as e:
            log_message(f"[VAULT][WARNING] YARA scan failed: {e} — {file_path}")
            return ScanResult(False, None, file_path, None, "YARA_ERROR")
        if matches:
            rule = matches[0].rule
            try:
                quarantine_path = quarantine_file(file_path, matched_rules=[rule])
            except RuntimeError as qe:
                log_message(f"[VAULT][WARNING] Quarantine failed: {qe}")
                telemetry_inc('scan_quarantine_failed')
                return ScanResult(False, rule, file_path, None, "QUARANTINE_FAILED")
            meta_path = quarantine_path + ".meta"
            log_message(f"[VAULT][MATCH] {file_path} => Rule: {rule}")
            if not notify("Threat quarantined!", f"RULE: {rule}\nPath: {file_path}"):
                log_message("[VAULT][WARN] Notification dispatch failed.")
            telemetry_inc('scan_match')
            return ScanResult(True, rule, quarantine_path, meta_path, "MATCH")
        telemetry_inc('scan_clean')
        return ScanResult(False, None, file_path, None, "CLEAN")
    except Exception:
        log_message(f"[VAULT][ERROR] Failed to force scan {file_path}:\n{traceback.format_exc()}")
        telemetry_inc('scan_error')
        return ScanResult(False, None, file_path, None, "ERROR")

def _is_internal_path(path: str) -> bool:
    p = os.path.abspath(path).replace("\\", "/").lower()
    # Allow explicit subpaths first
    for allow in _INTERNAL_ALLOW_SUBPATHS:
        if p.startswith(allow):
            return False
    # quick allow for paths outside project directory
    for root in _EXCLUDE_ROOTS:
        if p == root or p.startswith(root + "/"):
            return True
    # common cache/temp folders inside the project
    return "/__pycache__/" in p

# Backwards-compatible structured result (tuple subclass)
ScanResult = namedtuple("ScanResult", "matched rule quarantined_path meta_path status")


def scan_file_for_realtime(file_path):
    """Scan a file with precompiled YARA rules and (optionally) quarantine.

    Backwards-compatible return supports tuple unpacking of first four
    values (matched, rule, quarantined_path, meta_path). A fifth logical
    value 'status' is accessible if callers use the named fields.

    Status values:
      NO_RULES           – rules not loaded
      SKIPPED_INTERNAL   – skipped internal rule file directory
      MATCH              – rule matched & quarantined
      QUARANTINE_FAILED  – rule matched but quarantine failed
      CLEAN              – no match
      YARA_ERROR         – YARA engine error (file disappeared, etc.)
      ERROR              – unexpected exception
    """
    if not rules:
        log_message("[ERROR] No YARA rules loaded.")
        return ScanResult(False, None, file_path, None, "NO_RULES")

    try:
        if not os.path.isfile(file_path):
            return ScanResult(False, None, file_path, None, "SKIPPED_NON_FILE")
        try:
            normalized_path = file_path.replace("\\", "/").lower()
            # Shared exclusions: internal workspace and temp-like files/roots
            excluded, reason = is_excluded_path(file_path)
            # INTERNAL exclusion is overrideable if allowlist matched earlier; we already returned False in _is_internal_path()
            if excluded:
                if reason == 'INTERNAL' and any(normalized_path.startswith(a) for a in _INTERNAL_ALLOW_SUBPATHS):
                    log_message(f"[INFO] Overriding INTERNAL exclusion for vaulted path: {file_path}")
                else:
                    status = "SKIPPED_INTERNAL" if reason == 'INTERNAL' else "SKIPPED_TEMP"
                    log_message(f"[SKIPPED] {reason}: {file_path}")
                    return ScanResult(False, None, file_path, None, status)

            matches = rules.match(file_path, timeout=60)
        except yara.Error as e:
            log_message(f"[WARNING] YARA scan failed: {e} — {file_path}")
            return ScanResult(False, None, file_path, None, "YARA_ERROR")

        if matches:
            rule = matches[0].rule
            try:
                quarantine_path = quarantine_file(file_path, matched_rules=[rule])
            except RuntimeError as qe:
                log_message(f"[WARNING] Quarantine failed: {qe}")
                telemetry_inc('scan_quarantine_failed')
                return ScanResult(False, rule, file_path, None, "QUARANTINE_FAILED")

            meta_path = quarantine_path + ".meta"
            log_message(f"[MATCH] {file_path} => Rule: {rule}")
            if not notify("Threat quarantined!", f"RULE: {rule}\nPath: {file_path}"):
                log_message("[WARN] Notification dispatch failed.")
            telemetry_inc('scan_match')
            return ScanResult(True, rule, quarantine_path, meta_path, "MATCH")

        # No match
        telemetry_inc('scan_clean')
        return ScanResult(False, None, file_path, None, "CLEAN")

    except Exception:
        log_message(f"[ERROR] Failed to scan {file_path}:\n{traceback.format_exc()}")
        telemetry_inc('scan_error')
        return ScanResult(False, None, file_path, None, "ERROR")
