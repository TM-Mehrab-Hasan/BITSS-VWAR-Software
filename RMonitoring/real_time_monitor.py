

#V111111111111111111111111111111111111111111111111
# import os
# import time
# import threading
# import getpass
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler
# from Scanning.scanner_core import scan_file_for_realtime
# from utils.logger import log_message
# from queue import Queue
# from pathlib import Path
# import string
# import subprocess
# from RMonitoring.pipe_client import start_pipe_reader, stop_pipe_reader


# def is_file_ready(path):
#     try:
#         if not os.path.exists(path):
#             return False
#         if os.path.getsize(path) == 0:
#             return False
#         with open(path, "rb") as f:
#             chunk = f.read(4096)
#             return bool(chunk)
#     except:
#         return False


# class RealTimeMonitor(FileSystemEventHandler):
#     def __init__(self, gui, watch_paths=None):
#         self.gui = gui

#         # Setup included folders if not passed
#         if watch_paths is None:
#             user_profile = Path(os.path.expanduser("~"))
#             self.included_folders = [
#                 str(user_profile / "Downloads"),
#                 str(user_profile / "Desktop"),
#                 str(user_profile / "Documents")
#             ]
#             # Add all non-C drives
#             for letter in string.ascii_uppercase:
#                 if letter == "C":
#                     continue
#                 drive_path = f"{letter}:/"
#                 if os.path.exists(drive_path):
#                     self.included_folders.append(drive_path)

#             valid_included_folders = [p for p in self.included_folders if os.path.exists(p)]
#             self.watch_paths = valid_included_folders
#         else:
#             self.watch_paths = watch_paths if isinstance(watch_paths, list) else [watch_paths]

#         print(f"[DEBUG] Included folders to watch: {self.watch_paths}")

#         self.observer = Observer()
#         self.recent_events = {}  # path -> timestamp
#         self.pending_scan_files = set()
#         self.already_scanned = set()

#         base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
#         print(f"[DEBUG] Base directory (excluded): {base_dir}")

#         self.excluded_folders = [base_dir]
#         # Exclude recycle bins on all drives
#         for drive_letter in string.ascii_uppercase:
#             drive = f"{drive_letter}:\\"
#             recycle_bin = os.path.join(drive, "$Recycle.Bin")
#             if os.path.exists(drive):
#                 self.excluded_folders.append(recycle_bin)

#         self.excluded_extensions = (".tmp", ".log", ".lock", ".crdownload", ".part", ".ds_store", "thumbs.db")
#         self.excluded_prefixes = ("~$",)

#         self.scan_queue = Queue()
#         self.scan_worker = threading.Thread(target=self._scan_worker_loop, daemon=True)
#         self.scan_worker.start()

#         # C++ monitor related
#         self._cpp_proc = None
#         self._pipe_thread = None


#     # --- Watchdog monitoring methods (your existing system) ---

#     def start_watchdog(self):
#         print("[DEBUG] Starting watchdog observer")
#         for path in self.watch_paths:
#             print(f"  ➤ Watching: {path}")
#             try:
#                 self.observer.schedule(self, path=path, recursive=True)
#             except Exception as e:
#                 print(f"[ERROR] Failed to watch {path}: {e}")
#         self.observer.start()

#     def stop_watchdog(self):
#         print("[INFO] Stopping watchdog observer.")
#         self.observer.stop()
#         self.observer.join()

#     def is_excluded(self, path):
#         path = os.path.abspath(path).lower()
#         for folder in self.excluded_folders:
#             folder = os.path.abspath(folder).lower()
#             if folder in path:
#                 return True
#         return False

#     def is_excluded_file(self, path):
#         filename = os.path.basename(path).lower()
#         if filename.endswith(self.excluded_extensions) or filename.startswith(self.excluded_prefixes):
#             return True
#         try:
#             if os.path.exists(path) and os.path.getsize(path) == 0:
#                 return True
#         except:
#             return True
#         return False

#     def on_created(self, event):
#         if not event.is_directory:
#             self._handle_event(event.src_path)

#     def on_modified(self, event):
#         if not event.is_directory:
#             self._handle_event(event.src_path)

#     def _handle_event(self, path):
#         path = os.path.abspath(path).replace("\\", "/").lower()
#         now = time.time()

#         if self.is_excluded(path) or self.is_excluded_file(path):
#             return

#         if path in self.recent_events and now - self.recent_events[path] < 5:
#             return

#         self.scan_queue.put(path)


