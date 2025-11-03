import os
import sys
import ctypes
import tkinter as tk
from activation.license_utils import is_activated, LicenseValidator
from activation.gui import show_activation_window
from app_main import VWARScannerGUI
from utils.update_checker import check_for_updates
from tkinter import messagebox
import subprocess
import time
import argparse
from utils.startup import is_startup_enabled
from utils.tray import create_tray
from config import ICON_PATH
from utils.notify import notify
import atexit
import shutil

# Suppress PyInstaller temp folder cleanup warnings
def cleanup_pyinstaller_temp():
    """Ensure all subprocesses are terminated before exit."""
    global _monitor_process
    
    # Kill monitor process if still running
    if _monitor_process:
        try:
            _monitor_process.terminate()
            _monitor_process.wait(timeout=1)
        except Exception:
            try:
                _monitor_process.kill()
            except Exception:
                pass
    
    # Kill any remaining vwar_monitor.exe processes
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "vwar_monitor.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=2
        )
    except Exception:
        pass

# Register cleanup handler
atexit.register(cleanup_pyinstaller_temp)

def is_admin():
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Relaunch the script with admin rights if not already."""
    script = os.path.abspath(sys.argv[0])
    params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)

def already_running():
    """Check if VWAR.exe is already running."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq VWAR.exe"],
            stdout=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        lines = result.stdout.strip().splitlines()
        process_lines = [line for line in lines if "VWAR.exe" in line]
        if len(process_lines) > 2:  # More than one instance
            return True
    except Exception as e:
        print(f"[WARNING] Failed to check running tasks: {e}")
    return False

def check_exe_name():
    """Ensure executable is named correctly."""
    exe_name = os.path.basename(sys.argv[0])
    if exe_name.lower() != "vwar.exe":
        messagebox.showerror("Invalid File", "Executable must be named VWAR.exe")
        sys.exit()

# Global monitor process reference
_monitor_process = None

