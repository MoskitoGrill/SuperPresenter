"""Ordered song data. Text is never stripped or interpreted here."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SongSection:
    identifier: str
    # Split on LF only: preserve empty lines, indentation and Unicode separators.
    lines: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    xml_tail: str | None = field(default=None, compare=False, repr=False)


@dataclass
class SongVariant:
    name: str
    sections: list[SongSection] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    xml_tail: str | None = field(default=None, compare=False, repr=False)

    xml_text: str | None = field(default=None, compare=False, repr=False)


@dataclass
class SongRepetition:
    name: str
    guide: str
    is_main: bool = False
    attributes: dict[str, str] = field(default_factory=dict)
    xml_tail: str | None = field(default=None, compare=False, repr=False)


@dataclass
class Song:
    title: str = ""
    variants: list[SongVariant] = field(default_factory=list)
    repetitions: list[SongRepetition] = field(default_factory=list)
    source_path: Path | None = field(default=None, compare=False)
    attributes: dict[str, str] = field(default_factory=dict)
    xml_tail: str | None = field(default=None, compare=False, repr=False)

    xml_text: str | None = field(default=None, compare=False, repr=False)
    repetition_locations: list[tuple[int | None, int]] = field(
        default_factory=list, compare=False, repr=False)

    # Unknown root metadata is retained without interpreting it as song content.
    extra_elements: list = field(default_factory=list, compare=False, repr=False)

    @classmethod
    def from_texts(cls, title="", variants=None, repetitions=None, main="default"):
        """Build the ordered model from text fields (drafts and legacy import)."""
        repetitions = {"default": ""} if repetitions is None else repetitions
        return cls(title,
                   [SongVariant(name, [SongSection(sid, text.split('\n'))
                                       for sid, text in sections.items()])
                    for name, sections in (variants or {}).items()],
                   [SongRepetition(name, text, name == main)
                    for name, text in repetitions.items()])

    @property
    def variant_texts(self):
        """A read-only projection for existing editor fields, never stored state."""
        return {variant.name or f"variant {i}":
                {section.identifier or f"s{j}": '\n'.join(section.lines).strip()
                 for j, section in enumerate(variant.sections, 1)}
                for i, variant in enumerate(self.variants, 1)}

    @property
    def repetition_texts(self):
        return {rep.name or "default": rep.guide.strip() for rep in self.repetitions}

    @property
    def main_repetition(self):
        """Editor/presenter selection: marked main, default, then first."""
        marked = next((rep for rep in self.repetitions if rep.is_main), None)
        if marked is not None:
            return marked.name or "default"
        names = self.repetition_texts
        return "default" if "default" in names else next(iter(names), "")

    @property
    def guide(self):
        return self.repetition_texts.get(self.main_repetition, "")

    @property
    def selected_repetition(self) -> SongRepetition | None:
        """First marked main, otherwise first repetition; never reorder data."""
        return next((r for r in self.repetitions if r.is_main),
                    self.repetitions[0] if self.repetitions else None)
