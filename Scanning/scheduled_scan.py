import os, json, threading, time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional, Literal, Callable, Tuple
from config import SCHEDULED_SCAN_CONFIG_PATH
from utils.logger import log_message
from utils.notify import notify
from utils.settings import SETTINGS
from utils.exclusions import is_excluded_path
try:
    from Scanning.scanner_core import scan_file_for_realtime
except Exception:  # allow unit tests without full environment (e.g., missing yara)
    def scan_file_for_realtime(path: str):  # type: ignore
        return (False, None, None, None, 'SKIPPED_TEST_ENV')

@dataclass
class ScanScheduleConfig:
    enabled: bool
    time: str            # HH:MM (primary time reference)
    paths: List[str]
    include_subdirs: bool = True
    # New frequency set: realtime (no scheduled batch; rely on realtime monitor), hourly, twice_daily, daily, custom(interval)
    frequency: Literal['realtime','hourly','twice_daily','daily','custom'] = 'realtime'
    weekdays: List[int] = None          # legacy field kept for backward compat
    interval_minutes: int = 1440        # for custom mode
    last_run: str = None                # ISO timestamp of last run

DEFAULT_CONFIG = ScanScheduleConfig(enabled=False, time="02:00", paths=[], weekdays=[0])


def load_scan_schedule() -> ScanScheduleConfig:
    if not os.path.exists(SCHEDULED_SCAN_CONFIG_PATH):
        return DEFAULT_CONFIG
    try:
        with open(SCHEDULED_SCAN_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Map any legacy frequencies
        legacy_freq = data.get('frequency', 'realtime')
        if legacy_freq in ('weekly','interval'):  # map old names
            if legacy_freq == 'weekly':
                legacy_freq = 'daily'  # reduce to daily (UI no longer has weekly)
            if legacy_freq == 'interval':
                legacy_freq = 'custom'
        if legacy_freq not in ('realtime','hourly','twice_daily','daily','custom'):
            legacy_freq = 'realtime'
        return ScanScheduleConfig(
            enabled=data.get('enabled', False),
            time=data.get('time', '02:00'),
            paths=data.get('paths', []),
            include_subdirs=data.get('include_subdirs', True),
            frequency=legacy_freq,
            weekdays=data.get('weekdays') or [0],
            interval_minutes=int(data.get('interval_minutes', 1440)),
            last_run=data.get('last_run')
        )
    except Exception as e:
        log_message(f"[SCHEDULED SCAN] Failed loading config: {e}")
        return DEFAULT_CONFIG


def save_scan_schedule(cfg: ScanScheduleConfig):
    os.makedirs(os.path.dirname(SCHEDULED_SCAN_CONFIG_PATH), exist_ok=True)
    with open(SCHEDULED_SCAN_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(asdict(cfg), f, indent=4)


class ScheduledScanRunner:
    def __init__(self, gui_ref=None):
        self.gui_ref = gui_ref  # optional reference to main GUI for logging or UI updates
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_run_date = ""  # kept for backwards daily logic
        # Callbacks (GUI thread expected): start(total_files), progress(scanned, total, matches), complete(summary_dict)
        self.on_start: Optional[Callable[[int], None]] = None
        self.on_progress: Optional[Callable[[int,int,int], None]] = None
        self.on_complete: Optional[Callable[[dict], None]] = None

    def _is_excluded(self, path: str) -> bool:
        excluded, _ = is_excluded_path(path)
        return bool(excluded)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                cfg = load_scan_schedule()
                if not cfg.enabled:
                    time.sleep(60)
                    continue
                now = datetime.now()
                freq = cfg.frequency
                # realtime: do nothing (monitoring handles real-time protection)
                if freq == 'realtime':
                    time.sleep(60)
                    continue

                if freq == 'custom':
                    last = datetime.fromisoformat(cfg.last_run) if cfg.last_run else None
                    if (last is None) or (now - last >= timedelta(minutes=cfg.interval_minutes)):
                        self._trigger_run(cfg)
                        continue
                    time.sleep(15)
                    continue

                # Parse configured time
                try:
                    hh, mm = map(int, cfg.time.split(':'))
                except Exception:
                    hh, mm = 2, 0

                # Hourly: run when minute matches, guard by hour duplication
                if freq == 'hourly':
                    if now.minute == mm:
                        if not cfg.last_run:
                            self._trigger_run(cfg); time.sleep(60); continue
                        try:
                            lr = datetime.fromisoformat(cfg.last_run)
                            if lr.strftime('%Y-%m-%d %H') != now.strftime('%Y-%m-%d %H'):
                                self._trigger_run(cfg); time.sleep(60); continue
                        except Exception:
                            self._trigger_run(cfg); time.sleep(60); continue
                    time.sleep(20)
                    continue

                # Twice daily: run at primary hour or hour+12 at given minute.
                if freq == 'twice_daily':
                    alt_hour = (hh + 12) % 24
                    if now.minute == mm and now.hour in (hh, alt_hour):
                        if not cfg.last_run:
                            self._trigger_run(cfg); time.sleep(60); continue
                        try:
                            lr = datetime.fromisoformat(cfg.last_run)
                            # Prevent second run in same hour
                            if lr.strftime('%Y-%m-%d %H') != now.strftime('%Y-%m-%d %H'):
                                self._trigger_run(cfg); time.sleep(60); continue
                        except Exception:
                            self._trigger_run(cfg); time.sleep(60); continue
                    time.sleep(25)
                    continue

                if freq == 'daily':
                    if now.hour == hh and now.minute == mm:
                        # duplication guard
                        if cfg.last_run:
                            try:
                                lr = datetime.fromisoformat(cfg.last_run)
                                if lr.strftime('%Y-%m-%d %H:%M') == now.strftime('%Y-%m-%d %H:%M'):
                                    time.sleep(30); continue
                            except Exception:
                                pass
                        self._trigger_run(cfg)
                        time.sleep(60)
                        continue
                    time.sleep(30)
                    continue

                # Fallback sleep
                time.sleep(60)
            except Exception as e:
                log_message(f"[SCHEDULED SCAN] Loop error: {e}")
                time.sleep(60)

    def _trigger_run(self, cfg: ScanScheduleConfig):
        # Update last_run before actual work to avoid duplicate triggers
        cfg.last_run = datetime.now().isoformat()
        save_scan_schedule(cfg)
        threading.Thread(target=self._run_scan_job, args=(cfg,), daemon=True).start()

    def _run_scan_job(self, cfg: ScanScheduleConfig):
        log_message(f"[SCHEDULED SCAN] Starting scheduled scan @ {cfg.time} for {len(cfg.paths)} path(s)")
        start_time = datetime.now()
        files_to_scan: List[str] = []
        missing_paths: List[str] = []
        for base in cfg.paths:
            if not os.path.exists(base):
                missing_paths.append(base)
                continue
            if os.path.isfile(base):
                if not self._is_excluded(base):
                    files_to_scan.append(base)
            else:
                if cfg.include_subdirs:
                    for root, _, files in os.walk(base):
                        if self._is_excluded(root):
                            continue
                        for f in files:
                            fp = os.path.join(root, f)
                            if not self._is_excluded(fp):
                                files_to_scan.append(fp)
                else:
                    for name in os.listdir(base):
                        p = os.path.join(base, name)
                        if os.path.isfile(p) and not self._is_excluded(p):
                            files_to_scan.append(p)

        total = len(files_to_scan)
        matches = 0
        matched_files: List[Tuple[str,str]] = []  # (path, rule)

        self._emit_start(total)
        for idx, path in enumerate(files_to_scan, start=1):
            matched, rule, _, _ = scan_file_for_realtime(path)[:4]
            if matched:
                matches += 1
                matched_files.append((path, rule))
            self._emit_progress(idx, total, matches)

        duration = (datetime.now() - start_time).total_seconds()
        summary = {
            "total_files": total,
            "matches": matches,
            "missing_paths": missing_paths,
            "matched_samples": matched_files[:25],  # cap list for UI
            "duration_sec": duration,
            "ended_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        log_message(f"[SCHEDULED SCAN] Completed. Files={total} Matches={matches} Duration={duration:.2f}s")
        if matches > 0 and SETTINGS.tray_notifications:
            try:
                notify("VWAR Threat Alert", f"Scheduled scan found {matches} suspicious file(s).")
            except Exception:
                pass
        self._emit_complete(summary)

    def _scan_path(self, path: str):
        matched, rule, qpath, meta_path = scan_file_for_realtime(path)[:4]
        if matched:
            log_message(f"[SCHEDULED SCAN] MATCH {path} rule={rule}")

    # Public API to force immediate run
    def run_now(self):
        cfg = load_scan_schedule()
        if not cfg.paths:
            log_message("[SCHEDULED SCAN] Run Now aborted: no paths configured")
            return
        self._trigger_run(cfg)

    # Emit helpers scheduling via GUI if possible
    def _dispatch_gui(self, func: Callable, *args):
        if self.gui_ref and hasattr(self.gui_ref, 'schedule_gui'):
            try:
                self.gui_ref.schedule_gui(func, *args)
            except Exception:
                pass
        else:
            try:
                func(*args)
            except Exception:
                pass

    def _emit_start(self, total):
        if self.on_start:
            self._dispatch_gui(self.on_start, total)

    def _emit_progress(self, scanned, total, matches):
        if self.on_progress:
            self._dispatch_gui(self.on_progress, scanned, total, matches)

    def _emit_complete(self, summary):
        if self.on_complete:
            self._dispatch_gui(self.on_complete, summary)

# Helper for unit tests to evaluate due status (simplified logic)
def should_run_interval(now: datetime, last_run_iso: Optional[str], interval_minutes: int) -> bool:
    if last_run_iso is None:
        return True
    try:
        last = datetime.fromisoformat(last_run_iso)
        return (now - last) >= timedelta(minutes=interval_minutes)
    except Exception:
        return True

def is_due_daily(now: datetime, cfg: ScanScheduleConfig) -> bool:
    """Return True if a daily schedule is due at 'now' considering last_run minute-level duplication guard."""
    if cfg.frequency != 'daily' or not cfg.enabled:
        return False
    if now.strftime('%H:%M') != cfg.time:
        return False
    if not cfg.last_run:
        return True
    try:
        lr = datetime.fromisoformat(cfg.last_run)
        # Prevent double run in same minute
        return lr.strftime('%Y-%m-%d %H:%M') != now.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return True

def is_due_weekly(now: datetime, cfg: ScanScheduleConfig) -> bool:
    if cfg.frequency != 'weekly' or not cfg.enabled:
        return False
    if now.strftime('%H:%M') != cfg.time:
        return False
    if cfg.weekdays and now.weekday() not in cfg.weekdays:
        return False
    if not cfg.last_run:
        return True
    try:
        lr = datetime.fromisoformat(cfg.last_run)
        return lr.strftime('%Y-%m-%d %H:%M') != now.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return True
