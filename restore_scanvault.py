"""
Restore all vaulted files from scanvault to their original locations.
This script reads the .meta files and restores files safely.
"""
import os
import shutil
import json
from pathlib import Path

SCANVAULT_FOLDER = r"g:\Ratul\Job\BFIN IT\Versions\Bitss\BITSS-VWAR-Software\dist\scanvault"
RESTORE_LOG = "restore_log.txt"

def restore_vaulted_files():
    """Restore all vaulted files to their original locations."""
    
    if not os.path.exists(SCANVAULT_FOLDER):
        print(f"[ERROR] Scanvault folder not found: {SCANVAULT_FOLDER}")
        return
    
    restored_count = 0
    skipped_count = 0
    error_count = 0
    
    log_lines = []
    log_lines.append("=" * 80)
    log_lines.append("SCANVAULT RESTORE LOG")
    log_lines.append("=" * 80)
    log_lines.append("")
    
    # Find all .meta files
    meta_files = []
    for root, dirs, files in os.walk(SCANVAULT_FOLDER):
        for file in files:
            if file.endswith('.vaulted.meta'):
                meta_files.append(os.path.join(root, file))
    
    print(f"[INFO] Found {len(meta_files)} vaulted files")
    log_lines.append(f"Found {len(meta_files)} vaulted files\n")
    
    for meta_path in meta_files:
        try:
            # Read metadata
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            original_path = metadata.get('original_path', '')
            vaulted_path = metadata.get('vaulted_path', '')
            timestamp = metadata.get('timestamp', 'Unknown')
            status = metadata.get('final_status', '')
            
            # Skip duplicates
            if status == "DUPLICATE_SUPPRESSED":
                skipped_count += 1
                log_lines.append(f"[SKIP] Duplicate: {original_path}")
                continue
            
            # Check if vaulted file exists
            if not vaulted_path or not os.path.exists(vaulted_path):
                # Try to construct vaulted path from meta filename
                vaulted_path = meta_path.replace('.vaulted.meta', '.vaulted')
                if not os.path.exists(vaulted_path):
                    error_count += 1
                    log_lines.append(f"[ERROR] Vaulted file not found: {vaulted_path}")
                    continue
            
            # Check if original location still exists (for safety)
            original_dir = os.path.dirname(original_path)
            if not os.path.exists(original_dir):
                try:
                    os.makedirs(original_dir, exist_ok=True)
                    log_lines.append(f"[CREATE] Created directory: {original_dir}")
                except Exception as e:
                    error_count += 1
                    log_lines.append(f"[ERROR] Cannot create directory {original_dir}: {e}")
                    continue
            
            # Check if file already exists at original location
            if os.path.exists(original_path):
                # Create backup name
                backup_path = original_path + f".backup_{timestamp.replace(':', '').replace(' ', '_')}"
                try:
                    shutil.copy2(original_path, backup_path)
                    log_lines.append(f"[BACKUP] Existing file backed up to: {backup_path}")
                except Exception as e:
                    log_lines.append(f"[WARNING] Could not backup existing file: {e}")
            
            # Restore the file (copy, not move, to keep vault intact)
            try:
                shutil.copy2(vaulted_path, original_path)
                restored_count += 1
                print(f"[OK] Restored: {os.path.basename(original_path)} -> {original_path}")
                log_lines.append(f"[RESTORE] {vaulted_path} -> {original_path} (Time: {timestamp})")
            except Exception as e:
                error_count += 1
                log_lines.append(f"[ERROR] Failed to restore {vaulted_path}: {e}")
        
        except Exception as e:
            error_count += 1
            log_lines.append(f"[ERROR] Failed to process {meta_path}: {e}")
    
    # Summary
    log_lines.append("")
    log_lines.append("=" * 80)
    log_lines.append("SUMMARY")
    log_lines.append("=" * 80)
    log_lines.append(f"Total files found: {len(meta_files)}")
    log_lines.append(f"Successfully restored: {restored_count}")
    log_lines.append(f"Skipped (duplicates): {skipped_count}")
    log_lines.append(f"Errors: {error_count}")
    log_lines.append("=" * 80)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files found: {len(meta_files)}")
    print(f"Successfully restored: {restored_count}")
    print(f"Skipped (duplicates): {skipped_count}")
    print(f"Errors: {error_count}")
    print("=" * 80)
    
    # Write log file
    with open(RESTORE_LOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))
    
    print(f"\n[INFO] Full log written to: {RESTORE_LOG}")
    print("\n[NOTE] Original vaulted files are preserved in scanvault folder.")
    print("[NOTE] You can safely delete the scanvault folder after verifying restored files.")

if __name__ == "__main__":
    print("=" * 80)
    print("SCANVAULT RESTORE UTILITY")
    print("=" * 80)
    print(f"Scanvault location: {SCANVAULT_FOLDER}")
    print("\nThis will restore all vaulted files to their original locations.")
    print("Existing files will be backed up with .backup_* extension.")
    print("Vaulted files will remain in scanvault (copy, not move).")
    print("=" * 80)
    
    response = input("\nProceed with restore? (yes/no): ").strip().lower()
    if response in ['yes', 'y']:
        restore_vaulted_files()
    else:
        print("[CANCELLED] Restore cancelled by user.")
