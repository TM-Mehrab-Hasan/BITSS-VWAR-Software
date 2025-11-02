"""
ScanVault Restore Utility
Restores files from scanvault back to their original locations using metadata.
"""

import os
import json
import shutil
from pathlib import Path
from config import SCANVAULT_FOLDER
from utils.logger import log_message


def list_vaulted_files():
    """List all vaulted files with their metadata."""
    if not os.path.exists(SCANVAULT_FOLDER):
        print("[ERROR] ScanVault folder does not exist")
        return []
    
    vaulted_files = []
    
    for file in os.listdir(SCANVAULT_FOLDER):
        if file.endswith('.vaulted'):
            meta_file = os.path.join(SCANVAULT_FOLDER, file + '.meta')
            vaulted_path = os.path.join(SCANVAULT_FOLDER, file)
            
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    vaulted_files.append({
                        'vaulted_file': file,
                        'vaulted_path': vaulted_path,
                        'meta_path': meta_file,
                        'original_path': metadata.get('original_path', 'Unknown'),
                        'timestamp': metadata.get('timestamp', 'Unknown'),
                        'event': metadata.get('event', 'Unknown'),
                        'signature': metadata.get('signature', 'Unknown')
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to read metadata for {file}: {e}")
    
    return vaulted_files


def restore_file(vaulted_path, meta_path, force=False):
    """
    Restore a single file from scanvault to its original location.
    
    Args:
        vaulted_path: Path to the .vaulted file
        meta_path: Path to the .meta file
        force: If True, overwrite existing file at original location
    
    Returns:
        tuple: (success, message)
    """
    try:
        # Read metadata
        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        original_path = metadata.get('original_path')
        if not original_path:
            return False, "No original_path in metadata"
        
        # Convert forward slashes to backslashes for Windows
        original_path = original_path.replace('/', '\\')
        
        # Check if vaulted file exists
        if not os.path.exists(vaulted_path):
            return False, f"Vaulted file not found: {vaulted_path}"
        
        # Check if original location already has a file
        if os.path.exists(original_path) and not force:
            return False, f"File already exists at original location (use force=True to overwrite)"
        
        # Create parent directory if needed
        parent_dir = os.path.dirname(original_path)
        os.makedirs(parent_dir, exist_ok=True)
        
        # Copy file back to original location
        shutil.copy2(vaulted_path, original_path)
        
        log_message(f"[RESTORE] {vaulted_path} → {original_path}")
        
        return True, f"Successfully restored to {original_path}"
        
    except Exception as e:
        error_msg = f"Failed to restore: {e}"
        log_message(f"[ERROR] {error_msg}")
        return False, error_msg


def restore_all_files(force=False, delete_after=False):
    """
    Restore all files from scanvault.
    
    Args:
        force: If True, overwrite existing files
        delete_after: If True, delete vaulted file and metadata after successful restore
    
    Returns:
        dict: Statistics of restoration
    """
    vaulted_files = list_vaulted_files()
    
    stats = {
        'total': len(vaulted_files),
        'restored': 0,
        'failed': 0,
        'errors': []
    }
    
    print(f"\n[INFO] Found {stats['total']} vaulted files")
    print("=" * 60)
    
    for item in vaulted_files:
        print(f"\nRestoring: {item['vaulted_file']}")
        print(f"  Original: {item['original_path']}")
        print(f"  Timestamp: {item['timestamp']}")
        
        success, message = restore_file(item['vaulted_path'], item['meta_path'], force)
        
        if success:
            stats['restored'] += 1
            print(f"  ✅ {message}")
            
            # Delete vaulted file and metadata if requested
            if delete_after:
                try:
                    os.remove(item['vaulted_path'])
                    os.remove(item['meta_path'])
                    print(f"  🗑️ Deleted vaulted file and metadata")
                except Exception as e:
                    print(f"  ⚠️ Failed to delete: {e}")
        else:
            stats['failed'] += 1
            stats['errors'].append({
                'file': item['vaulted_file'],
                'error': message
            })
            print(f"  ❌ {message}")
    
    print("\n" + "=" * 60)
    print(f"Restoration complete:")
    print(f"  Total: {stats['total']}")
    print(f"  Restored: {stats['restored']}")
    print(f"  Failed: {stats['failed']}")
    
    return stats


def delete_vaulted_file(vaulted_path, meta_path):
    """
    Delete a vaulted file and its metadata without restoring.
    
    Args:
        vaulted_path: Path to the .vaulted file
        meta_path: Path to the .meta file
    
    Returns:
        tuple: (success, message)
    """
    try:
        if os.path.exists(vaulted_path):
            os.remove(vaulted_path)
        
        if os.path.exists(meta_path):
            os.remove(meta_path)
        
        log_message(f"[DELETE] Removed vaulted file: {vaulted_path}")
        return True, "Successfully deleted"
        
    except Exception as e:
        error_msg = f"Failed to delete: {e}"
        log_message(f"[ERROR] {error_msg}")
        return False, error_msg


def clear_scanvault(confirm=False):
    """
    Delete all files in scanvault (use with caution!).
    
    Args:
        confirm: Must be True to actually delete
    
    Returns:
        int: Number of files deleted
    """
    if not confirm:
        print("[WARNING] This will delete ALL vaulted files!")
        print("Call clear_scanvault(confirm=True) to proceed")
        return 0
    
    vaulted_files = list_vaulted_files()
    deleted_count = 0
    
    for item in vaulted_files:
        success, _ = delete_vaulted_file(item['vaulted_path'], item['meta_path'])
        if success:
            deleted_count += 1
    
    # Also clear history folder
    history_dir = os.path.join(SCANVAULT_FOLDER, 'history')
    if os.path.exists(history_dir):
        try:
            shutil.rmtree(history_dir)
            os.makedirs(history_dir, exist_ok=True)
            print(f"[INFO] Cleared history folder")
        except Exception as e:
            print(f"[ERROR] Failed to clear history: {e}")
    
    log_message(f"[SCANVAULT] Cleared {deleted_count} vaulted files")
    return deleted_count


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("ScanVault Restore Utility")
    print("=" * 60)
    
    # List all vaulted files
    files = list_vaulted_files()
    
    if not files:
        print("\n[INFO] No vaulted files found")
        sys.exit(0)
    
    print(f"\nFound {len(files)} vaulted files:\n")
    
    for i, item in enumerate(files, 1):
        print(f"{i}. {item['vaulted_file']}")
        print(f"   Original: {item['original_path']}")
        print(f"   Timestamp: {item['timestamp']}")
        print(f"   Event: {item['event']}")
        print()
    
    # Interactive menu
    print("\nOptions:")
    print("1. Restore all files (keep vaulted copies)")
    print("2. Restore all files and delete vaulted copies")
    print("3. List files only (done)")
    print("4. Clear all vaulted files (DELETE)")
    print("5. Exit")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        print("\n[INFO] Restoring all files (force=False)...")
        restore_all_files(force=False, delete_after=False)
    elif choice == "2":
        confirm = input("Delete vaulted files after restore? (yes/no): ").strip().lower()
        if confirm == "yes":
            print("\n[INFO] Restoring and deleting...")
            restore_all_files(force=False, delete_after=True)
        else:
            print("[INFO] Cancelled")
    elif choice == "3":
        print("[INFO] Listing complete")
    elif choice == "4":
        confirm = input("Are you SURE you want to DELETE all vaulted files? (yes/no): ").strip().lower()
        if confirm == "yes":
            deleted = clear_scanvault(confirm=True)
            print(f"[INFO] Deleted {deleted} vaulted files")
        else:
            print("[INFO] Cancelled")
    else:
        print("[INFO] Exiting")
