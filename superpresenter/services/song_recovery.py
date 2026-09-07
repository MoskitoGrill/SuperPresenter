"""Crash recovery records, separate from songs; no executable serialization."""
import json
import os
from pathlib import Path
import tempfile
import uuid

from superpresenter.services.song_repository import SongRepository


class RecoveryLease:
    """An OS lock distinguishes a crashed editor from another running instance."""
    def __init__(self, path):
        self.path = Path(path)
        self.handle = self.path.open('a+b')
        try:
            if self.handle.seek(0, os.SEEK_END) == 0:
                self.handle.write(b'0')
                self.handle.flush()
            self.handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.handle.close()
            raise

    def close(self):
        self.handle.close()  # Closing releases the lock, including after a crash.


class SongRecovery:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / (uuid.uuid4().hex + '.json')
        self.lease = RecoveryLease(self.path.with_suffix('.lock'))
        self.repository = SongRepository()

    def write(self, session):
        payload = {
            'version': 1,
            'path': str(session.path.resolve()) if session.path else None,
            'song': self.repository.dumps(session.song).decode('utf-8'),
            'clean_song': self.repository.dumps(session.clean_song).decode('utf-8'),
        }
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.directory, suffix='.tmp',
                                             mode='w', encoding='utf-8', delete=False) as out:
                temporary = Path(out.name)
                json.dump(payload, out, ensure_ascii=False)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def clear(self):
        self.path.unlink(missing_ok=True)

    def candidates(self):
        return [p for p in sorted(self.directory.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
                if p != self.path]

    def claim(self, candidate):
        candidate = Path(candidate)
        if candidate.parent.resolve() != self.directory.resolve() or candidate.suffix != '.json':
            raise ValueError('Neplatná cesta zálohy.')
        try:
            return RecoveryLease(candidate.with_suffix('.lock'))
        except PermissionError:
            return None  # Another editor still owns this backup.
        except BlockingIOError:
            return None

    def read(self, candidate):
        data = json.loads(Path(candidate).read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('Nepodporovaný formát zálohy.')
        path = data.get('path')
        if path is not None and not isinstance(path, str):
            raise ValueError('Neplatná cesta písně v záloze.')
        return (self.repository.loads(data['song'], path),
                self.repository.loads(data['clean_song'], path), path)

    def close(self):
        self.lease.close()
        # Leave the tiny lock file to avoid races with another recovery reader.