#     def wait_and_scan_file(self, path):
#         max_wait = 5
#         waited = 0
#         stable_counter = 0
#         try:
#             while waited < max_wait:
#                 if is_file_ready(path):
#                     stable_counter += 1
#                     if stable_counter >= 3:
#                         break
#                 else:
#                     stable_counter = 0
#                 time.sleep(0.5)
#                 waited += 0.5

#             if stable_counter < 3:
#                 print(f"[WARNING] File never stabilized: {path}")
#                 return

#             time.sleep(0.2)  # slight delay

#             if getattr(self.gui, "monitoring_active", False):
#                 try:
#                     matched, rule, file_path, meta_path = scan_file_for_realtime(path)
#                     if matched and meta_path:
#                         monitor_page = self.gui
#                         if monitor_page and hasattr(monitor_page, "add_to_quarantine_listbox"):
#                             monitor_page.add_to_quarantine_listbox(file_path, meta_path, [rule])
#                         if hasattr(self.gui, "notify_threat_detected"):
#                             self.gui.notify_threat_detected(file_path, [rule])
#                 except Exception as e:
#                     print(f"[ERROR] Failed scanning {path}: {e}")
#             else:
#                 self.pending_scan_files.add(path)
#                 print(f"[INFO] Queued for future scan: {path}")
#         finally:
#             self.recent_events[path] = time.time()
#             self.already_scanned.discard(path)

#     def process_pending_files(self):
#         print("[INFO] Processing pending files...")
#         for path in list(self.pending_scan_files):
#             if os.path.exists(path):
#                 print(f"[INFO] Scanning pending: {path}")
#                 self.wait_and_scan_file(path)
#         self.pending_scan_files.clear()

#     def _scan_worker_loop(self):
#         while True:
#             try:
#                 path = self.scan_queue.get()
#                 threading.Thread(target=self.wait_and_scan_file, args=(path,), daemon=True).start()
#             except Exception as e:
#                 print(f"[ERROR] Worker failed: {e}")


#     # --- New methods for C++ real-time monitor integration ---

#     def start_cpp_monitor_engine(self, exe_path=None, excludes=None):
#         """
#         Start the C++ monitor executable and pipe reader.
#         exe_path: path to vwar_monitor.exe (default: project_root/vwar_monitor/vwar_monitor.exe)
#         excludes: optional list of paths to exclude (strings).
#         """
#         if getattr(self, "_cpp_proc", None):
#             print("[INFO] C++ monitor already running.")
#             return

#         if exe_path is None:
#             exe_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vwar_monitor', 'vwar_monitor.exe'))

#         if not os.path.exists(exe_path):
#             print(f"[ERROR] C++ monitor executable not found: {exe_path}")
#             return

#         cmd = [exe_path]
#         if excludes:
#             for e in excludes:
#                 cmd.append(str(e))

#         try:
#             self._cpp_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#             print(f"[INFO] Started C++ monitor (pid {self._cpp_proc.pid})")
#         except Exception as e:
#             print(f"[ERROR] Failed to start C++ monitor: {e}")
#             self._cpp_proc = None
#             return

#         self._pipe_thread = start_pipe_reader(self.scan_queue)

#     def stop_cpp_monitor_engine(self):
#         """
#         Stop the pipe reader and terminate the C++ process if running.
#         """
#         try:
#             stop_pipe_reader()
#         except Exception:
#             pass

#         if getattr(self, "_cpp_proc", None):
#             try:
#                 self._cpp_proc.terminate()
#                 self._cpp_proc.wait(timeout=3)
#             except Exception:
#                 try:
#                     self._cpp_proc.kill()
#                 except Exception:
#                     pass
#             print("[INFO] C++ monitor stopped.")
#             self._cpp_proc = None
#             self._pipe_thread = None
#V111111111111111111111111111111111111111111111111



import os
import sys
import time
import threading
import subprocess
from queue import Queue
from pathlib import Path
from Scanning.scanner_core import scan_file_for_realtime
from RMonitoring.pipe_client import start_pipe_reader, stop_pipe_reader
from utils.exclusions import is_excluded_path, print_exclusion_debug
from Scanning.scanvault import vault_capture_file
from utils.logger import telemetry_inc, log_message
from config import RENAME_FOLLOW_DEBUG
from utils.path_utils import resource_path

def is_file_ready(path):
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return False
        with open(path, "rb") as f:
            return bool(f.read(4096))
    except:
        return False

