"""Lazy, in-memory song search using the shared repository; no GUI dependencies."""
from dataclasses import dataclass
import logging
from pathlib import Path
import unicodedata

from superpresenter.services.song_repository import SongRepository, SongRepositoryError

logger = logging.getLogger(__name__)


def normalize(text):
    # Strip accents only from Latin characters. Cyrillic й/ї stay distinct.
    result = []
    latin = False
    for char in unicodedata.normalize('NFD', text.casefold()):
        if not unicodedata.combining(char):
            latin = 'LATIN' in unicodedata.name(char, '')
        if not (latin and unicodedata.combining(char)):
            result.append(char)
    return ' '.join(unicodedata.normalize('NFC', ''.join(result)).split())


@dataclass(frozen=True)
class SearchField:
    location: str
    text: str
    normalized: str
    rank: int


@dataclass(frozen=True)
class IndexedSong:
    path: Path
    title: str
    fields: tuple[SearchField, ...]


@dataclass(frozen=True)
class SearchResult:
    path: Path
    title: str
    location: str
    snippet: str
    rank: int


def excerpt(text, words, limit=150):
    """Return two original lines around the strongest query match."""
    lines = [' '.join(line.split()) for line in text.splitlines() if line.strip()]
    if not lines:
        return ''
    hits = [{word for word in words if word in normalize(line)} for line in lines]
    # Prefer a matching line and its successor; at the end use its predecessor.
    candidates = [min(i, max(0, len(lines) - 2)) for i, hit in enumerate(hits) if hit]
    start = max(candidates, key=lambda i: len(set().union(*hits[i:i + 2]))) if candidates else 0

    def shorten(line):
        if len(line) <= limit:
            return line
        offset = 0
        for word in line.split(' '):
            if any(token in normalize(word) for token in words):
                break
            offset += len(word) + 1
        else:
            offset = 0  # A context-only line should show its beginning.
        left = max(0, min(offset, len(line)) - 25)
        right = min(len(line), left + limit)
        return ('…' if left else '') + line[left:right] + ('…' if right < len(line) else '')

    return '\n'.join(shorten(line) for line in lines[start:start + 2])


class SongSearch:
    def __init__(self, root, repository=None):
        self.root = Path(root)
        self.repository = repository or SongRepository()
        self.songs = []
        self.failures = []

    def rebuild(self):
        songs, failures = [], []
        if not self.root.is_dir():
            raise OSError(f'Složka písní není dostupná: {self.root}')
        for path in sorted(self.root.rglob('*'), key=lambda p: str(p).casefold()):
            if not path.is_file() or path.suffix.lower() != '.xml' or path.name == '.xml':
                continue
            try:
                song = self.repository.load(path)
                if not song.title.strip():
                    raise ValueError('Prázdný název písně')
                fields = [('Název', song.title, 2), ('Soubor', path.name, 3)]
                fields.extend((f'{variant.name} / {section.identifier}', '\n'.join(section.lines), 4)
                              for variant in song.variants for section in variant.sections)
                songs.append(IndexedSong(path.resolve(), song.title, tuple(
                    SearchField(location, text, normalize(text), rank)
                    for location, text, rank in fields)))
            except (SongRepositoryError, OSError, ValueError) as exc:
                failures.append(path)
                logger.warning('Nelze indexovat píseň %s: %s', path, exc)
        self.songs, self.failures = songs, failures

    def search(self, query):
        query = normalize(query)
        words = query.split()
        if not words:
            return []
        results = []
        for song in self.songs:
            for field in song.fields:
                if not all(word in field.normalized for word in words):
                    continue
                rank = field.rank
                if rank == 2:
                    rank = 0 if field.normalized == query else 1 if field.normalized.startswith(query) else 2
                snippet_field = field
                if field.rank < 4:
                    sections = [item for item in song.fields if item.rank == 4 and item.text.strip()]
                    if sections:
                        snippet_field = max(sections, key=lambda item: sum(
                            word in item.normalized for word in words))
                results.append(SearchResult(song.path, song.title, field.location,
                                            excerpt(snippet_field.text, words), rank))
                break
        return sorted(results, key=lambda r: (r.rank, normalize(r.title), r.title, str(r.path)))
