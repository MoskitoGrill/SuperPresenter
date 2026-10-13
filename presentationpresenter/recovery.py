"""Each process owns one journal; previous and damaged journals are preserved."""
from pathlib import Path
from uuid import uuid4
from .storage import save, load
import os

def lock(handle):
    handle.seek(0)
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

class Recovery:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / (str(uuid4()) + '.ppres')
        self.last = None
        self.handle = None

    def candidates(self):
        result = []
        for path in self.directory.glob('*.ppres'):
            if path == self.path:
                continue
            try:
                with path.with_suffix('.lock').open('a+b') as handle:
                    lock(handle)
                    result.append(path)
            except OSError:
                continue
        return sorted(result, key=lambda p: p.stat().st_mtime, reverse=True)

    def write(self, document):
        if document != self.last:
            if self.handle is None:
                self.directory.mkdir(parents=True, exist_ok=True)
                self.handle = self.path.with_suffix('.lock').open('a+b')
                try:
                    lock(self.handle)
                except OSError:
                    self.release()
                    raise
            save(self.path, document)
            self.last = document

    def archive(self, path):
        """Retain a startup journal for manual rescue without offering it again."""
        path = Path(path)
        if path.parent.resolve() != self.directory.resolve() or path == self.path:
            raise ValueError('Neplatný soubor obnovy')
        with path.with_suffix('.lock').open('a+b') as handle:
            lock(handle)
            destination = self.directory / 'archive'
            destination.mkdir(exist_ok=True)
            target = destination / path.name
            if target.exists():
                target = destination / (str(uuid4()) + '.ppres')
            os.replace(path, target)
        return target

    def clean(self):
        self.path.unlink(missing_ok=True)
        self.release()
        self.path.with_suffix('.lock').unlink(missing_ok=True)

    def release(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None