class RealTimeMonitor:
    def __init__(self, gui):
        self.gui = gui
        self.scan_queue = Queue()
        self.pending_scan_files = set()
        self.already_scanned = set()
        self._recent_events = {}  # path -> last handled timestamp
        self._cpp_proc = None
        self._pipe_thread = None

        # Print exclusion debug info at startup
        print_exclusion_debug()

        # Start the scan worker
        self.scan_worker = threading.Thread(target=self._scan_worker_loop, daemon=True)
        self.scan_worker.start()

    # ---------------- Scan Worker ----------------
    def _scan_worker_loop(self):
        while True:
            path = self.scan_queue.get()
            threading.Thread(target=self.wait_and_scan_file, args=(path,), daemon=True).start()

    def wait_and_scan_file(self, path):
        # Track dynamic path (handles temp -> final rename during downloads)
        norm_path = os.path.abspath(path)
        original_path = norm_path

        # Ignore directories immediately
        if not os.path.splitext(norm_path)[1] and not os.path.isfile(norm_path):
            return

        # Skip internal/recycle-bin paths early (but still record last seen to suppress bursts)
        excluded, _reason = is_excluded_path(norm_path)
        now = time.time()
        if excluded and _reason in ('INTERNAL', 'RECYCLE_BIN'):
            self._recent_events[norm_path] = now
            return

        # Suppress duplicate events for the same file within a short window
        last = self._recent_events.get(norm_path)
        if last and (now - last) < 5.0:
            return

        # Stabilization configuration
        max_wait = 30
        sample_interval = 0.5
        settle_required = 4
        stable_counter = 0
        waited = 0.0
        last_size = -1
        last_mtime = -1

        partial_exts = ('.crdownload', '.part', '.partial', '.download', '.tmp')
        rename_followed = False

        def follow_rename(current_path: str) -> str | None:
            """If a temp download file disappeared, try to locate its final name.

            Returns new absolute path if found, otherwise None.
            """
            nonlocal rename_followed
            lower = current_path.lower()
            for ext in partial_exts:
                if lower.endswith(ext):
                    base = current_path[: -len(ext)]
                    if os.path.exists(base):
                        new_abs = os.path.abspath(base)
                        if RENAME_FOLLOW_DEBUG:
                            log_message(f"[MONITOR] rename-follow: {current_path} -> {new_abs}")
                        telemetry_inc('rename_follow_hit')
                        rename_followed = True
                        return new_abs
            # As a fallback, look for a file created very recently in same dir with same stem
            try:
                d = os.path.dirname(current_path)
                stem = os.path.basename(current_path).split('.')[0]
                candidates = []
                now_ts = time.time()
                for f in os.listdir(d):
                    if f.startswith(stem) and not any(f.lower().endswith(e) for e in partial_exts):
                        p = os.path.join(d, f)
                        try:
                            st = os.stat(p)
                            if now_ts - st.st_mtime < 5.0:  # created/modified in last 5s
                                candidates.append((st.st_mtime, p))
                        except Exception:
                            pass
                if candidates:
                    candidates.sort(reverse=True)
                    new_abs = os.path.abspath(candidates[0][1])
                    if RENAME_FOLLOW_DEBUG:
                        log_message(f"[MONITOR] rename-follow (heuristic): {current_path} -> {new_abs}")
                    telemetry_inc('rename_follow_hit')
                    rename_followed = True
                    return new_abs
            except Exception:
                pass
            return None

        try:
            while waited < max_wait:
                if not os.path.exists(norm_path):
                    # Try to follow rename only if original looked like temp
                    newp = follow_rename(norm_path)
                    if newp:
                        norm_path = newp
                        # reset stability counters for new path
                        stable_counter = 0
                        last_size = -1
                        last_mtime = -1
                        # Do not mark recent for old path to allow final event too
                        continue
                    else:
                        # Give a small grace period before abandoning
                        time.sleep(sample_interval)
                        waited += sample_interval
                        if waited >= max_wait:
                            return
                        continue

                try:
                    stat = os.stat(norm_path)
                    size = stat.st_size
                    mtime = int(stat.st_mtime)
                except Exception:
                    size = -1
                    mtime = -1

                lower_name = norm_path.lower()
                if any(lower_name.endswith(ext) for ext in partial_exts):
                    stable_counter = 0
                else:
                    if size == last_size and mtime == last_mtime and size > 0:
                        stable_counter += 1
                    else:
                        stable_counter = 0
                last_size, last_mtime = size, mtime

                if size > 0:
                    try:
                        with open(norm_path, 'rb') as _f:
                            pass
                    except Exception:
                        stable_counter = 0

                if stable_counter >= settle_required:
                    break
                time.sleep(sample_interval)
                waited += sample_interval

            if stable_counter < settle_required:
                print(f"[INFO] Skipping early capture (unstable download): {norm_path}")
                return

            time.sleep(0.2)

            try:
                event_type = 'download_finalized' if rename_followed else 'created'
                vaulted_path, meta_path = vault_capture_file(norm_path, event=event_type)
                if hasattr(self.gui, "add_to_scanvault_listbox"):
                    self.gui.add_to_scanvault_listbox(vaulted_path, meta_path)
                telemetry_inc('stabilized_capture')
                from Scanning.vault_processor import get_vault_processor
                get_vault_processor().enqueue_for_scan(vaulted_path, meta_path)
            except Exception as e:
                if "Duplicate capture suppressed" in str(e):
                    self._recent_events[norm_path] = time.time()
                    telemetry_inc('duplicate_suppressed')
                    return
                print(f"[WARNING] ScanVault capture failed for {norm_path}: {e}")
                if getattr(self.gui, "monitoring_active", False):
                    try:
                        result = scan_file_for_realtime(norm_path)
                        matched, rule, file_path, meta_path = result[:4]
                        status = getattr(result, 'status', 'UNKNOWN')
                        if matched and meta_path:
                            if hasattr(self.gui, "add_to_quarantine_listbox"):
                                self.gui.add_to_quarantine_listbox(file_path, meta_path, [rule])
                            if hasattr(self.gui, "notify_threat_detected"):
                                self.gui.notify_threat_detected(file_path, [rule])
                        else:
                            if status == "QUARANTINE_FAILED":
                                print(f"[WARNING] Quarantine failed for {file_path} (rule={rule})")
                            elif status == "YARA_ERROR":
                                print(f"[WARNING] YARA error while scanning {file_path}")
                            elif status == "ERROR":
                                print(f"[ERROR] Unexpected scan error {file_path}")
                            elif status == "NO_RULES":
                                print("[ERROR] No rules loaded during real-time scan.")
                    except Exception as e2:
                        print(f"[ERROR] Failed scanning {norm_path}: {e2}")
                else:
                    self.pending_scan_files.add(norm_path)
                    print(f"[INFO] Queued for future scan: {norm_path}")
        finally:
            self.already_scanned.discard(norm_path)
            self._recent_events[norm_path] = time.time()

    # ---------------- Pipe Integration ----------------
    def start_cpp_monitor_engine(self, exe_path=None, excludes=None):
        if self._cpp_proc:
            print("[INFO] C++ monitor already running.")
            return

        # Resolve path to vwar_monitor.exe in a PyInstaller-friendly way
        if exe_path is None:
            candidates = []
            try:
                candidates.append(resource_path(os.path.join('vwar_monitor', 'vwar_monitor.exe')))
            except Exception:
                pass
            candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vwar_monitor', 'vwar_monitor.exe')))
            try:
                candidates.append(os.path.join(os.path.dirname(sys.executable), 'vwar_monitor', 'vwar_monitor.exe'))
            except Exception:
                pass
            exe_path = next((p for p in candidates if p and os.path.exists(p)), candidates[-1])

        if not os.path.exists(exe_path):
            print(f"[ERROR] C++ monitor executable not found: {exe_path}")
            print("[HINT] If running a PyInstaller build, include the folder via:\n"
                  "       --add-data \"vwar_monitor;vwar_monitor\"\n"
                  "       or place the 'vwar_monitor' folder next to the EXE.")
            return

        cmd = [exe_path]
        if excludes:
            cmd += [str(e) for e in excludes]

        try:
            creationflags = 0
            startupinfo = None
            if os.name == 'nt':
                # Hide console window for the C++ watcher so it runs in background
                try:
                    creationflags |= subprocess.CREATE_NO_WINDOW
                except Exception:
                    pass
                try:
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    si.wShowWindow = 0  # SW_HIDE
                    startupinfo = si
                except Exception:
                    startupinfo = None

            self._cpp_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            print(f"[INFO] Started C++ monitor (pid {self._cpp_proc.pid})")
        except Exception as e:
            print(f"[ERROR] Failed to start C++ monitor: {e}")
            self._cpp_proc = None
            return

        # Start pipe reader to push detected files into scan_queue
        self._pipe_thread = start_pipe_reader(self.scan_queue)

    def stop_cpp_monitor_engine(self):
        try:
            stop_pipe_reader()
        except Exception:
            pass

        if self._cpp_proc:
            try:
                self._cpp_proc.terminate()
                self._cpp_proc.wait(timeout=3)
            except Exception:
                try:
                    self._cpp_proc.kill()
                except Exception:
                    pass
            print("[INFO] C++ monitor stopped.")
            self._cpp_proc = None
            self._pipe_thread = None

    # ---------------- Pending Files ----------------
    def process_pending_files(self):
        for path in list(self.pending_scan_files):
            if os.path.exists(path):
                self.wait_and_scan_file(path)
        self.pending_scan_files.clear()
