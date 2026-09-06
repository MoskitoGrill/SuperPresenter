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
    title: str
    variants: list[SongVariant] = field(default_factory=list)
    repetitions: list[SongRepetition] = field(default_factory=list)
    source_path: Path | None = field(default=None, compare=False)
    attributes: dict[str, str] = field(default_factory=dict)
    xml_tail: str | None = field(default=None, compare=False, repr=False)

    xml_text: str | None = field(default=None, compare=False, repr=False)
    repetition_locations: list[tuple[int | None, int]] = field(
        default_factory=list, compare=False, repr=False)

    @property
    def selected_repetition(self) -> SongRepetition | None:
        """First marked main, otherwise first repetition; never reorder data."""
        return next((r for r in self.repetitions if r.is_main),
                    self.repetitions[0] if self.repetitions else None)
