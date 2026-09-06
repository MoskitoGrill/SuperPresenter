"""Song XML IO shared by the embedded editor and presentation adapter."""
from copy import deepcopy
import os
from pathlib import Path
import re
import tempfile
import unicodedata
import xml.etree.ElementTree as ET

from superpresenter.domain.editable_song import EditableSong as Song


class SongEditorRepository:
    def load(self, path):
        root = ET.parse(path).getroot()
        if root.tag != "slide":
            raise ValueError(f"{path}: očekáván kořenový element slide")
        variants = {}
        for i, variant in enumerate(root.findall("variant"), 1):
            name = variant.get("name") or f"variant {i}"
            if name in variants:
                raise ValueError(f"Duplicitní jazyk: {name}")
            sections = {}
            for j, section in enumerate(variant.findall("section"), 1):
                sid = section.get("name") or f"s{j}"
                if sid in sections:
                    raise ValueError(f"Duplicitní sekce: {name}/{sid}")
                sections[sid] = (section.text or "").strip()
            variants[name] = sections
        repetitions = {}
        main = None
        for rep in root.findall("repetition"):
            name = rep.get("name") or "default"
            if name in repetitions:
                raise ValueError(f"Duplicitní opakování: {name}")
            repetitions[name] = (rep.text or "").strip()
            if main is None and rep.get("main", "").lower() in ("1", "true", "yes"):
                main = name
        main = main or ("default" if "default" in repetitions else next(iter(repetitions), ""))
        return Song(root.get("name") or Path(path).stem, variants, repetitions, main, root)

    def serialize(self, song):
        root = deepcopy(song.template) if song.template is not None else ET.Element("slide")
        root.set("name", song.title)
        def sync(parent, tag, values):
            old = {node.get("name"): node for node in parent.findall(tag)}
            for node in parent.findall(tag):
                parent.remove(node)
            for name in values:
                node = old.get(name)
                if node is None:
                    node = ET.Element(tag)
                node.set("name", name)
                parent.append(node)
                yield name, node
        for name, variant in sync(root, "variant", song.variants):
            for sid, section in sync(variant, "section", song.variants[name]):
                section.text = "\n" + song.variants[name][sid] + "\n"
        for name, rep in sync(root, "repetition", song.repetitions):
            rep.attrib.pop("main", None)
            if name == song.main_repetition:
                rep.set("main", "1")
            rep.text = "\n" + song.repetitions[name] + "\n"
        ET.indent(root, space="    ")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

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

    def save(self, song, path, *, overwrite=False):
        if not song.title.strip():
            raise ValueError("Název písně nesmí být prázdný.")
        target = Path(path)
        payload = self.serialize(song)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".song-", suffix=".tmp", delete=False) as handle:
                temporary = handle.name
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if overwrite:
                os.replace(temporary, target)
            else:
                # Atomic publication without overwriting a concurrently created file.
                os.link(temporary, target)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
