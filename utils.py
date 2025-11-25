"""
Utility functions for the application
"""

import sys
from pathlib import Path

def resource_path(relative_path: str) -> Path:
    """ Get absolute path to a resource, works for dev and for PyInstaller. 
        This is for resources that are BUNDLED with the executable."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # This is the correct path for bundled assets.
        base_path = Path(sys._MEIPASS)
    except Exception:
        # Not running in a PyInstaller bundle, so base path is the CWD
        base_path = Path(".").resolve()

    return base_path / relative_path

def get_base_path() -> Path:
    """ Get the base path for EXTERNAL files, works for dev and for PyInstaller.
        This is for files like config.ini that are NOT bundled."""
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the base path is the directory containing the executable
        return Path(sys.executable).parent
    else:
        # If run from source, the base path is the current working directory
        return Path(".")