def run_vwar_monitor():
    """Start the C++ monitor process silently."""
    global _monitor_process
    
    if getattr(sys, 'frozen', False):
        # PyInstaller bundle
        base_path = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable)
    else:
        # Dev mode
        base_path = os.path.dirname(os.path.abspath(__file__))

    # The native monitor lives in the 'vwar_monitor' subfolder. Resolve the
    # executable path accordingly so it works in both dev and PyInstaller
    # frozen bundles where datas include the 'vwar_monitor' directory.
    monitor_path = os.path.join(base_path, "vwar_monitor", "vwar_monitor.exe")

    if os.path.exists(monitor_path):
        try:                                                                                        
            _monitor_process = subprocess.Popen(
                [monitor_path],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            print("[INFO] VWAR Monitor started.")
        except Exception as e:
            print("[ERROR] Failed to start VWAR Monitor:", e)
    else:
        print("[WARNING] VWAR Monitor not found:", monitor_path)

def stop_vwar_monitor():
    """Stop the C++ monitor process."""
    global _monitor_process
    
    if _monitor_process:
        try:
            _monitor_process.terminate()
            _monitor_process.wait(timeout=3)
            print("[INFO] VWAR Monitor stopped.")
        except Exception as e:
            print(f"[WARNING] Failed to stop VWAR Monitor gracefully: {e}")
            try:
                _monitor_process.kill()
            except Exception:
                pass
    
    # Also try to kill any remaining vwar_monitor.exe processes
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "vwar_monitor.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        pass

def main():
    # CRITICAL: Set working directory to executable location
    # This ensures data folders are created in the correct location
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        exe_dir = os.path.dirname(sys.executable)
        os.chdir(exe_dir)
        print(f"[INFO] Working directory set to: {exe_dir}")
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--silent", action="store_true", help="Run services only (no GUI)")
    parser.add_argument("--tray", action="store_true", help="Start minimized to system tray")
    parser.add_argument("--help", action="store_true", help="Show help and exit")
    parser.add_argument("--no-admin", action="store_true", help="Skip admin check (dev mode)")
    args, unknown = parser.parse_known_args()
    if args.help:
        print("VWAR Scanner options:\n  --silent   Run background services only (monitor, scheduler)\n  --tray     Start to system tray; GUI shown when icon clicked\n  --no-admin Skip admin elevation (for development)\n  --help     Show this help")
        return
    # check_exe_name()
    
    # Check if already running (skip in dev mode)
    if not args.no_admin and already_running():
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("VWAR Scanner", "VWAR is already running.")
        sys.exit()

    # Step 1: Elevate to admin (skip if --no-admin flag or running from Python directly)
    if not args.no_admin and not is_admin():
        # Only relaunch if running from compiled .exe
        if getattr(sys, 'frozen', False):
            print("[INFO] Not running as admin. Relaunching...")
            run_as_admin()
            return
        else:
            print("[WARNING] Running in development mode without admin privileges.")
            print("[INFO] Some features (real-time monitoring) may not work properly.")
            print("[TIP] Use 'python main.py --no-admin' to suppress this warning.")

    # Step 2: Check activation
    activated, reason = is_activated()
    if not activated:
        print(f"[INFO] Activation check failed: {reason}")
        show_activation_window(reason=reason)
        return

    # Step 3: Check for updates
    check_for_updates()

    # Step 4: Start background monitor
    run_vwar_monitor()

    # Step 5: Launch main GUI unless --silent
    if args.silent:
        print("[INFO] Silent mode: GUI not started (services running if any threads started in imports).")
        # Keep process alive minimally for scheduled scanning / monitoring; spin sleep loop
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            return
    else:
        # Normal mode: Create GUI with system tray integration
        print("[INFO] Launching VWAR Scanner GUI with system tray...")
        root = tk.Tk()
        
        # Start minimized to tray if --tray flag is set
        if args.tray:
            root.withdraw()
        
        app = VWARScannerGUI(root)
        
        # Define license validation callbacks
        def on_license_invalid(reason):
            """Called when license becomes invalid during runtime."""
            print(f"[LICENSE] License invalidated: {reason}")
            # Notify user
            try:
                notify("⚠️ License Invalid", f"Your license is no longer valid.\n{reason}")
            except Exception:
                pass
            # Trigger graceful degradation
            app.degrade_to_view_only(reason)
        
        def on_expiry_warning(days_left):
            """Called when license is expiring soon (7 days or less)."""
            print(f"[LICENSE] Expiry warning: {days_left} days remaining")
            
            # Update warning banner on home page
            try:
                app.schedule_gui(app.update_expiry_warning, days_left)
            except Exception:
                pass
            
            # Send toast notification (once per day)
            try:
                notify("⏰ License Expiring Soon", 
                       f"Your license expires in {days_left} day(s).\nPlease renew to continue using VWAR Scanner.")
            except Exception:
                pass
        
        def on_license_valid():
            """Called when license becomes valid again (after renewal)."""
            print(f"[LICENSE] License renewed - restoring full functionality")
            # Notify user
            try:
                notify("✅ License Renewed", "Your license has been renewed!\nAll features are now enabled.")
            except Exception:
                pass
            # Restore from view-only mode
            app.restore_from_view_only()
        
        # Start real-time license validation
        license_validator = LicenseValidator(
            on_invalid_callback=on_license_invalid,
            on_expiry_warning_callback=on_expiry_warning,
            on_valid_callback=on_license_valid,
            app_instance=app  # Pass app reference for timer reset
        )
        license_validator.start()
        
        # Store validator reference for cleanup
        app.license_validator = license_validator
        
        # Start ScanVault processor immediately to handle vaulted files
        try:
            from Scanning.vault_processor import start_vault_processor
            start_vault_processor()
            print("[INFO] ScanVault processor started")
        except Exception as e:
            print(f"[WARNING] Failed to start ScanVault processor: {e}")
        
        # Real-time update checker not needed - using simple version
        # from utils.update_checker import start_update_checker
        # update_checker = start_update_checker(app_instance=app)
        # app.update_checker = update_checker
        
        # Create tray icon functions
        def restore():
            try:
                root.deiconify()
                root.state('normal')
                root.after(0, lambda: root.lift())
                root.focus_force()
            except Exception as e:
                print(f"[TRAY] Restore failed: {e}")
        
        def exit_app():
            try:
                # Stop monitoring and cleanup
                if hasattr(app, 'on_close'):
                    app.on_close()
                
                # Stop the C++ monitor process
                stop_vwar_monitor()
                
                # Give threads a moment to clean up
                time.sleep(0.5)
                
                # Destroy root window
                try:
                    root.quit()
                    root.destroy()
                except Exception:
                    pass
                
            except Exception as e:
                print(f"[ERROR] Exit error: {e}")
            finally:
                # Use sys.exit instead of os._exit to allow proper cleanup
                sys.exit(0)
        
        def scan_now():
            try:
                # Restore window first
                restore()
                # Show scan page
                if hasattr(app, 'pages') and "scan" in app.pages:
                    app.show_page("scan")
            except Exception as e:
                print(f"[TRAY] Scan now failed: {e}")
        
        # Create system tray icon
        tray = create_tray(restore, exit_app, ICON_PATH, on_scan_now=scan_now)
        
        # Store tray reference in app for access
        app.tray_icon = tray
        
        root.mainloop()

if __name__ == "__main__":
    main()

