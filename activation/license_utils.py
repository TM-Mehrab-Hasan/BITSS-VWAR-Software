import os
import requests
import json
import threading
import time
import socket
from datetime import datetime, timedelta
from config import (
    ACTIVATION_FILE, 
    LICENSE_CACHE_FILE,
    API_LICENSE_FETCH, 
    API_LICENSE_FETCH_KEY,
    LICENSE_CHECK_INTERVAL_STABLE,
    LICENSE_CHECK_INTERVAL_NORMAL,
    LICENSE_CHECK_INTERVAL_URGENT,
    LICENSE_CHECK_INTERVAL_EXPIRED,
    LICENSE_OFFLINE_GRACE_HOURS,
    LICENSE_WARNING_DAYS,
    API_YARA_FETCH,
    API_YARA_FETCH_KEY,
    YARA_FOLDER
)
from activation.hwid import get_processor_info, get_motherboard_info
from cryptography.fernet import Fernet
import base64, hashlib


def generate_fernet_key_from_string(secret_string):
    sha256 = hashlib.sha256(secret_string.encode()).digest()
    return base64.urlsafe_b64encode(sha256)

SECRET_KEY = generate_fernet_key_from_string("VWAR@BIFIN")
fernet = Fernet(SECRET_KEY)


# ============================================================================
# NETWORK CHECK UTILITY
# ============================================================================

def is_network_available():
    """Quick check if network is available.
    
    Returns:
        bool: True if network is available, False otherwise
    """
    try:
        socket.setdefaulttimeout(2)
        socket.getaddrinfo('google.com', 80)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False


# ============================================================================
# LICENSE CACHE MANAGER
# ============================================================================

