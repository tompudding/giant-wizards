import sys
import os


def get_path():
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        return sys._MEIPASS
    except Exception:
        return os.path.abspath(".")


def path(filename):
    if os.path.isabs(filename):
        return filename

    return os.path.join(get_path(), filename)
