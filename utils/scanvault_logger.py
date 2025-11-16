"""
Dedicated ScanVault Logger Module
Provides structured logging for ScanVault operations with automatic rotation.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from config import SCANVAULT_LOG_FILE, SCANVAULT_LOG_MAX_SIZE_MB, SCANVAULT_LOG_BACKUP_COUNT, SCANVAULT_LOG_LEVEL

# Global logger instance
_scanvault_logger = None


def get_scanvault_logger():
    """Get or create the ScanVault logger instance."""
    global _scanvault_logger
    
    if _scanvault_logger is not None:
        return _scanvault_logger
    
    # Create logger
    _scanvault_logger = logging.getLogger('ScanVault')
    _scanvault_logger.setLevel(getattr(logging, SCANVAULT_LOG_LEVEL, logging.INFO))
    
    # Prevent duplicate handlers
    if _scanvault_logger.handlers:
        return _scanvault_logger
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(SCANVAULT_LOG_FILE), exist_ok=True)
    
    # Create rotating file handler
    max_bytes = SCANVAULT_LOG_MAX_SIZE_MB * 1024 * 1024
    file_handler = RotatingFileHandler(
        SCANVAULT_LOG_FILE,
        maxBytes=max_bytes,
        backupCount=SCANVAULT_LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    
    # Create formatter with detailed information
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    _scanvault_logger.addHandler(file_handler)
    
    # Log initialization
    _scanvault_logger.info("=" * 80)
    _scanvault_logger.info("ScanVault Logger Initialized")
    _scanvault_logger.info(f"Log File: {SCANVAULT_LOG_FILE}")
    _scanvault_logger.info(f"Max Size: {SCANVAULT_LOG_MAX_SIZE_MB}MB, Backups: {SCANVAULT_LOG_BACKUP_COUNT}")
    _scanvault_logger.info("=" * 80)
    
    return _scanvault_logger


def log_capture(file_path, vaulted_path, event_type="created", success=True, error=None):
    """Log file capture event."""
    logger = get_scanvault_logger()
    
    if success:
        logger.info(f"CAPTURE | {event_type.upper()} | {file_path} → {os.path.basename(vaulted_path)}")
    else:
        logger.error(f"CAPTURE_FAILED | {event_type.upper()} | {file_path} | Error: {error}")


def log_scan(vaulted_path, status, rule=None, scan_time_ms=None):
    """Log file scan event."""
    logger = get_scanvault_logger()
    
    time_str = f" | {scan_time_ms}ms" if scan_time_ms else ""
    
    if status == "CLEAN":
        logger.info(f"SCAN_CLEAN | {os.path.basename(vaulted_path)}{time_str}")
    elif status == "THREAT":
        logger.warning(f"SCAN_THREAT | {os.path.basename(vaulted_path)} | Rule: {rule}{time_str}")
    elif status == "ERROR":
        logger.error(f"SCAN_ERROR | {os.path.basename(vaulted_path)}{time_str}")
    else:
        logger.info(f"SCAN_{status.upper()} | {os.path.basename(vaulted_path)}{time_str}")


def log_restore(vaulted_path, original_path, success=True, error=None):
    """Log file restoration event."""
    logger = get_scanvault_logger()
    
    if success:
        logger.info(f"RESTORE | {os.path.basename(vaulted_path)} → {original_path}")
    else:
        logger.error(f"RESTORE_FAILED | {os.path.basename(vaulted_path)} | Error: {error}")


def log_quarantine(vaulted_path, quarantine_path, rule):
    """Log file quarantine event."""
    logger = get_scanvault_logger()
    logger.warning(f"QUARANTINED | {os.path.basename(vaulted_path)} → {os.path.basename(quarantine_path)} | Rule: {rule}")


def log_rate_limit(limit_type, current_value, max_value):
    """Log rate limiting event."""
    logger = get_scanvault_logger()
    logger.warning(f"RATE_LIMIT | {limit_type} | Current: {current_value}, Max: {max_value}")


def log_duplicate(file_path, signature):
    """Log duplicate file suppression."""
    logger = get_scanvault_logger()
    logger.debug(f"DUPLICATE | {file_path} | Signature: {signature[:16]}...")


def log_mode_switch(mode_from, mode_to, reason):
    """Log scanning mode switch (HYBRID mode)."""
    logger = get_scanvault_logger()
    logger.info(f"MODE_SWITCH | {mode_from} → {mode_to} | Reason: {reason}")


def log_statistics(stats_dict):
    """Log statistics summary."""
    logger = get_scanvault_logger()
    logger.info(f"STATS | {stats_dict}")


def log_error(operation, error, file_path=None):
    """Log error event."""
    logger = get_scanvault_logger()
    
    if file_path:
        logger.error(f"ERROR | {operation} | {file_path} | {error}")
    else:
        logger.error(f"ERROR | {operation} | {error}")
