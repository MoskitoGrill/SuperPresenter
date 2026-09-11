"""One edit session for both a new draft and an existing song."""
from copy import deepcopy
from pathlib import Path
import re

from superpresenter.domain.song import Song, SongVariant, SongSection, SongRepetition
from superpresenter.services.song_repository import SongRepository
from superpresenter.services.construct_parser import parse_construct, ConstructError


class SongEditSession:
    def __init__(self, repository=None):
        self.repository = repository or SongRepository()
        self.reset(Song.from_texts())

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
        if not self.song.title.strip():
            raise ValueError("Název písně nesmí být prázdný.")
        self.repository.save(self.song, target, overwrite=overwrite)
        # A failed deletion keeps the original AND the new copy and the session dirty.
        if rename and old and old.resolve() != target.resolve():
            try:
                old.unlink()
            except OSError as exc:
                raise OSError(f"Kopie byla uložena do {target}, ale původní soubor {old} nelze odstranit: {exc}") from exc
        self.song.source_path = target
        self.reset(self.song, target)

    def repetition_problems(self):
        """Report invalid references/syntax with the shared presentation parser."""
        sections = list(dict.fromkeys(sid for variant in self.song.variant_texts.values() for sid in variant))
        problems = {}
        for name, guide in self.song.repetition_texts.items():
            if not guide.strip():
                continue  # Existing omitted-section warning handles empty guides.
            try:
                parse_construct(guide, sections)
            except ConstructError as exc:
                problems[name] = str(exc)
        return problems

    def omitted_sections(self):
        """Advisory coverage of every named repetition, without expanding loops.

        Section IDs are whole tokens; line/range suffixes and repeat counts do
        not form section references. This is not a construct syntax validator.
        """
        sections = list(dict.fromkeys(sid for variant in self.song.variant_texts.values() for sid in variant))
        missing = {}
        for name, guide in (self.song.repetition_texts or {"(žádné opakování)": ""}).items():
            tokens = re.findall(r"\*[0-9]+|\.[0-9]+(?::[0-9]+)?|[^\s().:*@]+", guide)
            used = {sid for token in tokens if not token.startswith(('*', '.'))
                    for sid in re.split(r'(?<=[0-9])(?=[A-Za-z])', token)}
            omitted = [sid for sid in sections if sid not in used]
            if omitted:
                missing[name] = omitted
        return missing

    def remove_section(self, sid):
        """Renumber sections and every named construct together, in all languages."""
        match = re.fullmatch(r"([A-Za-z]+)([0-9]+)", sid)
        mapping = {sid: None}
        if match:
            kind, number = match[1], int(match[2])
            for sections in self.song.variant_texts.values():
                for name in sections:
                    other = re.fullmatch(r"([A-Za-z]+)([0-9]+)", name)
                    if other and other[1] == kind and int(other[2]) > number:
                        mapping[name] = f"{kind}{int(other[2]) - 1}"
        for variant in self.song.variants:
            retained = []
            for i, section in enumerate(variant.sections, 1):
                name = section.identifier or f"s{i}"
                if name != sid:
                    if name in mapping:
                        section.identifier = mapping[name]
                    retained.append(section)
            variant.sections = retained
        def replace(token):
            pin, name, suffix = token[1], token[2], token[3] or ''
            replacement = mapping.get(name, name)
            return pin + replacement + suffix if replacement is not None else ''
        for repetition in self.song.repetitions:
            guide = repetition.guide
            guide = re.sub(r"(@?)([A-Za-z]+[0-9]*)(\.[0-9]+(?::[0-9]+)?)?", replace, guide)
            while re.search(r"\(\s*\)(?:\*[0-9]+)?", guide):
                guide = re.sub(r"\(\s*\)(?:\*[0-9]+)?", '', guide)
            repetition.guide = guide.strip()


def update_song_fields(original, title, variants, repetitions, main):
    """Apply editor text fields to a copy of Song, retaining unchanged raw XML data."""
    song = deepcopy(original)
    song.title = title
    old_variants = {variant.name or f"variant {i}": variant
                    for i, variant in enumerate(song.variants, 1)}
    variant_indices = {id(variant): i for i, variant in enumerate(song.variants)}
    updated = []
    remap = {}
    # Retain model order even when the GUI groups widgets by section/language.
    names = [name for name in old_variants if name in variants]
    names += [name for name in variants if name not in old_variants]
    for name in names:
        variant = old_variants.get(name)
        if variant is None:
            variant = SongVariant(name)
        else:
            remap[variant_indices[id(variant)]] = len(updated)
        old_sections = {section.identifier or f"s{i}": section
                        for i, section in enumerate(variant.sections, 1)}
        sections = []
        ids = [sid for sid in old_sections if sid in variants[name]]
        ids += [sid for sid in variants[name] if sid not in old_sections]
        for sid in ids:
            text = variants[name][sid]
            section = old_sections.get(sid)
            if section is None:
                section = SongSection(sid, text.split('\n'))
            elif '\n'.join(section.lines).strip() != text:
                section.lines = text.split('\n')
            sections.append(section)
        variant.sections = sections
        updated.append(variant)
    song.variants = updated
    old_reps = {rep.name or "default": i for i, rep in enumerate(song.repetitions)}
    updated_reps, locations = [], []
    selection_changed = original.main_repetition != main
    # Some legacy songs have both a nested and root repetition with the same
    # name. The field shows the last one, but other copies must remain intact.
    for index, rep in enumerate(song.repetitions):
        name = rep.name or "default"
        if name not in repetitions:
            continue
        if old_reps[name] == index and rep.guide.strip() != repetitions[name]:
            rep.guide = repetitions[name]
        if selection_changed:
            rep.is_main = name == main and old_reps[name] == index
        location = song.repetition_locations[index] if index < len(song.repetition_locations) else (None, len(song.variants) + len(song.extra_elements) + len(updated_reps))
        parent, position = location
        if parent is not None:
            location = (remap[parent], position) if parent in remap else (None, len(song.variants) + len(updated_reps))
        updated_reps.append(rep)
        locations.append(location)
    for name, text in repetitions.items():
        if name not in old_reps:
            updated_reps.append(SongRepetition(name, text, name == main))
            locations.append((None, len(song.variants) + len(song.extra_elements) + len(updated_reps) - 1))
    song.repetitions = updated_reps
    song.repetition_locations = locations
    return song


def validate_editor_fields(song):
    """Duplicate identifiers cannot be represented by unique editor fields."""
    def unique(names, label):
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicitní {label}: nelze bezpečně otevřít v editoru.")
    unique([v.name or f"variant {i}" for i, v in enumerate(song.variants, 1)], "jazyk")
    for variant in song.variants:
        unique([s.identifier or f"s{i}" for i, s in enumerate(variant.sections, 1)], "sekce")
