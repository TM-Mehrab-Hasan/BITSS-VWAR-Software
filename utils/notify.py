from utils.logger import log_message
from utils.path_utils import resource_path

# Optional backends imported at module level so packagers (PyInstaller) pick them up
try:
    from plyer import notification as _plyer_notification  # type: ignore
except Exception:  # pragma: no cover
    _plyer_notification = None  # type: ignore

try:
    from win10toast import ToastNotifier as _ToastNotifier  # type: ignore
except Exception:  # pragma: no cover
    _ToastNotifier = None  # type: ignore

# Optional pywin32 for balloon fallback
try:
    import win32api  # type: ignore
    import win32con  # type: ignore
    import win32gui  # type: ignore
    import win32gui_struct  # type: ignore
except Exception:  # pragma: no cover
    win32api = win32con = win32gui = win32gui_struct = None  # type: ignore

def _icon_path() -> str | None:
    """Resolve app icon in both dev and PyInstaller runtime."""
    try:
        icon = resource_path("assets/VWAR.ico")
        return icon if icon and os.path.exists(icon) else None
    except Exception:
        return None


import os


# Global toaster instance (thread-safe when used with threaded=True)
_toaster_instance = None

def _get_toaster():
    """Get or create the global ToastNotifier instance."""
    global _toaster_instance
    if _toaster_instance is None and _ToastNotifier is not None:
        try:
            _toaster_instance = _ToastNotifier()
        except Exception:
            pass
    return _toaster_instance


def notify(title: str, message: str, duration: int = 10) -> bool:
    """Send a desktop notification.

    Tries multiple backends in order:
    1) plyer (most stable, cross-platform)
    2) win10toast (Windows toast - has some stderr noise but works)
    3) pywin32 balloon (fallback)

    Returns True on success, False otherwise. Logs any errors.
    """
    icon = _icon_path()

    # Backend 1: plyer (most stable)
    try:
        if _plyer_notification is not None:
            # Some plyer backends accept app_icon; ignore if not supported
            kwargs = {"title": title, "message": message, "timeout": duration}
            if icon:
                kwargs["app_icon"] = icon  # type: ignore[assignment]
            _plyer_notification.notify(**kwargs)
            log_message("[NOTIFY] Dispatched via plyer")
            return True
    except Exception as e:
        log_message(f"[NOTIFY][plyer] failed: {e}")

    # Backend 2: win10toast (non-blocking with threaded=True)
    try:
        toaster = _get_toaster()
        if toaster is not None:
            # threaded=True makes show_toast non-blocking by running in its own thread
            # Must be called from main thread, but it spawns worker thread internally
            import threading
            import sys
            import io
            
            # Temporarily suppress stderr to hide win10toast's internal thread warnings
            old_stderr = sys.stderr
            sys.stderr = io.StringIO()
            
            try:
                result = toaster.show_toast(
                    title, 
                    message, 
                    icon_path=icon, 
                    duration=duration, 
                    threaded=True  # This spawns internal thread, returns immediately
                )
                log_message("[NOTIFY] Dispatched via win10toast (threaded)")
                return True
            finally:
                # Restore stderr
                sys.stderr = old_stderr
    except Exception as e:
        log_message(f"[NOTIFY][win10toast] failed: {e}")

    # Backend 3: Windows tray balloon via pywin32
    try:
        if win32gui is not None:
            # Create a temporary, hidden window with tray icon and show a balloon
            class_name = "VWARNotifyClass"
            message_map = {win32con.WM_DESTROY: (lambda h, m, w, l: None)}  # type: ignore
            wc = win32gui.WNDCLASS()  # type: ignore
            hinst = wc.hInstance = win32api.GetModuleHandle(None)  # type: ignore
            wc.lpszClassName = class_name
            wc.lpfnWndProc = message_map  # type: ignore
            try:
                atom = win32gui.RegisterClass(wc)  # type: ignore
            except Exception:
                atom = win32gui.GetClassInfo(hinst, class_name)  # type: ignore
            hwnd = win32gui.CreateWindowEx(0, atom, "VWARNotifyWnd", 0, 0, 0, 0, 0, 0, 0, hinst, None)  # type: ignore
            # Load icon
            try:
                hicon = win32gui.LoadImage(hinst, icon, win32con.IMAGE_ICON, 0, 0, win32con.LR_LOADFROMFILE) if icon else win32gui.LoadIcon(0, win32con.IDI_APPLICATION)  # type: ignore
            except Exception:
                hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)  # type: ignore
            flags = win32con.NIF_ICON | win32con.NIF_MESSAGE | win32con.NIF_TIP  # type: ignore
            nid = (hwnd, 0, flags, win32con.WM_USER + 20, hicon, "VWAR")  # type: ignore
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)  # type: ignore
            # Show balloon
            NIIF_INFO = 0x00000001
            balloon = (hwnd, 0, win32con.NIF_INFO, win32con.WM_USER + 20, hicon, "VWAR", message, duration * 1000, title, NIIF_INFO)  # type: ignore
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, balloon)  # type: ignore
                log_message("[NOTIFY] Dispatched via tray balloon")
                # Schedule cleanup on a short timer in background thread
                import threading, time as _t
                def _cleanup():
                    _t.sleep(max(3, duration + 1))
                    try:
                        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)  # type: ignore
                        win32gui.DestroyWindow(hwnd)  # type: ignore
                    except Exception:
                        pass
                threading.Thread(target=_cleanup, daemon=True).start()
                return True
            except Exception as e:
                # Cleanup on failure
                try:
                    win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)  # type: ignore
                    win32gui.DestroyWindow(hwnd)  # type: ignore
                except Exception:
                    pass
                log_message(f"[NOTIFY][tray] failed: {e}")
    except Exception as e:
        log_message(f"[NOTIFY][tray-init] failed: {e}")

        log_message("[NOTIFY] All backends failed; falling back to log only")
        return False


