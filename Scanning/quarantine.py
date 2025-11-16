# # Scanning/quarantine.py

# import os
# import shutil
# import json
# import hashlib
# from datetime import datetime
# import time
# from config import QUARANTINE_FOLDER
# from utils.logger import log_message


# def quarantine_file(file_path, matched_rules=None):
#     """
#     Moves a suspicious file to the quarantine folder and writes a .meta file.

#     Args:
#         file_path (str): Path to the suspicious file.
#         matched_rules (list): List of matched YARA rule names.

#     Returns:
#         str: Path to the quarantined file (not .meta).
#     """
#     if not os.path.exists(file_path):
#         raise RuntimeError(f"File no longer exists: {file_path}")

#     os.makedirs(QUARANTINE_FOLDER, exist_ok=True)

#     try:
#         file_name = os.path.basename(file_path)
#         # timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#         timestamp_raw = datetime.now()
#         timestamp_file = timestamp_raw.strftime("%Y%m%d%H%M%S")       # For file name
#         timestamp_human = timestamp_raw.strftime("%Y-%m-%d %H:%M:%S") # For metadata
        

#         # Use SHA-256 hash of the full original path (short & unique)
#         path_hash = hashlib.sha256(file_path.encode()).hexdigest()[:16]
#         quarantine_filename = f"{file_name}__{timestamp_file}__{path_hash}.quarantined"
#         quarantine_path = os.path.join(QUARANTINE_FOLDER, quarantine_filename)

#         # Move the file to quarantine
#         # shutil.move(file_path, quarantine_path)
#         # Move the file with retry in case the file is temporarily locked or renamed
#         for attempt in range(3):
#             if os.path.exists(file_path):
#                 try:
#                     shutil.move(file_path, quarantine_path)
#                     break  # ✅ success, exit retry loop
#                 except Exception as e:
#                     if attempt == 2:
#                         raise RuntimeError(f"Move failed after 3 attempts: {e}")
#                     time.sleep(0.3)
#             else:
#                 time.sleep(0.3)
#         else:
#             raise RuntimeError(f"File no longer exists after waiting: {file_path}")

#         # Write metadata
#         meta_path = quarantine_path + ".meta"
#         metadata = {
#             "original_path": file_path,
#             "quarantined_path": quarantine_path,
#             "timestamp": timestamp_human,
#             "matched_rules": matched_rules or [],
#         }

#         with open(meta_path, "w", encoding="utf-8") as meta_file:
#             json.dump(metadata, meta_file, indent=4)

#         log_message(f"[QUARANTINED] {file_path} → {quarantine_path}")
#         return quarantine_path

#     except Exception as e:
#         raise RuntimeError(f"Failed to quarantine {file_path}: {e}")


# import os
# import shutil
# import json
# import hashlib
# import time
# from datetime import datetime

# from config import QUARANTINE_FOLDER
# from utils.logger import log_message


# def quarantine_file(file_path, matched_rules=None):
#     """
#     Moves a suspicious file to the quarantine folder and writes a .meta file,
#     but only if the file is successfully moved.

#     Args:
#         file_path (str): Path to the suspicious file.
#         matched_rules (list): List of matched YARA rule names.

#     Returns:
#         str: Path to the quarantined file (not .meta).
#     """
#     if not os.path.exists(file_path):
#         raise RuntimeError(f"File no longer exists: {file_path}")

#     os.makedirs(QUARANTINE_FOLDER, exist_ok=True)

#     try:
#         file_name = os.path.basename(file_path)

#         # Generate timestamp and hash
#         timestamp_raw = datetime.now()
#         timestamp_file = timestamp_raw.strftime("%Y%m%d%H%M%S")
#         timestamp_human = timestamp_raw.strftime("%Y-%m-%d %H:%M:%S")
#         path_hash = hashlib.sha256(file_path.encode()).hexdigest()[:16]

