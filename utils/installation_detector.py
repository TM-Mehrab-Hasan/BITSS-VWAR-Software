"""
Automatic Installation Detection Module
Detects running installer processes and enables special installation mode automatically.
"""

import os
import psutil
import time
import threading
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Set, Dict, Optional
from utils.logger import log_message
from utils.notify import notify

# Installer process patterns (case-insensitive)
INSTALLER_PROCESS_NAMES = {
    # Common installer executables
    'msiexec.exe',
    'setup.exe',
    'install.exe',
    'installer.exe',
    'uninstaller.exe',
    'update.exe',
    'updater.exe',
    
    # Package managers
    'winget.exe',
    'choco.exe',
    'scoop.exe',
    
    # Software installers
    'steam.exe',
    'epicgameslauncher.exe',
    'origin.exe',
    'battle.net.exe',
    
    # System installers
    'wusa.exe',  # Windows Update Standalone Installer
    'dism.exe',  # Deployment Image Servicing
    'pkgmgr.exe',  # Package Manager
}

# Installer file extensions
INSTALLER_EXTENSIONS = {'.exe', '.msi', '.bat', '.cmd', '.ps1', '.vbs', '.wsf', '.reg', '.scr', '.jar', '.app', '.deb', '.rpm', '.pkg', '.dmg', '.run', '.sh'}

# Installation log file
INSTALLATION_LOG = os.path.join('data', 'installation.log')

# Global logger instance
_installation_logger = None


