"""Windows startup integration utilities.

Provides functions to enable/disable application auto start when the
current user logs into Windows. Implements HKCU Run key approach to avoid
extra dependencies (no shortcut creation libraries required).

Safe to import on non-Windows platforms (functions become no-ops that
return False) but primary target is Windows.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

try:  # Windows-only imports
    import winreg  # type: ignore
except ImportError:  # pragma: no cover - non Windows environment
    winreg = None  # type: ignore

try:
    from utils.logger import log_message
    from utils.settings import SETTINGS
except Exception:  # Fallback if logger not available early
    def log_message(msg: str):  # type: ignore
        print(msg)

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_VALUE = "VWARScanner"  # Registry value name


def _is_windows() -> bool:
    return os.name == "nt" and winreg is not None  # type: ignore


def get_executable_path() -> str:
    """Return the full path that should be launched at startup.

    If bundled with PyInstaller (sys.frozen) return the executable path,
    else return the current script absolute path.
    """
    if getattr(sys, "frozen", False):  # PyInstaller / frozen
        return sys.executable
    return os.path.abspath(sys.argv[0])


def enable_startup() -> bool:
    """Add/overwrite registry Run entry for current user.

    Returns True on success, False on failure.
    """
    if not _is_windows():
        log_message("[STARTUP] enable_startup called on non-Windows platform – ignored")
        return False
    exe_path = get_executable_path()
    if SETTINGS.startup_tray:
        exe_path = f"{exe_path} --tray"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)  # type: ignore
        winreg.SetValueEx(key, APP_REG_VALUE, 0, winreg.REG_SZ, f'"{exe_path}"')  # type: ignore
        winreg.CloseKey(key)  # type: ignore
        log_message(f"[STARTUP] Enabled auto start: {exe_path}")
        return True
    except Exception as e:  # pragma: no cover - registry specific
        log_message(f"[STARTUP] Failed enabling auto start: {e}")
        return False


def disable_startup() -> bool:
    """Remove registry Run entry. Returns True if removed or absent."""
    if not _is_windows():
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)  # type: ignore
        try:
            winreg.DeleteValue(key, APP_REG_VALUE)  # type: ignore
            log_message("[STARTUP] Disabled auto start")
        except FileNotFoundError:
            pass  # Already absent
        winreg.CloseKey(key)  # type: ignore
        return True
    except Exception as e:  # pragma: no cover
        log_message(f"[STARTUP] Failed disabling auto start: {e}")
        return False


def is_startup_enabled() -> bool:
    """Check if registry Run entry exists and points to an existing path."""
    if not _is_windows():
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ)  # type: ignore
        try:
            val, _ = winreg.QueryValueEx(key, APP_REG_VALUE)  # type: ignore
            winreg.CloseKey(key)  # type: ignore
            if not val:
                return False
            # Strip surrounding quotes if present
            cleaned = val.strip().strip('"')
            return os.path.exists(cleaned)
        except FileNotFoundError:
            winreg.CloseKey(key)  # type: ignore
            return False
    except Exception:
        return False


__all__ = [
    "enable_startup",
    "disable_startup",
    "is_startup_enabled",
    "get_executable_path",
]