#         quarantine_filename = f"{file_name}__{timestamp_file}__{path_hash}.quarantined"
#         quarantine_path = os.path.join(QUARANTINE_FOLDER, quarantine_filename)

#         # Move the file with retries
#         for attempt in range(3):
#             if os.path.exists(file_path):
#                 try:
#                     shutil.move(file_path, quarantine_path)
#                     break  # Success
#                 except Exception as e:
#                     if attempt == 2:
#                         raise RuntimeError(f"Move failed after 3 attempts: {e}")
#                     time.sleep(0.3)
#             else:
#                 time.sleep(0.3)
#         else:
#             raise RuntimeError(f"File no longer exists after waiting: {file_path}")

#         # Write metadata only if the file was successfully moved
#         if os.path.exists(quarantine_path):
#             meta_path = quarantine_path + ".meta"
#             metadata = {
#                 "original_path": file_path,
#                 "quarantined_path": quarantine_path,
#                 "timestamp": timestamp_human,
#                 "matched_rules": matched_rules or [],
#             }

#             with open(meta_path, "w", encoding="utf-8") as f:
#                 json.dump(metadata, f, indent=4)

#             # log_message(f"[QUARANTINED] {file_path} → {quarantine_path}")
#             print(f"line 147 qurainte.py [QUARANTINED] {file_path} → {quarantine_path}")
#             return quarantine_path
#         else:
#             raise RuntimeError(f"Quarantined file unexpectedly missing: {quarantine_path}")

#     except Exception as e:
#         raise RuntimeError(f"Failed to quarantine {file_path}: {e}")


import os
import shutil
import json
import hashlib
import time
from datetime import datetime

from config import QUARANTINE_FOLDER, MAX_QUARANTINE_FILES, MAX_QUARANTINE_SIZE_MB
from utils.logger import log_message, telemetry_inc


def _check_quarantine_limits():
    """🛡️ Check quarantine folder limits and clean up if exceeded.
    
    Returns True if within limits, False if cleanup needed.
    """
    if not os.path.exists(QUARANTINE_FOLDER):
        return True
    
    try:
        # Count files and calculate total size
        quarantined_files = [f for f in os.listdir(QUARANTINE_FOLDER) if f.endswith('.quarantined')]
        file_count = len(quarantined_files)
        
        # Check file count limit
        if file_count >= MAX_QUARANTINE_FILES:
            log_message(f"[QUARANTINE] ⚠️ Limit exceeded: {file_count} files (max: {MAX_QUARANTINE_FILES}). Cleaning oldest files.")
            telemetry_inc('quarantine_limit_exceeded')
            _cleanup_old_quarantine_files(keep_newest=int(MAX_QUARANTINE_FILES * 0.8))  # Keep 80%
            return False
        
        # Check size limit
        total_size_bytes = 0
        for f in quarantined_files:
            try:
                fpath = os.path.join(QUARANTINE_FOLDER, f)
                total_size_bytes += os.path.getsize(fpath)
            except Exception:
                pass
        
        total_size_mb = total_size_bytes / (1024 * 1024)
        if total_size_mb >= MAX_QUARANTINE_SIZE_MB:
            log_message(f"[QUARANTINE] ⚠️ Size limit exceeded: {total_size_mb:.1f}MB (max: {MAX_QUARANTINE_SIZE_MB}MB). Cleaning oldest files.")
            telemetry_inc('quarantine_size_exceeded')
            _cleanup_old_quarantine_files(keep_newest=int(MAX_QUARANTINE_FILES * 0.5))  # Keep 50%
            return False
        
        return True
    except Exception as e:
        log_message(f"[QUARANTINE] Error checking limits: {e}")
        return True  # Continue on error


