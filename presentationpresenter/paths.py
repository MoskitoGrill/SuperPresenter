"""Portable presentation directory beside the application, independent of cwd."""
import sys
from pathlib import Path


def presentation_directory():
    if getattr(sys, 'frozen', False):
        root = Path(sys.executable).resolve().parent
    else:
        root = Path(__file__).resolve().parent.parent
    directory = root / 'presentation'
    directory.mkdir(parents=True, exist_ok=True)
    return directory
