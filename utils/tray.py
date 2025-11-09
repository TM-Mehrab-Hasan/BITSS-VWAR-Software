from __future__ import annotations

import os
import sys
import threading
import time
from typing import Callable, Optional

try:
    import win32api  # type: ignore
    import win32con  # type: ignore
    import win32gui  # type: ignore
    import win32gui_struct  # type: ignore
    import pywintypes  # type: ignore
    
    # Shell notify icon constants
    NIM_ADD = 0x00000000
    NIM_MODIFY = 0x00000001
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    
    PYWIN32_AVAILABLE = True
except Exception:  # pragma: no cover
    win32api = win32con = win32gui = win32gui_struct = pywintypes = None  # type: ignore
    PYWIN32_AVAILABLE = False

try:
    from utils.logger import log_message
except Exception:  # pragma: no cover
    def log_message(msg: str):  # type: ignore
        print(msg)


class TrayIcon:
    def __init__(self, tooltip: str, icon_path: Optional[str], on_restore: Callable[[], None], on_exit: Callable[[], None], on_scan_now: Optional[Callable[[], None]] = None):
        self.tooltip = tooltip
        self.icon_path = icon_path
        self.on_restore = on_restore
        self.on_exit = on_exit
        self.on_scan_now = on_scan_now
        self.hwnd = None
        self.hicon = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> bool:
        if not PYWIN32_AVAILABLE:
            log_message("[TRAY] pywin32 not available; tray disabled")
            return False
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._running = False
        if win32gui and self.hwnd:
            try:
                win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)  # type: ignore
            except Exception:
                pass
    
    def update_tooltip(self, new_tooltip: str):
        """Update the tray icon tooltip dynamically."""
        if not PYWIN32_AVAILABLE or not self.hwnd or not self.hicon:
            return
        try:
            self.tooltip = new_tooltip
            flags = NIF_TIP
            nid = (self.hwnd, 0, flags, 0, 0, new_tooltip)
            win32gui.Shell_NotifyIcon(NIM_MODIFY, nid)  # type: ignore
        except Exception as e:
            log_message(f"[TRAY] Failed to update tooltip: {e}")

    # Windows message loop implementation
    def _message_loop(self):  # pragma: no cover - GUI thread
        try:
            # Window class for hidden window
            wc = win32gui.WNDCLASS()  # type: ignore
            hinst = wc.hInstance = win32api.GetModuleHandle(None)  # type: ignore
            wc.lpszClassName = "VWARTrayClass"
            wc.lpfnWndProc = {
                win32con.WM_COMMAND: self._on_command,
                win32con.WM_DESTROY: self._on_destroy,
                win32con.WM_USER + 20: self._on_notify,
            }
            
            try:
                class_atom = win32gui.RegisterClass(wc)  # type: ignore
            except Exception:
                # Class might already be registered
                class_atom = win32gui.WNDCLASS  # type: ignore
                
            # Create hidden window
            self.hwnd = win32gui.CreateWindowEx(
                0, "VWARTrayClass", "VWARTray", 0, 0, 0, 0, 0, 0, 0, hinst, None
            )  # type: ignore
            
            # Load icon
            if self.icon_path and os.path.exists(self.icon_path):
                try:
                    self.hicon = win32gui.LoadImage(
                        hinst, self.icon_path, win32con.IMAGE_ICON, 0, 0, 
                        win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
                    )  # type: ignore
                except Exception as e:
                    log_message(f"[TRAY] Failed to load icon: {e}")
                    self.hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)  # type: ignore
            else:
                self.hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)  # type: ignore
            
            # Add tray icon
            flags = NIF_ICON | NIF_MESSAGE | NIF_TIP
            nid = (self.hwnd, 0, flags, win32con.WM_USER + 20, self.hicon, self.tooltip)
            
            try:
                win32gui.Shell_NotifyIcon(NIM_ADD, nid)  # type: ignore
                log_message("[TRAY] Tray icon added successfully")
            except Exception as e:
                log_message(f"[TRAY] Failed to add tray icon: {e}")
                return
            
            # Message pump loop
            while self._running:
                try:
                    win32gui.PumpWaitingMessages()  # type: ignore
                except Exception:
                    pass
                time.sleep(0.1)
            
            # Cleanup
            try:
                win32gui.Shell_NotifyIcon(NIM_DELETE, nid)  # type: ignore
                log_message("[TRAY] Tray icon removed")
            except Exception:
                pass
                
        except Exception as e:
            log_message(f"[TRAY] Message loop error: {e}")
            import traceback
            log_message(traceback.format_exc())

    def _on_notify(self, hwnd, msg, wparam, lparam):  # pragma: no cover - user interaction
        if lparam == win32con.WM_LBUTTONUP:  # type: ignore
            self.on_restore()
        elif lparam == win32con.WM_RBUTTONUP:  # context menu
            self._show_menu()
        return True

    def _show_menu(self):  # pragma: no cover
        menu = win32gui.CreatePopupMenu()  # type: ignore
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1, "Open VWAR")  # type: ignore
        win32gui.AppendMenu(menu, win32con.MF_STRING, 3, "Scan Now")  # type: ignore
        win32gui.AppendMenu(menu, win32con.MF_STRING, 2, "Exit")  # type: ignore
        pos = win32gui.GetCursorPos()  # type: ignore
        win32gui.SetForegroundWindow(self.hwnd)  # type: ignore
        win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN, pos[0], pos[1], 0, self.hwnd, None)  # type: ignore

    def _on_command(self, hwnd, msg, wparam, lparam):  # pragma: no cover
        cmd_id = win32api.LOWORD(wparam)  # type: ignore
        if cmd_id == 1:
            self.on_restore()
        elif cmd_id == 2:
            self.on_exit()
        elif cmd_id == 3 and self.on_scan_now:
            self.on_scan_now()

    def _on_destroy(self, hwnd, msg, wparam, lparam):  # pragma: no cover
        self.stop()


def create_tray(on_restore: Callable[[], None], on_exit: Callable[[], None], icon_path: Optional[str], tooltip: str = "VWAR", on_scan_now: Optional[Callable[[], None]] = None) -> Optional[TrayIcon]:
    tray = TrayIcon(tooltip, icon_path, on_restore, on_exit, on_scan_now=on_scan_now)
    if tray.start():
        return tray
    return None

__all__ = ["create_tray", "TrayIcon"]