def show_app_notification(root, title: str, message: str, duration: int = 5000, 
                          bg_color: str = "#009AA5", title_color: str = "white"):
    """
    Show an animated slide-in notification inside the app (alternative to system notifications).
    
    Args:
        root: Tkinter root window
        title: Notification title
        message: Notification message
        duration: Time to display in milliseconds (default 5000ms = 5s)
        bg_color: Background color (default teal theme)
        title_color: Title text color
    
    ✨ Features smooth slide-in from bottom-right with fade-out animation.
    """
    try:
        from tkinter import Toplevel, Label, Frame
        
        # Create notification window (no border, always on top)
        notif = Toplevel(root)
        notif.overrideredirect(True)
        notif.attributes("-topmost", True)
        notif.config(bg=bg_color)
        
        # Content frame
        content = Frame(notif, bg=bg_color, bd=2, relief="raised")
        content.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Title label
        Label(content, text=title, font=("Arial", 12, "bold"),
              bg=bg_color, fg=title_color).pack(anchor="w", padx=10, pady=(8, 2))
        
        # Message label
        Label(content, text=message, font=("Arial", 10),
              bg=bg_color, fg="white", wraplength=280, justify="left").pack(anchor="w", padx=10, pady=(2, 8))
        
        # Calculate position (bottom-right corner)
        notif.update_idletasks()
        width = 320
        height = notif.winfo_reqheight()
        screen_width = notif.winfo_screenwidth()
        screen_height = notif.winfo_screenheight()
        
        # Start position (off-screen to the right)
        start_x = screen_width
        end_x = screen_width - width - 20
        y = screen_height - height - 60
        
        notif.geometry(f"{width}x{height}+{start_x}+{y}")
        
        # ✨ Slide-in animation (smooth 20-step movement)
        def slide_in(step=0):
            if step < 20:
                current_x = start_x + int((end_x - start_x) * (step / 20))
                notif.geometry(f"{width}x{height}+{current_x}+{y}")
                root.after(15, lambda: slide_in(step + 1))  # 15ms per frame = 300ms total
            else:
                # After slide-in complete, schedule fade-out
                root.after(duration, lambda: fade_out(notif, 1.0))
        
        # ✨ Fade-out animation (opacity reduction)
        def fade_out(window, alpha):
            try:
                if alpha > 0:
                    window.attributes("-alpha", alpha)
                    root.after(50, lambda: fade_out(window, alpha - 0.1))  # 50ms per step
                else:
                    window.destroy()
            except Exception:
                pass  # Window already destroyed
        
        # Start animation
        slide_in()
        
        return True
    except Exception as e:
        log_message(f"[APP_NOTIFY] Failed to show notification: {e}")
        return False
