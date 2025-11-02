import os
import sys
import tempfile
import string
from functools import lru_cache
import re

# Centralized path exclusion helpers for scanning/monitoring

@lru_cache(maxsize=1)
def get_base_dir() -> str:
    # utils/ -> project root assumed one level up
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

@lru_cache(maxsize=1)
def get_internal_exclude_roots() -> set[str]:
    base = get_base_dir()
    # ALWAYS exclude the directory containing the executable (whether frozen or not)
    exe_dir = None
    try:
        if getattr(sys, 'frozen', False):
            # PyInstaller executable
            exe_dir = os.path.abspath(os.path.dirname(sys.executable))
        else:
            # Running as Python script - exclude the script's directory
            exe_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    except Exception:
        exe_dir = None
    
    roots = {
        base,
        os.path.join(base, 'assets'),
        os.path.join(base, 'assets', 'yara'),
        os.path.join(base, 'quarantine'),
        os.path.join(base, 'scanvault'),
        os.path.join(base, 'build'),
        os.path.join(base, '__pycache__'),
        os.path.join(base, 'data'),
        os.path.join(base, 'data', 'scan_queue'),
        os.path.join(base, '.venv'),
        os.path.join(base, 'venv'),
        os.path.join(base, 'dist'),
        os.path.join(base, '.git'),
        os.path.join(base, '.mypy_cache'),
        os.path.join(base, '.pytest_cache'),
        os.path.join(base, 'VWAR_i'),
        os.path.join(base, 'VWAR.spec'),
        os.path.join(base, '.vscode'),
        os.path.join(base, 'tests'),
        os.path.join(base, 'Backup'),
        os.path.join(base, 'Scanning'),
        os.path.join(base, 'RMonitoring'),
        os.path.join(base, 'activation'),
        os.path.join(base, 'utils'),
    }
    
    # Always exclude exe directory and its subdirectories
    if exe_dir:
        roots.update({
            exe_dir,
            os.path.join(exe_dir, 'assets'),
            os.path.join(exe_dir, 'assets', 'yara'),
            os.path.join(exe_dir, 'vwar_monitor'),
            os.path.join(exe_dir, 'quarantine'),
            os.path.join(exe_dir, 'scanvault'),
            os.path.join(exe_dir, 'data'),
            os.path.join(exe_dir, '_internal'),
        })
    
    return {os.path.abspath(p) for p in roots}

@lru_cache(maxsize=1)
def get_temp_roots() -> set[str]:
    roots: set[str] = set()
    # OS temp
    try:
        roots.add(os.path.abspath(tempfile.gettempdir()))
    except Exception:
        pass
    # Windows temp dirs
    for env in ("TEMP", "TMP"):  # user-level
        val = os.environ.get(env)
        if val:
            roots.add(os.path.abspath(val))
    # System temp
    sys_temp = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
    roots.add(os.path.abspath(sys_temp))
    # Recycle Bin on each drive (Windows)
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            # Add canonical recycle bin + system volume information
            roots.add(os.path.abspath(os.path.join(drive, '$Recycle.Bin')))
            roots.add(os.path.abspath(os.path.join(drive, 'System Volume Information')))
    return roots

_TEMP_EXTS = (
    '.tmp', '.temp', '.part', '.partial', '.crdownload', '.download',
    '.swp', '.swo', '.bak', '.old', '.log', '.lock', '.cache', '.dmp',
    '.tmp~', '.~tmp'
)
_TEMP_FILES = (
    'thumbs.db', '.ds_store',
)
_TEMP_PREFIXES = (
    '~$', '._',
)


def is_temp_like_file(path: str) -> bool:
    name = os.path.basename(path).lower()
    if name.startswith(_TEMP_PREFIXES):
        return True
    if name in _TEMP_FILES:
        return True
    root, ext = os.path.splitext(name)
    if ext in _TEMP_EXTS:
        return True
    # zero-byte files often transient; treat cautiously
    try:
        if os.path.exists(path) and os.path.getsize(path) == 0:
            return True
    except Exception:
        return True
    return False


def is_under_any(path: str, roots: set[str]) -> bool:
    """Case-insensitive containment check for Windows paths (still works on *nix)."""
    try:
        p = os.path.abspath(path)
        pl = p.lower()
        for r in roots:
            rr = os.path.abspath(r)
            rrl = rr.lower()
            if pl == rrl or pl.startswith(rrl + os.sep.lower()):
                return True
    except Exception:
        return False
    return False


_RECYCLE_BIN_PATTERN = re.compile(r"^[A-Z]:\\\\?\\?\$recycle\.bin", re.IGNORECASE)

def is_excluded_path(path: str) -> tuple[bool, str]:
    """
    Returns (excluded, reason) where reason is one of:
      INTERNAL, TEMP_ROOT, TEMP_FILE, RECYCLE_BIN, NONE
    Explicit recycle bin detection added to prevent vaulting deleted files.
    """
    # Normalize early
    norm = os.path.abspath(path)
    if is_under_any(norm, get_internal_exclude_roots()):
        return True, 'INTERNAL'
    # Explicit recycle bin pattern check first (fast lower-case compare)
    low = norm.lower()
    if low.endswith('.lnk'):
        # Shortcuts themselves not necessarily transient; continue normally
        pass
    if '$recycle.bin' in low:
        # Ensure we catch any nested items inside Recycle Bin (sometimes localized or with GUIDs)
        # Path segments check
        parts = low.split(os.sep)
        for seg in parts:
            if seg == '$recycle.bin':
                return True, 'RECYCLE_BIN'
    # Temp roots (includes canonical recycle bins added earlier)
    if is_under_any(norm, get_temp_roots()):
        return True, 'TEMP_ROOT'
    if is_temp_like_file(norm):
        return True, 'TEMP_FILE'
    return False, 'NONE'


def print_exclusion_debug():
    """Print all excluded paths for debugging."""
    print("\n" + "=" * 80)
    print("EXCLUSION DEBUG INFO")
    print("=" * 80)
    print(f"Base directory: {get_base_dir()}")
    print(f"Frozen (exe): {getattr(sys, 'frozen', False)}")
    if getattr(sys, 'frozen', False):
        print(f"Executable: {sys.executable}")
    else:
        print(f"Script: {sys.argv[0]}")
    print("\nInternal exclude roots:")
    for root in sorted(get_internal_exclude_roots()):
        exists = "✓" if os.path.exists(root) else "✗"
        print(f"  [{exists}] {root}")
    print("\nTemp roots:")
    for root in sorted(get_temp_roots()):
        exists = "✓" if os.path.exists(root) else "✗"
        print(f"  [{exists}] {root}")
    print("=" * 80 + "\n")
