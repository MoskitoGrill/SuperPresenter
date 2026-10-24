"""Atomic writes shared by documents and local preferences, without UI/media."""
import os
import tempfile
import time
from pathlib import Path


def _with_windows_retry(action):
    for attempt in range(6):
        try:
            return action()
        except PermissionError as exc:
            if os.name != 'nt' or getattr(exc, 'winerror', None) not in (None, 5, 32) or attempt == 5:
                raise
            time.sleep(.005*2**attempt)


def read_text(path):
    """A concurrent Windows replacement may briefly deny opening a reader."""
    return _with_windows_retry(lambda: Path(path).read_text(encoding='utf-8'))


def atomic_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
        # Readers can briefly deny replacement. The old file remains intact;
        # retry only transient access errors, for at most 155ms in total.
        _with_windows_retry(lambda: os.replace(temporary, path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
