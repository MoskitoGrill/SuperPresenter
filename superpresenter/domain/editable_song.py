"""Shared, GUI-independent song representation; template retains XML metadata."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EditableSong:
    title: str = ""
    variants: dict[str, dict[str, str]] = field(default_factory=dict)
    repetitions: dict[str, str] = field(default_factory=lambda: {"default": ""})
    main_repetition: str = "default"
    template: Any = field(default=None, repr=False, compare=False)

    @property
    def guide(self):
        return self.repetitions.get(self.main_repetition, "")
