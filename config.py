
# ACTIVATION_FILE = "data/activation.json"
# ICON_PATH = "assets/VWAR.ico"
# YARA_RULE_FOLDER = "assets/yara/"
# QUARANTINE_FOLDER = "quarantine"
# BACKUP_FOLDER = "VWARbackup"
CURRENT_VERSION = "3.0.0"

import os
from utils.path_utils import resource_path


# ============================================================
# API ENDPOINTS - All endpoints now require authentication
# ============================================================

# License API
API_LICENSE_FETCH = "https://bitts.fr/vwar_windows/license-fetch"
API_LICENSE_FETCH_KEY = "FDD56B7B7C466581BAD28EDCC83CE"

API_HW_INFO_INSERT = "https://bitts.fr/vwar_windows/hw-info-insert"
API_HW_INFO_INSERT_KEY = "E246F159FBC2B3F39227394CBBD76"

API_AUTO_RENEW = "https://bitts.fr/vwar_windows/autoReNew"
API_AUTO_RENEW_KEY = "47831D7C324F4C929B99AB7D58769"

# Library API (YARA Rules)
API_YARA_INSERT = "https://library.bitss.one/vwar_windows/insert-rule"
API_YARA_INSERT_KEY = "93B78A8977A6617EB2BEDE4235848"

API_YARA_FETCH = "https://library.bitss.one/vwar_windows/fetch-rule"
API_YARA_FETCH_KEY = "7A6D317B24AAE34DD74B9B8E35E5F"

# Legacy endpoints (deprecated - use authenticated endpoints above)
API_GET = API_LICENSE_FETCH  # For backward compatibility
API_POST = API_HW_INFO_INSERT  # For backward compatibility

# Update URL - point to your repository's update info
UPDATE_URL = "https://raw.githubusercontent.com/TM-Mehrab-Hasan/BITSS-VWAR-Software/main/update_info.json"

# License validation polling interval (seconds)
# Set to 3600 for 1-hour real-time enforcement (checks every hour).
# Lower values = more responsive but higher server load.
# Recommended: 3600 (1 hour) for production, 1800 (30 min) for more frequent checks.
LICENSE_VALIDATION_INTERVAL = 30  # 30 second



AUTO_BACKUP_CONFIG_PATH = "data/auto_backup.json"
SCHEDULED_SCAN_CONFIG_PATH = "data/scan_schedule.json"

# === General App Settings ===
APP_NAME = "VWAR Scanner"



# ICON_PATH = resource_path("assets/VWAR.ico")
ICON_PATH = "assets/VWAR.ico"

# === Activation ===
ACTIVATION_FILE = os.path.join("data", "activation.enc")
LICENSE_CACHE_FILE = os.path.join("data", "license_cache.json")

# === Real-Time License Validation Settings ===
# Check intervals (seconds) - adaptive based on expiry proximity
LICENSE_CHECK_INTERVAL_STABLE = 60      # When >30 days remain
LICENSE_CHECK_INTERVAL_NORMAL = 30      # When 8-30 days remain  
LICENSE_CHECK_INTERVAL_URGENT = 10      # When ≤7 days remain
LICENSE_CHECK_INTERVAL_EXPIRED = 5      # When expired (fast renewal detection)

# Offline grace period - how long to allow offline usage (hours)
LICENSE_OFFLINE_GRACE_HOURS = 24

# Warning thresholds (days)
LICENSE_WARNING_DAYS = 7                # Show warning when ≤7 days remain

# === YARA Rule Handling ===
YARA_FOLDER = os.path.join("assets", "yara")

# === Quarantine ===
QUARANTINE_FOLDER = "quarantine"
SCANVAULT_FOLDER = "scanvault"

# === Backup Settings ===
BACKUP_FOLDER = "VWARbackup"
BACKUP_INTERVAL_SECONDS = 30

# === Auto Scan Settings ===
MONITOR_PATHS = [
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/Desktop")
]

# === Log File (optional future use) ===
LOG_FILE = os.path.join("data", "vwar.log")

# === ScanVault Dedicated Logging ===
SCANVAULT_LOG_FILE = os.path.join("data", "scanvault.log")
SCANVAULT_LOG_MAX_SIZE_MB = 10      # Max log file size before rotation
SCANVAULT_LOG_BACKUP_COUNT = 5      # Keep 5 backup logs (scanvault.log.1, .2, etc.)
SCANVAULT_LOG_LEVEL = "INFO"        # Options: DEBUG, INFO, WARNING, ERROR

# === Debug switches ===
# When True, logs old -> new path when following renames (.crdownload/.part to final)
RENAME_FOLLOW_DEBUG = True

# === ScanVault post-restore recheck ===
# Delay (in seconds) before re-scanning the restored file; keep small for faster feedback
POST_RESTORE_RECHECK_DELAY = 4

# === ScanVault Scanning Mode ===
# PERFECT: Sequential scanning (one file at a time) - 100% accuracy, slower
# FAST: Parallel scanning (6 workers) - faster but may miss files under heavy load
# HYBRID: Smart mode - uses parallel for small batches (<5 files), sequential for large batches
# For production security: Use HYBRID for best balance of speed and accuracy
SCANVAULT_MODE = "PERFECT"  # Options: "PERFECT", "FAST", or "HYBRID"

# Hybrid mode thresholds
SCANVAULT_HYBRID_BATCH_THRESHOLD = 5  # Switch to sequential when queue exceeds this
SCANVAULT_HYBRID_MAX_WORKERS = 6      # Parallel workers for small batches

# === Brute Force Attack Protection ===
# Rate limiting (prevents rapid file creation attacks)
MAX_CAPTURES_PER_SECOND = 20          # Maximum files captured per second (0 = unlimited)
MAX_QUEUE_SIZE = 500                   # Maximum files in scan queue (prevents memory exhaustion)
MAX_QUARANTINE_FILES = 1000            # Maximum files in quarantine folder
MAX_QUARANTINE_SIZE_MB = 5000          # Maximum quarantine folder size (5GB)

# Burst protection (allows brief spikes but blocks sustained attacks)
BURST_WINDOW_SECONDS = 10              # Time window for burst detection
MAX_BURST_CAPTURES = 100               # Maximum captures in burst window

# Restoration rate limiting (prevents restore spam attacks)
MAX_RESTORES_PER_MINUTE = 30           # Maximum file restorations per minute

