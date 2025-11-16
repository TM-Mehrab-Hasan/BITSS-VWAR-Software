# RMonitoring/pipe_client.py
import threading
import json
import time
import pywintypes
import win32file
from pathlib import Path

PIPE_NAME = r'\\.\pipe\vwar_monitor'
_stop_event = threading.Event()

def start_pipe_reader(scan_queue):
    """
    scan_queue: your existing Queue instance (from real_time_monitor.py).
    Returns the Thread object.
    """
    def run():
        buffer = b""
        while not _stop_event.is_set():
            try:
                # Try to open the named pipe (blocks if server not available)
                handle = None
                try:
                    handle = win32file.CreateFile(
                        PIPE_NAME,
                        win32file.GENERIC_READ,
                        0,  # no sharing
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                except pywintypes.error:
                    time.sleep(0.8)
                    continue

                # read loop
                while not _stop_event.is_set():
                    try:
                        rc, data = win32file.ReadFile(handle, 4096)
                        if rc == 0:
                            if not data:
                                time.sleep(0.01)
                                continue
                            buffer += data
                            while b'\n' in buffer:
                                line, buffer = buffer.split(b'\n', 1)
                                if not line.strip():
                                    continue
                                try:
                                    obj = json.loads(line.decode('utf-8', errors='ignore'))
                                    p = obj.get('path')
                                    if p:
                                        # push into your existing scan queue as-is
                                        scan_queue.put(p)
                                except Exception as e:
                                    print("[pipe_client] JSON parse error:", e)
                        else:
                            break
                    except pywintypes.error:
                        # pipe disconnected
                        break

                try:
                    handle.Close()
                except:
                    pass

            except Exception as ex:
                print("[pipe_client] top-level error:", ex)
                time.sleep(1.0)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t

def stop_pipe_reader():
    _stop_event.set()
