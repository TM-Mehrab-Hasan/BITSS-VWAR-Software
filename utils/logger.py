import os
from datetime import datetime
from collections import defaultdict

LOG_PATH = os.path.join("data", "vwar.log")


def log_message(message: str, to_file: bool = True):
    """Log message to console and optionally to a log file."""
    timestamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    # print(timestamped)

    if to_file:
        try:
            os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(timestamped + "\n")
        except Exception as e:
            print(f"[ERROR] Failed to write to log file: {e}")

# --- Lightweight Telemetry ----------------------------------------------------
_telemetry_counters = defaultdict(int)

def telemetry_inc(key: str, delta: int = 1, echo: bool = True):
    """Increment a named telemetry counter and optionally log its new value.

    Example keys: 'rename_follow_hit', 'duplicate_suppressed',
    'stabilized_capture', 'scan_match', 'scan_clean', 'scan_error'.
    """
    try:
        _telemetry_counters[key] += delta
        if echo:
            log_message(f"[TELEMETRY] {key} += {delta} total={_telemetry_counters[key]}")
    except Exception:
        # Telemetry must not break runtime
        pass

def telemetry_snapshot():
    """Log a snapshot of all telemetry counters."""
    try:
        if not _telemetry_counters:
            log_message("[TELEMETRY] snapshot: (empty)")
            return
        summary = ", ".join(f"{k}={v}" for k, v in sorted(_telemetry_counters.items()))
        log_message(f"[TELEMETRY] snapshot: {summary}")
    except Exception:
        pass
