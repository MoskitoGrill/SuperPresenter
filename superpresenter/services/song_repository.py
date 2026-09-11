"""Standard XML persistence; no GUI imports or repetition expression evaluation."""

from copy import deepcopy
import re
import unicodedata
from pathlib import Path
import os
import tempfile
import xml.etree.ElementTree as ET

from superpresenter.domain.song import Song, SongVariant, SongSection, SongRepetition


class SongRepositoryError(Exception):
    def __init__(self, path, cause):
        self.path = Path(path) if path is not None else None
        self.cause = cause
        super().__init__(f"{self.path or '<unsaved song>'}: {cause}")


class SongLoadError(SongRepositoryError):
    """Unreadable XML or unsupported song structure."""


class SongSaveError(SongRepositoryError):
    """Song could not be written."""


class SongValidationError(SongRepositoryError):
    """Model cannot be represented safely as song XML."""


class _SongTreeBuilder(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError('DTD declarations are not supported')


def _attributes(element, *reserved):
    return {k: v for k, v in element.attrib.items() if k not in reserved}


def _check_children(element, allowed):
    for child in element:
        if child.tag not in allowed:
            raise ValueError(f'Unsupported element {child.tag!r} in {element.tag}')


class SongRepository:
    def load(self, path) -> Song:
        path = Path(path)
        try:
            return self.loads(path.read_bytes(), path)
        except OSError as exc:
            raise SongLoadError(path, exc) from exc

    def loads(self, data, path=None) -> Song:
        """Decode the same song format from a recovery record or file contents."""
        path = Path(path) if path is not None else None
        try:
            root = ET.fromstring(data, parser=ET.XMLParser(target=_SongTreeBuilder()))
            return self._from_root(root, path)
        except (ET.ParseError, ValueError, LookupError) as exc:
            raise SongLoadError(path, exc) from exc

    def _from_root(self, root, path):
        if root.tag != 'slide':
            raise ValueError('Root element must be slide')
        extras = [(i, deepcopy(child)) for i, child in enumerate(root)
                  if child.tag not in {'variant', 'repetition'}]
        song = Song(root.get('name', ''), source_path=path,
                    attributes=_attributes(root, 'name'), xml_text=root.text, extra_elements=extras)
        for variant in root.findall('variant'):
            _check_children(variant, {'section', 'repetition'})
            model = SongVariant(variant.get('name', ''),
                                attributes=_attributes(variant, 'name'),
                                xml_text=variant.text, xml_tail=variant.tail)
            for section in variant.findall('section'):
                _check_children(section, set())
                model.sections.append(SongSection(
                    section.get('name', ''), (section.text or '').split('\n'),
                    _attributes(section, 'name'), xml_tail=section.tail))
            song.variants.append(model)
        variants = root.findall('variant')
        locations = {}
        for index, child in enumerate(root):
            if child.tag == 'repetition':
                locations[id(child)] = (None, index)
            elif child.tag == 'variant':
                for position, nested in enumerate(child):
                    if nested.tag == 'repetition':
                        locations[id(nested)] = (variants.index(child), position)
        for repetition in root.iter('repetition'):
            song.repetition_locations.append(locations[id(repetition)])
            _check_children(repetition, set())
            song.repetitions.append(SongRepetition(
                repetition.get('name', ''), repetition.text or '',
                repetition.get('main', '').lower() in ('1', 'true', 'yes'), _attributes(repetition, 'name', 'main'),
                xml_tail=repetition.tail))
        return song

    def dumps(self, song):
        self.validate(song)
        return ET.tostring(self._to_xml(song), encoding='utf-8', xml_declaration=True).replace(b'\r', b'&#13;')

    def validate(self, song: Song):
        """Check storage invariants, not musical quality or guide syntax.

        Legacy empty names/text and missing repetitions remain representable.
        The read-only stage 2 validator provides stricter content diagnostics.
        """
        try:
            root = self._to_xml(song)
            # Also checks invalid XML names/characters and model value types.
            ET.fromstring(ET.tostring(root, encoding='utf-8'))
        except (TypeError, ValueError, AttributeError, IndexError, ET.ParseError) as exc:
            raise SongValidationError(song.source_path, exc) from exc

    def _to_xml(self, song):
        def node(tag, attributes, **reserved):
            if set(attributes).intersection(reserved):
                raise ValueError(f'{tag}: reserved attributes must use model fields')
            for value in [*attributes.values(), *reserved.values()]:
                if not isinstance(value, str):
                    raise ValueError(f'{tag}: attributes must be strings')
            return ET.Element(tag, {**attributes, **reserved})

        root = node('slide', song.attributes, name=song.title)
        root.text = song.xml_text
        for variant in song.variants:
            v = node('variant', variant.attributes, name=variant.name)
            v.text, v.tail = variant.xml_text, variant.xml_tail
            root.append(v)
            for section in variant.sections:
                s = node('section', section.attributes, name=section.identifier)
                s.text = '\n'.join(section.lines)
                s.tail = section.xml_tail
                v.append(s)
        insertions = [(root, position, deepcopy(element)) for position, element in song.extra_elements]
        for index, repetition in enumerate(song.repetitions):
            if 'main' in repetition.attributes or not isinstance(repetition.is_main, bool):
                raise ValueError('repetition: main must use the boolean is_main field')
            r = node('repetition', repetition.attributes, name=repetition.name)
            if repetition.is_main:
                r.set('main', '1')
            if not isinstance(repetition.guide, str):
                raise ValueError('repetition: guide must be a string')
            r.text = repetition.guide
            r.tail = repetition.xml_tail
            if index < len(song.repetition_locations):
                parent_index, position = song.repetition_locations[index]
                parent = root if parent_index is None else root.findall('variant')[parent_index]
                insertions.append((parent, position, r))
            else:
                root.append(r)

        for parent, position, element in sorted(insertions, key=lambda item: item[1]):
            parent.insert(position, element)
        return root

    def save(self, song: Song, path, *, overwrite=True):
        path = Path(path)
        temporary = None
        try:
            data = self.dumps(song)
            # Replace only after a complete write; never truncate the existing song.
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.song-', suffix='.tmp', delete=False) as out:
                temporary = Path(out.name)
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            if overwrite:
                os.replace(temporary, path)
            else:
                os.link(temporary, path)
        except (OSError, ValueError, SongValidationError) as exc:
            raise SongSaveError(path, exc) from exc
        finally:
            if temporary is not None:
                if temporary.exists():
                    os.unlink(temporary)

    @staticmethod
    def filename(title):
        if not title.strip():
            raise ValueError("Název písně nesmí být prázdný.")
        stem = unicodedata.normalize("NFD", title).encode("ascii", "ignore").decode().lower()
        stem = re.sub(r"[^a-z0-9_]", "", re.sub(r"\s+", "_", stem)).strip("_")
        if not stem:
            raise ValueError("Název musí obsahovat alespoň jedno písmeno použitelné v názvu souboru nebo číslici.")
        if stem.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
            stem = "song_" + stem
        return stem + ".xml"
