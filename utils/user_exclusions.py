"""
User-defined scan exclusions module.
Allows users to add/remove folders and files from scanning.
"""

import os
import json
from typing import Set, List
from pathlib import Path

# Configuration file path
USER_EXCLUSIONS_FILE = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'data', 
    'user_exclusions.json'
)

class UserExclusions:
    """Manages user-defined scan exclusions."""
    
    def __init__(self):
        self._excluded_paths: Set[str] = set()
        self._excluded_extensions: Set[str] = set()
        self.load()
    
    def load(self):
        """Load exclusions from config file."""
        try:
            os.makedirs(os.path.dirname(USER_EXCLUSIONS_FILE), exist_ok=True)
            if os.path.exists(USER_EXCLUSIONS_FILE):
                with open(USER_EXCLUSIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._excluded_paths = set(data.get('paths', []))
                    self._excluded_extensions = set(data.get('extensions', []))
        except Exception as e:
            print(f"[ERROR] Failed to load user exclusions: {e}")
            self._excluded_paths = set()
            self._excluded_extensions = set()
    
    def save(self):
        """Save exclusions to config file."""
        try:
            os.makedirs(os.path.dirname(USER_EXCLUSIONS_FILE), exist_ok=True)
            data = {
                'paths': list(self._excluded_paths),
                'extensions': list(self._excluded_extensions)
            }
            with open(USER_EXCLUSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[ERROR] Failed to save user exclusions: {e}")
    
    def add_path(self, path: str) -> bool:
        """Add a path to exclusions."""
        try:
            normalized = os.path.abspath(path)
            if os.path.exists(normalized):
                self._excluded_paths.add(normalized)
                self.save()
                return True
            return False
        except Exception as e:
            print(f"[ERROR] Failed to add path exclusion: {e}")
            return False
    
    def remove_path(self, path: str) -> bool:
        """Remove a path from exclusions."""
        try:
            normalized = os.path.abspath(path)
            if normalized in self._excluded_paths:
                self._excluded_paths.remove(normalized)
                self.save()
                return True
            return False
        except Exception as e:
            print(f"[ERROR] Failed to remove path exclusion: {e}")
            return False
    
    def add_extension(self, ext: str) -> bool:
        """Add a file extension to exclusions (e.g., '.mp4', '.iso')."""
        try:
            if not ext.startswith('.'):
                ext = '.' + ext
            ext = ext.lower()
            self._excluded_extensions.add(ext)
            self.save()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to add extension exclusion: {e}")
            return False
    
    def remove_extension(self, ext: str) -> bool:
        """Remove a file extension from exclusions."""
        try:
            if not ext.startswith('.'):
                ext = '.' + ext
            ext = ext.lower()
            if ext in self._excluded_extensions:
                self._excluded_extensions.remove(ext)
                self.save()
                return True
            return False
        except Exception as e:
            print(f"[ERROR] Failed to remove extension exclusion: {e}")
            return False
    
    def is_excluded(self, path: str) -> bool:
        """Check if a path should be excluded from scanning."""
        try:
            normalized = os.path.abspath(path).lower()
            
            # Check file extension exclusions
            _, ext = os.path.splitext(normalized)
            if ext in self._excluded_extensions:
                return True
            
            # Check path exclusions (including subdirectories)
            for excluded in self._excluded_paths:
                excluded_lower = excluded.lower()
                if normalized == excluded_lower or normalized.startswith(excluded_lower + os.sep):
                    return True
            
            return False
        except Exception:
            return False
    
    def get_excluded_paths(self) -> List[str]:
        """Get list of excluded paths."""
        return sorted(list(self._excluded_paths))
    
    def get_excluded_extensions(self) -> List[str]:
        """Get list of excluded extensions."""
        return sorted(list(self._excluded_extensions))
    
    def clear_all(self):
        """Remove all user exclusions."""
        self._excluded_paths.clear()
        self._excluded_extensions.clear()
        self.save()


# Global instance
_user_exclusions_instance = None

def get_user_exclusions() -> UserExclusions:
    """Get the global UserExclusions instance."""
    global _user_exclusions_instance
    if _user_exclusions_instance is None:
        _user_exclusions_instance = UserExclusions()
    return _user_exclusions_instance