def get_installation_logger():
    """Get or create the installation logger instance."""
    global _installation_logger
    
    if _installation_logger is not None:
        return _installation_logger
    
    # Create logger
    _installation_logger = logging.getLogger('InstallationDetector')
    _installation_logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers
    if _installation_logger.handlers:
        return _installation_logger
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(INSTALLATION_LOG), exist_ok=True)
    
    # Create rotating file handler (10MB max, 3 backups)
    file_handler = RotatingFileHandler(
        INSTALLATION_LOG,
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    _installation_logger.addHandler(file_handler)
    
    # Log initialization
    _installation_logger.info("=" * 80)
    _installation_logger.info("Installation Detector Initialized")
    _installation_logger.info(f"Log File: {INSTALLATION_LOG}")
    _installation_logger.info("=" * 80)
    
    return _installation_logger


class InstallationDetector:
    """
    Automatically detects running installer processes and tracks installation activity.
    """
    
    def __init__(self):
        self._active_installers: Dict[int, Dict] = {}  # pid -> {name, path, start_time}
        self._monitored_folders: Set[str] = set()  # Folders being installed to
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._logger = get_installation_logger()
        self._notified_installers: Set[int] = set()  # Track which installers we've notified about
        
    def start_monitoring(self):
        """Start background monitoring of installer processes."""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="InstallationDetector"
        )
        self._monitor_thread.start()
        log_message("[INSTALL_DETECT] Started monitoring for installer processes")
        self._logger.info("Installation detector monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        log_message("[INSTALL_DETECT] Stopped monitoring")
        self._logger.info("Installation detector monitoring stopped")
    
    def _monitor_loop(self):
        """Background thread that monitors for installer processes."""
        while self._running:
            try:
                self._check_running_installers()
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                log_message(f"[INSTALL_DETECT] Monitor error: {e}")
                time.sleep(10)
    
    def _check_running_installers(self):
        """Check for running installer processes."""
        current_pids = set()
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'create_time']):
                try:
                    proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                    proc_exe = proc.info['exe']
                    
                    # Check if process is an installer
                    is_installer = False
                    
                    # PRIORITY 1: Check by file extension first (most reliable)
                    if proc_exe:
                        ext = os.path.splitext(proc_exe)[1].lower()
                        if ext in INSTALLER_EXTENSIONS:
                            # Additional check: must have "install", "setup", etc. in name
                            base_name = os.path.basename(proc_exe).lower()
                            if any(word in base_name for word in ['install', 'setup', 'update', 'uninstall', 'upgrade', 'patch']):
                                is_installer = True
                    
                    # PRIORITY 2: Check by process name (fallback)
                    if not is_installer and proc_name in INSTALLER_PROCESS_NAMES:
                        is_installer = True
                    
                    if is_installer:
                        pid = proc.info['pid']
                        current_pids.add(pid)
                        
                        # New installer detected
                        with self._lock:
                            if pid not in self._active_installers:
                                installer_info = {
                                    'name': proc_name,
                                    'path': proc_exe or 'Unknown',
                                    'start_time': datetime.now(),
                                    'create_time': proc.info['create_time']
                                }
                                self._active_installers[pid] = installer_info
                                
                                # Log detection
                                log_message(f"[INSTALL_DETECT] 🔧 Installer detected: {proc_name} (PID: {pid})")
                                self._logger.info(f"INSTALLER_DETECTED | {proc_name} | PID: {pid} | Path: {proc_exe}")
                                
                                # Send notification for new installer
                                if pid not in self._notified_installers:
                                    self._notified_installers.add(pid)
                                    try:
                                        notify(
                                            "🔧 Installation Detected",
                                            f"Installer: {proc_name}\n"
                                            f"Files will be scanned in-place during installation.\n"
                                            f"Only malware will be quarantined."
                                        )
                                    except Exception as e:
                                        log_message(f"[INSTALL_DETECT] Notification failed: {e}")
                                
                                # Try to get installation folder - use parent folder for broader monitoring
                                if proc_exe:
                                    installer_dir = os.path.dirname(proc_exe)
                                    
                                    # Get parent directory for broader coverage
                                    # Example: C:\Users\Ratul\AppData\Local\BraveSoftware\Update
                                    #       -> C:\Users\Ratul\AppData\Local\BraveSoftware
                                    parent_dir = os.path.dirname(installer_dir)
                                    
                                    # Monitor both the installer folder and parent folder
                                    folders_to_monitor = [installer_dir, parent_dir]
                                    
                                    # For system installers (Program Files, WindowsApps), monitor specific app folders
                                    if 'windowsapps' in installer_dir.lower():
                                        # WindowsApps installers create files in same folder structure
                                        folders_to_monitor.append(installer_dir)
                                    elif 'program files' in installer_dir.lower():
                                        # Monitor Program Files parent for app installations
                                        folders_to_monitor.append(parent_dir)
                                    
                                    for folder in folders_to_monitor:
                                        folder_lower = folder.lower()
                                        if folder_lower not in self._monitored_folders:
                                            self._monitored_folders.add(folder_lower)
                                            self._logger.info(f"MONITORING_FOLDER | {folder}")
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Remove completed installers
            with self._lock:
                completed_pids = set(self._active_installers.keys()) - current_pids
                for pid in completed_pids:
                    installer_info = self._active_installers.pop(pid)
                    duration = (datetime.now() - installer_info['start_time']).total_seconds()
                    log_message(f"[INSTALL_DETECT] ✅ Installer completed: {installer_info['name']} (ran {duration:.0f}s)")
                    self._logger.info(f"INSTALLER_COMPLETED | {installer_info['name']} | Duration: {duration:.0f}s")
                    
                    # Remove from notified set
                    self._notified_installers.discard(pid)
        
        except Exception as e:
            log_message(f"[INSTALL_DETECT] Error checking processes: {e}")
    
    def is_installation_active(self) -> bool:
        """Check if any installer is currently running."""
        with self._lock:
            return len(self._active_installers) > 0
    
    def get_active_installers(self) -> list:
        """Get list of currently running installers."""
        with self._lock:
            return [
                {
                    'pid': pid,
                    'name': info['name'],
                    'path': info['path'],
                    'duration': (datetime.now() - info['start_time']).total_seconds()
                }
                for pid, info in self._active_installers.items()
            ]
    
    def is_file_being_installed(self, file_path: str) -> bool:
        """
        Check if a file is part of an active installation.
        Returns True if the file is in a folder being monitored for installation.
        """
        if not self.is_installation_active():
            return False
        
        file_lower = os.path.abspath(file_path).lower()
        
        with self._lock:
            for install_folder in self._monitored_folders:
                if file_lower.startswith(install_folder):
                    self._logger.info(f"FILE_PART_OF_INSTALLATION | {file_path} | Installer folder: {install_folder}")
                    return True
        
        return False
    
    def log_installation_scan(self, file_path: str, status: str, rule: str = None, scan_time_ms: int = None):
        """Log a file scan that happened during installation."""
        time_str = f" | {scan_time_ms}ms" if scan_time_ms else ""
        
        if status == "CLEAN":
            self._logger.info(f"INSTALL_SCAN_CLEAN | {os.path.basename(file_path)}{time_str}")
        elif status == "THREAT":
            self._logger.warning(f"INSTALL_SCAN_THREAT | {os.path.basename(file_path)} | Rule: {rule}{time_str}")
        else:
            self._logger.info(f"INSTALL_SCAN_{status.upper()} | {os.path.basename(file_path)}{time_str}")
    
    def log_installation_quarantine(self, file_path: str, quarantine_path: str, rule: str):
        """Log when a file is quarantined during installation."""
        self._logger.warning(f"INSTALL_QUARANTINE | {file_path} → {quarantine_path} | Rule: {rule}")


# Global singleton instance
_detector_instance: Optional[InstallationDetector] = None


def get_installation_detector() -> InstallationDetector:
    """Get the global installation detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = InstallationDetector()
    return _detector_instance
