"""
Installation Mode Module for ScanVault
Helps reduce false positives during software installation.
"""

import os
import time
import threading
from typing import Set, Optional
from utils.logger import log_message

# Common installer file extensions to auto-skip
INSTALLER_EXTENSIONS = {
    '.msi', '.exe', '.dll', '.sys', '.ocx', '.scr',
    '.cab', '.inf', '.cat', '.drv', '.cpl',
    '.tmp', '.temp', '.dat', '.bin'
}

# Trusted installer download folders (common locations)
TRUSTED_INSTALLER_PATHS = {
    'windows\\installer',
    'windows\\winsxs',
    'windows\\softwaredistribution',
    'programdata\\package cache',
    'appdata\\local\\temp',
    'appdata\\local\\microsoft\\windows\\inetcache'
}


class InstallationMode:
    """Manages temporary installation mode to skip scanning installer files."""
    
    def __init__(self):
        self._active = False
        self._lock = threading.Lock()
        self._end_time: Optional[float] = None
        self._timer_thread: Optional[threading.Thread] = None
        self._trusted_folders: Set[str] = set()
        
    def is_active(self) -> bool:
        """Check if installation mode is currently active."""
        with self._lock:
            if self._active and self._end_time:
                # Auto-disable if time expired
                if time.time() >= self._end_time:
                    self._deactivate_internal()
            return self._active
    
    def activate(self, duration_minutes: int = 10):
        """Activate installation mode for specified duration."""
        with self._lock:
            if self._active:
                log_message(f"[INSTALL_MODE] Already active, extending duration to {duration_minutes} min")
            else:
                log_message(f"[INSTALL_MODE] Activated for {duration_minutes} minutes")
            
            self._active = True
            self._end_time = time.time() + (duration_minutes * 60)
            
            # Start timer thread to auto-deactivate
            if self._timer_thread and self._timer_thread.is_alive():
                pass  # Will auto-expire based on _end_time
            else:
                self._timer_thread = threading.Thread(
                    target=self._timer_loop,
                    daemon=True,
                    name="InstallModeTimer"
                )
                self._timer_thread.start()
    
    def deactivate(self):
        """Manually deactivate installation mode."""
        with self._lock:
            self._deactivate_internal()
    
    def _deactivate_internal(self):
        """Internal deactivation (must hold lock)."""
        if self._active:
            self._active = False
            self._end_time = None
            log_message("[INSTALL_MODE] Deactivated")
    
    def _timer_loop(self):
        """Background thread to auto-deactivate after duration."""
        while True:
            time.sleep(10)  # Check every 10 seconds
            with self._lock:
                if not self._active:
                    break
                if self._end_time and time.time() >= self._end_time:
                    self._deactivate_internal()
                    break
    
    def get_remaining_time(self) -> int:
        """Get remaining time in seconds, or 0 if inactive."""
        with self._lock:
            if not self._active or not self._end_time:
                return 0
            remaining = int(self._end_time - time.time())
            return max(0, remaining)
    
    def add_trusted_folder(self, folder_path: str):
        """Add a folder to trusted installation locations."""
        normalized = os.path.abspath(folder_path).lower()
        with self._lock:
            self._trusted_folders.add(normalized)
            log_message(f"[INSTALL_MODE] Added trusted folder: {folder_path}")
    
    def remove_trusted_folder(self, folder_path: str):
        """Remove a folder from trusted installation locations."""
        normalized = os.path.abspath(folder_path).lower()
        with self._lock:
            self._trusted_folders.discard(normalized)
            log_message(f"[INSTALL_MODE] Removed trusted folder: {folder_path}")
    
    def get_trusted_folders(self) -> Set[str]:
        """Get copy of trusted folders set."""
        with self._lock:
            return self._trusted_folders.copy()
    
    def should_skip_file(self, file_path: str) -> bool:
        """
        Determine if a file should be skipped from ScanVault.
        
        Returns True if:
        - Installation mode is active AND file is installer-related
        - File is in a trusted installer location
        - File has installer extension
        """
        if not os.path.exists(file_path):
            return False
        
        file_lower = file_path.lower()
        file_ext = os.path.splitext(file_lower)[1]
        
        # Check if file is in a trusted system installer path
        for trusted_path in TRUSTED_INSTALLER_PATHS:
            if trusted_path in file_lower:
                log_message(f"[INSTALL_MODE] Skipping file in trusted path: {file_path}")
                return True
        
        # Check if file is in user-defined trusted folder
        with self._lock:
            file_abs = os.path.abspath(file_path).lower()
            for trusted_folder in self._trusted_folders:
                if file_abs.startswith(trusted_folder):
                    log_message(f"[INSTALL_MODE] Skipping file in user-trusted folder: {file_path}")
                    return True
        
        # If installation mode active, skip installer files
        if self.is_active():
            if file_ext in INSTALLER_EXTENSIONS:
                log_message(f"[INSTALL_MODE] Skipping installer file (mode active): {file_path}")
                return True
        
        return False


# Global singleton instance
_installation_mode_instance: Optional[InstallationMode] = None


def get_installation_mode() -> InstallationMode:
    """Get the global installation mode instance."""
    global _installation_mode_instance
    if _installation_mode_instance is None:
        _installation_mode_instance = InstallationMode()
    return _installation_mode_instance