class LicenseCacheManager:
    """Manages the license validity cache for offline/online operation."""
    
    def __init__(self, cache_path=LICENSE_CACHE_FILE):
        self.cache_path = cache_path
        self._lock = threading.Lock()
        
    def read_cache(self):
        """Read license cache from file.
        
        Returns:
            dict: Cache data or None if not available
        """
        with self._lock:
            try:
                if not os.path.exists(self.cache_path):
                    return None
                    
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CACHE] Failed to read cache: {e}")
                return None
    
    def write_cache(self, is_valid, valid_until, days_remaining, network_status="online"):
        """Write license cache to file.
        
        Args:
            is_valid (bool): Whether license is currently valid
            valid_until (str): Expiry datetime string
            days_remaining (int): Days until expiry
            network_status (str): 'online' or 'offline'
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
                
                cache_data = {
                    "is_valid": is_valid,
                    "valid_until": valid_until,
                    "last_server_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "days_remaining": days_remaining,
                    "network_status": network_status,
                    "offline_since": None if network_status == "online" else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Atomic write via temp file
                tmp_path = self.cache_path + ".tmp"
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2)
                os.replace(tmp_path, self.cache_path)
                
                return True
            except Exception as e:
                print(f"[CACHE] Failed to write cache: {e}")
                return False
    
    def is_cache_stale(self, grace_hours=LICENSE_OFFLINE_GRACE_HOURS):
        """Check if cache is too old to trust.
        
        Args:
            grace_hours (int): Maximum hours without server check
            
        Returns:
            bool: True if cache is stale
        """
        cache = self.read_cache()
        if not cache:
            return True
            
        try:
            last_check_str = cache.get("last_server_check")
            if not last_check_str:
                return True
                
            last_check = datetime.strptime(last_check_str, "%Y-%m-%d %H:%M:%S")
            hours_since = (datetime.now() - last_check).total_seconds() / 3600
            
            return hours_since > grace_hours
        except Exception:
            return True


# ============================================================================
# ACTIVATION STORAGE (with cross-process locking)
# ============================================================================

def _store_activation(record, cpu, mobo, auto_renew=None):
    """Save activation info locally to encrypted activation file with cross-process lock.
    
    Args:
        record: Server record dictionary
        cpu: Processor ID
        mobo: Motherboard ID
        auto_renew: Auto-renew status. If None, will extract from record["auto_renew"]
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(ACTIVATION_FILE), exist_ok=True)

        # If auto_renew not explicitly provided, extract from server record
        if auto_renew is None:
            auto_renew = record.get("auto_renew", "NO")
        
        # Ensure auto_renew is in correct format (string "YES"/"NO")
        if isinstance(auto_renew, bool):
            auto_renew = "YES" if auto_renew else "NO"
        elif isinstance(auto_renew, str):
            # Normalize to uppercase YES/NO
            auto_renew = "YES" if auto_renew.upper() == "YES" else "NO"
        else:
            auto_renew = "NO"  # Default fallback

        data = {
            "id": record.get("id"),
            "username": record.get("username"),
            "password": record.get("password"),
            "processor_id": cpu,
            "motherboard_id": mobo,
            "valid_till": record.get("valid_till"),
            "created_at": record.get("created_at", ""),
            "auto_renew": auto_renew
        }

        # Helper: simple cross-process lock using atomic lockfile creation
        lock_path = ACTIVATION_FILE + ".lock"

        def _acquire_lock(path, timeout=5.0, poll=0.08):
            """Try to create a lockfile atomically. Return True if acquired."""
            deadline = time.time() + timeout
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            mode = 0o600
            while True:
                try:
                    fd = os.open(path, flags, mode)
                    # Write pid/timestamp for diagnostics
                    try:
                        os.write(fd, f"pid:{os.getpid()}\n".encode('utf-8'))
                    except Exception:
                        pass
                    os.close(fd)
                    return True
                except FileExistsError:
                    if time.time() > deadline:
                        return False
                    time.sleep(poll)
                except Exception:
                    # Unexpected error creating lock file
                    return False

        def _release_lock(path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

        acquired = _acquire_lock(lock_path, timeout=5.0)
        if not acquired:
            print(f"[ERROR] Could not acquire activation file lock: {lock_path}")
            return False

        try:
            # Write to a temp file then atomically replace to avoid partial writes
            tmp_path = ACTIVATION_FILE + ".tmp"
            json_str = json.dumps(data).encode("utf-8")
            encrypted = fernet.encrypt(json_str)
            with open(tmp_path, "wb") as f:
                f.write(encrypted)
            # Atomic replace
            os.replace(tmp_path, ACTIVATION_FILE)
            print("[INFO] Activation info stored.")
            return True
        finally:
            # Ensure lock is released
            try:
                _release_lock(lock_path)
            except Exception:
                pass
    except Exception as e:
        print(f"[ERROR] Failed to store activation: {e}")
        return False


def get_auto_renew_status():
    """Get the current auto-renew status from local activation file."""
    try:
        if not os.path.exists(ACTIVATION_FILE):
            return False
        
        with open(ACTIVATION_FILE, "rb") as f:
            encrypted = f.read()
            decrypted = fernet.decrypt(encrypted)
            data = json.loads(decrypted.decode("utf-8"))
        
        # Handle both boolean and string values from database
        auto_renew = data.get("auto_renew", False)
        
        # Convert string "YES"/"NO" to boolean if needed
        if isinstance(auto_renew, str):
            return auto_renew.upper() == "YES"
        
        return bool(auto_renew)
    except Exception as e:
        print(f"[ERROR] Failed to get auto-renew status: {e}")
        return False


def update_auto_renew_status(enabled):
    """
    Update auto-renew status locally and sync with server.
    
    Args:
        enabled (bool): Whether auto-renew should be enabled
        
    Returns:
        tuple: (success: bool, message: str)
    """
    from config import API_AUTO_RENEW, API_AUTO_RENEW_KEY
    
    try:
        # Load current activation data
        if not os.path.exists(ACTIVATION_FILE):
            return False, "Activation file not found. Please activate first."
        
        with open(ACTIVATION_FILE, "rb") as f:
            encrypted = f.read()
            decrypted = fernet.decrypt(encrypted)
            data = json.loads(decrypted.decode("utf-8"))
        
        license_id = data.get("id")
        if not license_id:
            return False, "License ID not found in activation data."
        
        # ⚠️ VALIDATION: Check if trying to enable auto-renew with <30 days remaining
        if enabled:
            valid_till = data.get("valid_till")
            if valid_till:
                try:
                    end_date = datetime.strptime(valid_till, "%Y-%m-%d %H:%M:%S")
                    days_remaining = (end_date - datetime.now()).days
                    
                    if days_remaining < 30:
                        return False, (
                            f"❌ Cannot Enable Auto-Renew\n\n"
                            f"License validity remaining: {days_remaining} days\n\n"
                            f"Auto-renew can only be enabled when more than 30 days remain.\n\n"
                            f"Please contact support to renew your license manually:\n"
                            f"📧 support@bobosohomail.com\n"
                            f"🌐 www.bitss.one"
                        )
                except Exception as e:
                    print(f"[AUTO-RENEW] Could not parse valid_till date: {e}")
        
        # Update auto-renew on server
        # Database expects "YES" or "NO" strings
        payload = {
            "id": license_id,
            "auto_renew": "YES" if enabled else "NO"
        }
        
        headers = {
            "X-API-Key": API_AUTO_RENEW_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.post(API_AUTO_RENEW, json=payload, headers=headers, timeout=10)
        
        # Check if response is valid JSON
        try:
            result = response.json()
        except json.JSONDecodeError:
            return False, f"Server returned invalid response (Status: {response.status_code}). Please check API endpoint."
        
        if result.get("status") == "success":
            # Update local file with string value to match database format
            data["auto_renew"] = "YES" if enabled else "NO"
            json_str = json.dumps(data).encode("utf-8")
            encrypted = fernet.encrypt(json_str)
            with open(ACTIVATION_FILE, "wb") as f:
                f.write(encrypted)
            
            status_text = "enabled" if enabled else "disabled"
            return True, f"Auto-renew {status_text} successfully."
        else:
            error_msg = result.get("message", result.get("error", "Server rejected auto-renew update."))
            return False, f"Failed to update auto-renew: {error_msg}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {e}"
    except json.JSONDecodeError as e:
        return False, f"Invalid server response. API may not be configured correctly."
    except Exception as e:
        return False, f"Error updating auto-renew: {e}"


def is_activated():
    """
    Return (True, None) if activated.
    Return (False, reason) if not.
    """
    if not os.path.exists(ACTIVATION_FILE):
        return False, "Activation file not found."

    try:
        # Load and decrypt local activation file
        with open(ACTIVATION_FILE, "rb") as f:
            encrypted = f.read()
            decrypted = fernet.decrypt(encrypted)
            data = json.loads(decrypted.decode("utf-8"))

        valid_till = data.get("valid_till")
        created_at = data.get("created_at")
        cpu = data.get("processor_id")
        mobo = data.get("motherboard_id")

        if not (valid_till and created_at and cpu and mobo):
            return False, "Activation data is incomplete."

        # Get current hardware info early
        current_cpu = get_processor_info()
        current_mobo = get_motherboard_info()

        if cpu != current_cpu or mobo != current_mobo:
            return False, "Activation bound to another system."

        # Check dates
        start = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(valid_till, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()

        if now < start:
            return False, "Activation start date is in the future."

        if now > end:
            # Local license expired → check server for renewal
            try:
                headers = {
                    "X-API-Key": API_LICENSE_FETCH_KEY,
                    "Content-Type": "application/json"
                }
                payload = {
                    "processor_id": current_cpu,
                    "motherboard_id": current_mobo
                }
                response = requests.post(API_LICENSE_FETCH, json=payload, headers=headers, timeout=5)
                records = response.json().get("data", [])
                found = next((r for r in records if r.get("password") == data.get("password")), None)

                if found:
                    server_valid_till = found.get("valid_till")
                    
                    # Verify device is still authorized (check both device slots)
                    device1_cpu = found.get("processor_id")
                    device1_mobo = found.get("motherboard_id")
                    device2_cpu = found.get("processor_id_2")
                    device2_mobo = found.get("motherboard_id_2")
                    
                    # Check if current device matches either slot
                    is_device1 = (current_cpu == device1_cpu and current_mobo == device1_mobo)
                    is_device2 = (current_cpu == device2_cpu and current_mobo == device2_mobo)
                    
                    if not (is_device1 or is_device2):
                        return False, "Device no longer authorized. This device has been removed from the license."
                    
                    if server_valid_till:
                        server_end = datetime.strptime(server_valid_till, "%Y-%m-%d %H:%M:%S")
                        if now <= server_end:
                            # ✅ Renewed on server → update local license
                            _store_activation(found, current_cpu, current_mobo)
                            return True, None

                return False, "License expired.\nThis license key has expired. Please renew your license.\nContact us at: https://bitss.one/contact"

            except Exception as e:
                return False, f"License expired. Failed to check renewal server: {e}"

        # Still valid locally
        return True, None

    except Exception as e:
        return False, f"Failed to validate activation: {e}"


# ============================================================================
# REAL-TIME LICENSE VALIDATOR (Online/Offline with Adaptive Intervals)
# ============================================================================

class LicenseValidator:
    """Real-time license validator with online/offline support and adaptive check intervals.
    
    Features:
    - Online: Checks server every 10-60 seconds (adaptive based on expiry proximity)
    - Offline: Uses cached validity with 6-hour grace period
    - 7-day expiry warning with color-coded banner
    - Automatic renewal detection (5-second checks when expired)
    """
    
    def __init__(self, on_invalid_callback=None, on_expiry_warning_callback=None, on_valid_callback=None, app_instance=None):
        """Initialize real-time license validator.
        
        Args:
            on_invalid_callback: Function(reason) called when license becomes invalid
            on_expiry_warning_callback: Function(days_left) called for expiry warnings
            on_valid_callback: Function() called when license becomes valid again
            app_instance: Reference to VWARScannerGUI for UI updates
        """
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self.app = app_instance
        
        # Callbacks
        self.on_invalid = on_invalid_callback
        self.on_expiry_warning = on_expiry_warning_callback
        self.on_valid = on_valid_callback
        
        # State tracking
        self.is_valid = True
        self.is_online = False
        self.last_validation_time = None
        self.days_until_expiry = None
        self.current_check_interval = LICENSE_CHECK_INTERVAL_NORMAL
        
        # Cache manager
        self.cache_manager = LicenseCacheManager()
        
        # Last warning timestamp (for daily notifications)
        self._last_warning_date = None
        
    def start(self):
        """Start background validation thread."""
        if self._running:
            return
        
        self._running = True
        
        # Perform initial validation
        self._validate()
        
        # Start background thread
        self._thread = threading.Thread(target=self._validation_loop, daemon=True, name="LicenseValidator")
        self._thread.start()
        print(f"[LICENSE] Real-time validator started (adaptive intervals: 5-60s)")
    
    def stop(self):
        """Stop background validation thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        print("[LICENSE] Real-time validator stopped")
    
    def _get_adaptive_interval(self, days_remaining):
        """Calculate check interval based on days until expiry.
        
        Args:
            days_remaining (int): Days until license expires
            
        Returns:
            int: Check interval in seconds
        """
        if days_remaining is None:
            return LICENSE_CHECK_INTERVAL_NORMAL
        elif days_remaining < 0:
            # Expired - check frequently for renewals
            return LICENSE_CHECK_INTERVAL_EXPIRED
        elif days_remaining <= LICENSE_WARNING_DAYS:
            # Near expiry - real-time checks
            return LICENSE_CHECK_INTERVAL_URGENT
        elif days_remaining <= 30:
            # Approaching expiry
            return LICENSE_CHECK_INTERVAL_NORMAL
        else:
            # Stable license
            return LICENSE_CHECK_INTERVAL_STABLE
    
    def _validation_loop(self):
        """Main validation loop with adaptive intervals."""
        while self._running:
            try:
                # Sleep for current interval
                time.sleep(self.current_check_interval)
                
                # Perform validation
                self._validate()
                
            except Exception as e:
                print(f"[LICENSE] Validation loop error: {e}")
                time.sleep(5)  # Fallback interval on error
    
    def _validate(self):
        """Perform license validation (online or offline)."""
        with self._lock:
            try:
                # Remember previous state for transition detection
                previous_valid = bool(self.is_valid)
                
                # Check network availability
                self.is_online = is_network_available()
                
                if self.is_online:
                    # ONLINE MODE: Validate against server
                    self._validate_online()
                else:
                    # OFFLINE MODE: Use cached validity
                    self._validate_offline()
                
                # Update check interval based on current state
                self.current_check_interval = self._get_adaptive_interval(self.days_until_expiry)
                
                # Detect validity transitions
                if not previous_valid and self.is_valid:
                    # Transition: invalid -> valid (renewal detected!)
                    print("[LICENSE] ✅ Renewal detected! License is now valid.")
                    if self.on_valid:
                        try:
                            self.on_valid()
                        except Exception as e:
                            print(f"[LICENSE] on_valid callback error: {e}")
                
                elif previous_valid and not self.is_valid:
                    # Transition: valid -> invalid (expiry detected!)
                    print("[LICENSE] ❌ License has expired or become invalid.")
                    if self.on_invalid:
                        try:
                            self.on_invalid("License expired or invalid")
                        except Exception as e:
                            print(f"[LICENSE] on_invalid callback error: {e}")
                
                # Trigger 7-day warning (once per day)
                if self.is_valid and self.days_until_expiry is not None and self.days_until_expiry <= LICENSE_WARNING_DAYS:
                    today = datetime.now().date()
                    if self._last_warning_date != today:
                        self._last_warning_date = today
                        print(f"[LICENSE] ⚠️  License expires in {self.days_until_expiry} day(s)")
                        if self.on_expiry_warning:
                            try:
                                self.on_expiry_warning(self.days_until_expiry)
                            except Exception as e:
                                print(f"[LICENSE] on_expiry_warning callback error: {e}")
                
            except Exception as e:
                print(f"[LICENSE] Validation error: {e}")
                self.is_valid = False
    
    def _validate_online(self):
        """Validate license against server (online mode)."""
        try:
            print("[LICENSE] 🌐 Online validation...")
            
            # Check local activation first
            activated, reason = is_activated()
            self.last_validation_time = datetime.now()
            
            if not activated:
                print(f"[LICENSE] Local validation failed: {reason}")
                self.is_valid = False
                self.days_until_expiry = None
                
                # Update cache
                self.cache_manager.write_cache(False, "Unknown", None, "online")
                return
            
            # Get activation data for server sync
            try:
                with open(ACTIVATION_FILE, "rb") as f:
                    encrypted = f.read()
                    decrypted = fernet.decrypt(encrypted)
                    data = json.loads(decrypted.decode("utf-8"))
                
                valid_till = data.get("valid_till")
                local_password = data.get("password")
                
                # Calculate days remaining
                if valid_till:
                    try:
                        end_date = datetime.strptime(valid_till, "%Y-%m-%d %H:%M:%S")
                        self.days_until_expiry = (end_date - datetime.now()).days
                    except Exception:
                        self.days_until_expiry = None
                
                # Sync with server
                current_cpu = get_processor_info()
                current_mobo = get_motherboard_info()
                
                headers = {
                    "X-API-Key": API_LICENSE_FETCH_KEY,
                    "Content-Type": "application/json"
                }
                payload = {
                    "processor_id": current_cpu,
                    "motherboard_id": current_mobo
                }
                
                resp = requests.post(API_LICENSE_FETCH, json=payload, headers=headers, timeout=8)
                records = resp.json().get("data", [])
                server_record = next((r for r in records if r.get("password") == local_password), None)
                
                if server_record:
                    server_valid_till = server_record.get("valid_till")
                    
                    # Check if server reports expiry
                    if server_valid_till:
                        try:
                            server_end = datetime.strptime(server_valid_till, "%Y-%m-%d %H:%M:%S")
                            now = datetime.now()
                            
                            if now > server_end:
                                # Server says expired
                                print("[LICENSE] Server reports license expired")
                                self.is_valid = False
                                self.days_until_expiry = (server_end - now).days
                                
                                # Update local activation
                                _store_activation(server_record, current_cpu, current_mobo)
                                
                                # Update cache
                                self.cache_manager.write_cache(False, server_valid_till, self.days_until_expiry, "online")
                                return
                            else:
                                # Server says valid
                                self.days_until_expiry = (server_end - now).days
                        except Exception as e:
                            print(f"[LICENSE] Error parsing server date: {e}")
                    
                    # Check if server record differs from local
                    if server_record.get("valid_till") != valid_till:
                        print("[LICENSE] Server record differs - updating local")
                        _store_activation(server_record, current_cpu, current_mobo)
                        
                        # Trigger immediate UI refresh for Valid Till label and Auto-Renew
                        if self.app:
                            try:
                                self.app.schedule_gui(self.app._refresh_valid_till_now)
                                self.app.schedule_gui(self.app._refresh_auto_renew_now)
                            except Exception as e:
                                print(f"[UI] Failed to refresh UI: {e}")
                
                # If we got here, license is valid
                self.is_valid = True
                print(f"[LICENSE] ✅ Online validation passed ({self.days_until_expiry} days remaining)")
                
                # Update cache
                self.cache_manager.write_cache(True, valid_till, self.days_until_expiry, "online")
                
                # Always sync auto-renew from server (even if valid_till unchanged)
                if self.app:
                    try:
                        self.app.schedule_gui(self.app._refresh_auto_renew_now)
                    except Exception:
                        pass
                
                # Update UI timestamp
                if self.app:
                    try:
                        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        self.app.schedule_gui(self.app.update_last_server_check, ts)
                    except Exception:
                        pass
                
                # Check for YARA rule updates (background, non-blocking)
                try:
                    self._check_and_update_yara_rules()
                except Exception as e:
                    print(f"[YARA] Failed to initiate rule update check: {e}")
                
            except Exception as e:
                print(f"[LICENSE] Server sync error: {e}")
                # Fall back to local validation result
                self.is_valid = activated
                
        except Exception as e:
            print(f"[LICENSE] Online validation error: {e}")
            self.is_valid = False
    
    def _validate_offline(self):
        """Validate license using cache (offline mode)."""
        try:
            print("[LICENSE] 📴 Offline mode - using cache...")
            
            # Check if cache is stale
            if self.cache_manager.is_cache_stale():
                print("[LICENSE] ⚠️  Cache is stale (>6 hours offline)")
                self.is_valid = False
                self.days_until_expiry = None
                return
            
            # Read cache
            cache = self.cache_manager.read_cache()
            if not cache:
                print("[LICENSE] No cache available")
                self.is_valid = False
                self.days_until_expiry = None
                return
            
            # Use cached validity
            self.is_valid = cache.get("is_valid", False)
            self.days_until_expiry = cache.get("days_remaining")
            
            print(f"[LICENSE] Using cached validity: {'valid' if self.is_valid else 'invalid'}")
            
        except Exception as e:
            print(f"[LICENSE] Offline validation error: {e}")
            self.is_valid = False
    
    def _check_and_update_yara_rules(self):
        """Check for and download new YARA rules from server.
        
        This method is called during online validation to keep rules up-to-date.
        Runs in background thread to avoid blocking validation.
        """
        def update_rules_background():
            try:
                print("[YARA] 🔍 Checking for rule updates...")
                
                # Fetch rules from API
                headers = {
                    "X-API-Key": API_YARA_FETCH_KEY,
                    "Content-Type": "application/json"
                }
                
                response = requests.get(API_YARA_FETCH, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    print(f"[YARA] Server returned status {response.status_code}")
                    return
                
                json_data = response.json()
                
                if not json_data:
                    print("[YARA] No rules found on server")
                    return
                
                # Count new/updated rules
                new_rules = 0
                updated_rules = 0
                
                for rule in json_data:
                    category = rule.get("categoryname", "uncategorized")
                    rule_name = rule.get("rulename", "unknown_rule")
                    rule_content = rule.get("conditions", [{}])[0].get("string", "")
                    
                    if not rule_content:
                        continue
                    
                    # Ensure category directory exists
                    category_dir = os.path.join(YARA_FOLDER, category)
                    os.makedirs(category_dir, exist_ok=True)
                    
                    file_path = os.path.join(category_dir, f"{rule_name}.yar")
                    
                    # Check if rule already exists and compare content
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                existing_content = f.read()
                            
                            if existing_content != rule_content:
                                # Rule has changed
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.write(rule_content)
                                updated_rules += 1
                        except Exception as e:
                            print(f"[YARA] Error comparing rule {rule_name}: {e}")
                    else:
                        # New rule
                        try:
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(rule_content)
                            new_rules += 1
                        except Exception as e:
                            print(f"[YARA] Error writing new rule {rule_name}: {e}")
                
                # Report results
                if new_rules > 0 or updated_rules > 0:
                    print(f"[YARA] ✅ Rules updated: {new_rules} new, {updated_rules} modified")
                    
                    # Attempt to recompile rules (optional, non-blocking)
                    try:
                        from Scanning.yara_engine import compile_yara_rules
                        compile_yara_rules(log_func=lambda msg: None)  # Silent compilation
                        print("[YARA] ✅ Rules recompiled successfully")
                    except Exception as e:
                        print(f"[YARA] Note: Recompilation will occur on next scan start")
                else:
                    print("[YARA] ✅ All rules up-to-date")
                
            except requests.exceptions.RequestException as e:
                print(f"[YARA] Network error checking for updates: {e}")
            except Exception as e:
                print(f"[YARA] Error updating rules: {e}")
        
        # Run in background thread to avoid blocking validation
        threading.Thread(target=update_rules_background, daemon=True, name="YARARuleUpdater").start()
    
    def force_validate(self):
        """Force immediate validation (for manual checks)."""
        print("[LICENSE] Force validation requested")
        self._validate()
        return self.is_valid
    
    def get_status(self):
        """Get current license status.
        
        Returns:
            dict: Status information
        """
        with self._lock:
            return {
                'is_valid': self.is_valid,
                'is_online': self.is_online,
                'last_check': self.last_validation_time,
                'days_until_expiry': self.days_until_expiry,
                'check_interval': self.current_check_interval
            }


# ============================================================================
# GLOBAL VALIDATOR INSTANCE
# ============================================================================

_license_validator = None

def get_license_validator():
    """Get global license validator instance."""
    return _license_validator

def start_license_validation(on_invalid_callback=None, on_expiry_warning_callback=None, on_valid_callback=None, app_instance=None):
    """Start global license validation thread.
    
    Args:
        on_invalid_callback: Function(reason) called when license becomes invalid
        on_expiry_warning_callback: Function(days_left) called when license expiring soon
        on_valid_callback: Function() called when license becomes valid again
        app_instance: Reference to VWARScannerGUI for UI updates
    
    Returns:
        LicenseValidator: The global validator instance
    """
    global _license_validator
    
    if _license_validator is None:
        _license_validator = LicenseValidator(
            on_invalid_callback=on_invalid_callback,
            on_expiry_warning_callback=on_expiry_warning_callback,
            on_valid_callback=on_valid_callback,
            app_instance=app_instance
        )
    
    _license_validator.start()
    return _license_validator

def stop_license_validation():
    """Stop global license validation thread."""
    global _license_validator
    if _license_validator:
        _license_validator.stop()
