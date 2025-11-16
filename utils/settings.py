# Runtime settings and debug flag management
from dataclasses import dataclass

@dataclass
class AppSettings:
    debug: bool = False
    startup_tray: bool = True  # append --tray when enabling Windows startup
    tray_notifications: bool = True  # show notifications for matches when in tray/silent

SETTINGS = AppSettings()

def set_debug(value: bool):
    SETTINGS.debug = bool(value)

def is_debug():
    return SETTINGS.debug