def _cleanup_old_quarantine_files(keep_newest: int = 800):
    """🛡️ Remove oldest quarantined files to free up space.
    
    Args:
        keep_newest: Number of newest files to keep
    """
    try:
        files = [f for f in os.listdir(QUARANTINE_FOLDER) if f.endswith('.quarantined')]
        if len(files) <= keep_newest:
            return
        
        # Sort by creation time (oldest first)
        files_with_time = []
        for f in files:
            fpath = os.path.join(QUARANTINE_FOLDER, f)
            try:
                ctime = os.path.getctime(fpath)
                files_with_time.append((ctime, f))
            except Exception:
                pass
        
        files_with_time.sort()  # Oldest first
        
        # Delete oldest files
        num_to_delete = len(files_with_time) - keep_newest
        deleted_count = 0
        
        for _, fname in files_with_time[:num_to_delete]:
            try:
                qpath = os.path.join(QUARANTINE_FOLDER, fname)
                meta_path = qpath + '.meta'
                
                if os.path.exists(qpath):
                    os.remove(qpath)
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                
                deleted_count += 1
            except Exception as e:
                log_message(f"[QUARANTINE] Failed to delete {fname}: {e}")
        
        log_message(f"[QUARANTINE] Cleanup complete: Deleted {deleted_count} oldest files (kept {keep_newest} newest)")
        telemetry_inc('quarantine_cleanup_performed')
        
    except Exception as e:
        log_message(f"[QUARANTINE] Cleanup failed: {e}")


def quarantine_file(file_path, matched_rules=None):
    """
    Moves a suspicious file to the quarantine folder and writes a .meta file,
    but only if the file is successfully moved.

    Args:
        file_path (str): Path to the suspicious file.
        matched_rules (list): List of matched YARA rule names.

    Returns:
        str: Path to the quarantined file (not .meta).
    """
    if not os.path.exists(file_path):
        raise RuntimeError(f"File no longer exists: {file_path}")

    os.makedirs(QUARANTINE_FOLDER, exist_ok=True)
    
    # 🛡️ BRUTE FORCE PROTECTION: Check quarantine limits
    _check_quarantine_limits()

    try:
        file_name = os.path.basename(file_path)

        # Generate timestamp and hash
        timestamp_raw = datetime.now()
        timestamp_file = timestamp_raw.strftime("%Y%m%d%H%M%S")
        timestamp_human = timestamp_raw.strftime("%Y-%m-%d %H:%M:%S")
        path_hash = hashlib.sha256(file_path.encode()).hexdigest()[:16]

        quarantine_filename = f"{file_name}__{timestamp_file}__{path_hash}.quarantined"
        quarantine_path = os.path.join(QUARANTINE_FOLDER, quarantine_filename)

        # Move the file with retries
        for attempt in range(3):
            if os.path.exists(file_path):
                try:
                    shutil.move(file_path, quarantine_path)
                    break  # Success
                except Exception as e:
                    if attempt == 2:
                        raise RuntimeError(f"Move failed after 3 attempts: {e}")
                    time.sleep(0.3)
            else:
                time.sleep(0.3)
        else:
            raise RuntimeError(f"File no longer exists after waiting: {file_path}")

        # Write metadata only if the file was successfully moved
        if os.path.exists(quarantine_path):
            meta_path = quarantine_path + ".meta"
            # ✅ FIX: Store ACTUAL original path (not normalized lowercase)
            # Normalized path is only for duplicate detection, NOT for restoration
            actual_original_path = os.path.abspath(file_path).replace("\\", "/")
            metadata = {
                "original_path": actual_original_path,  # Keep actual case-sensitive path
                "quarantined_path": quarantine_path,
                "timestamp": timestamp_human,
                "matched_rules": matched_rules or [],
            }

            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)

            # log_message(f"[QUARANTINED] {file_path} → {quarantine_path}")
            # print(f"line 225 quraintine[QUARANTINED] {file_path} → {quarantine_path}")
            return quarantine_path
        else:
            raise RuntimeError(f"Quarantined file unexpectedly missing: {quarantine_path}")

    except Exception as e:
        raise RuntimeError(f"Failed to quarantine {file_path}: {e}")
