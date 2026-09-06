"""One edit session for both a new draft and an existing song."""
from copy import deepcopy
from pathlib import Path
import re

from superpresenter.domain.editable_song import EditableSong as Song
from superpresenter.services.song_editor_repository import SongEditorRepository as SongRepository


class SongEditSession:
    def __init__(self, repository=None):
        self.repository = repository or SongRepository()
        self.reset(Song())

    def reset(self, song, path=None):
        self.song = deepcopy(song)
        self.clean_song = deepcopy(song)
        self.path = Path(path) if path else None

    @property
    def dirty(self):
        return self.song != self.clean_song

    def load(self, path):
        self.reset(self.repository.load(path), path)

    def save(self, target, *, overwrite=False, rename=False):
        old = self.path
        target = Path(target)
        self.repository.save(self.song, target, overwrite=overwrite)
        # A failed deletion keeps the original AND the new copy and the session dirty.
        if rename and old and old.resolve() != target.resolve():
            try:
                old.unlink()
            except OSError as exc:
                raise OSError(f"Kopie byla uložena do {target}, ale původní soubor {old} nelze odstranit: {exc}") from exc
        self.reset(self.song, target)

    def remove_section(self, sid):
        """Renumber sections and every named construct together, in all languages."""
        match = re.fullmatch(r"([A-Za-z]+)([0-9]+)", sid)
        mapping = {sid: None}
        if match:
            kind, number = match[1], int(match[2])
            for sections in self.song.variants.values():
                for name in sections:
                    other = re.fullmatch(r"([A-Za-z]+)([0-9]+)", name)
                    if other and other[1] == kind and int(other[2]) > number:
                        mapping[name] = f"{kind}{int(other[2]) - 1}"
        for lang, sections in self.song.variants.items():
            self.song.variants[lang] = {mapping.get(name, name): text for name, text in sections.items() if name != sid}
        if self.song.template is not None:
            for variant in self.song.template.findall('variant'):
                for section in list(variant.findall('section')):
                    name = section.get('name')
                    if name == sid:
                        variant.remove(section)
                    elif name in mapping:
                        section.set('name', mapping[name])
        def replace(token):
            name, suffix = token[1], token[2] or ''
            replacement = mapping.get(name, name)
            return replacement + suffix if replacement is not None else ''
        for name, guide in self.song.repetitions.items():
            guide = re.sub(r"([A-Za-z]+[0-9]*)(\.[0-9]+(?::[0-9]+)?)?", replace, guide)
            while re.search(r"\(\s*\)(?:\*[0-9]+)?", guide):
                guide = re.sub(r"\(\s*\)(?:\*[0-9]+)?", '', guide)
            self.song.repetitions[name] = guide.strip()
