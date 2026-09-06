"""Pure stationary pagination. All indexes are zero-based; ranges are half-open.

The caller resolves construct order and language before pagination. Each section
occurrence needs a persistent unique ID (including repeated occurrences).
Explicit pinned/repeated copies are ordinary capacity-consuming input rows.
"""
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote


@dataclass(frozen=True)
class SourceLine:
    text: str
    section_id: str
    line_index: int
    pinned: bool = False
    repeated: bool = False

    def __post_init__(self):
        if not self.section_id or self.line_index < 0:
            raise ValueError('Source line needs a section ID and nonnegative index')
        if '\n' in self.text or '\r' in self.text:
            raise ValueError('One SourceLine must contain exactly one physical row')


@dataclass(frozen=True)
class LogicalSection:
    occurrence_id: str
    lines: tuple[SourceLine, ...]

    def __post_init__(self):
        object.__setattr__(self, 'lines', tuple(self.lines))
        if not self.occurrence_id:
            raise ValueError('Section occurrence ID must not be empty')


@dataclass(frozen=True)
class SourceRange:
    section_id: str
    start: int
    stop: int
    pinned: bool
    repeated: bool


@dataclass(frozen=True)
class HallPage:
    index: int
    lines: tuple[SourceLine, ...]


@dataclass(frozen=True)
class StreamPage:
    index: int
    hall_page_index: int
    hall_start: int
    lines: tuple[SourceLine, ...]


@dataclass(frozen=True)
class PresentationCue:
    step_index: int
    hall_page: HallPage
    stream_page: StreamPage
    occurrence_id: str
    source_ranges: tuple[SourceRange, ...]
    navigation_id: str


@dataclass(frozen=True)
class PresentationPlan:
    hall_pages: tuple[HallPage, ...]
    stream_pages: tuple[StreamPage, ...]
    cues: tuple[PresentationCue, ...]


def _source_ranges(lines: tuple[SourceLine, ...]) -> tuple[SourceRange, ...]:
    ranges = []
    for line in lines:
        current = SourceRange(line.section_id, line.line_index,
                              line.line_index + 1, line.pinned, line.repeated)
        if ranges:
            previous = ranges[-1]
            if (previous.section_id == current.section_id
                    and previous.stop == current.start
                    and previous.pinned == current.pinned
                    and previous.repeated == current.repeated):
                ranges[-1] = SourceRange(previous.section_id, previous.start,
                                         current.stop, current.pinned, current.repeated)
                continue
        ranges.append(current)
    return tuple(ranges)


def generate_pages(sections: Iterable[LogicalSection]) -> PresentationPlan:
    """Keep section boundaries; split hall pages at 8 and their streams at 4.

    Empty sections produce no pages. Blank text rows count toward capacity.
    Navigation IDs survive unrelated section insertion and text-only edits;
    changing row order or count may change the meaning of an ID.
    """
    halls, streams, cues = [], [], []
    seen = set()
    for section in sections:
        if section.occurrence_id in seen:
            raise ValueError('Duplicate section occurrence ID: ' + section.occurrence_id)
        seen.add(section.occurrence_id)
        for start in range(0, len(section.lines), 8):
            hall = HallPage(len(halls), section.lines[start:start + 8])
            halls.append(hall)
            for offset in range(0, len(hall.lines), 4):
                stream = StreamPage(len(streams), hall.index, offset,
                                    hall.lines[offset:offset + 4])
                streams.append(stream)
                cues.append(PresentationCue(
                    len(cues), hall, stream, section.occurrence_id,
                    _source_ranges(stream.lines),
                    f'{quote(section.occurrence_id, safe="")}:row:{start + offset}',
                ))
    return PresentationPlan(tuple(halls), tuple(streams), tuple(cues))


def format_timeline(plan: PresentationPlan) -> str:
    """Human-readable diagnostics, with one-based display numbering."""
    return '\n'.join(
        f'cue {cue.step_index + 1} -> hall {cue.hall_page.index + 1} / '
        f'stream {cue.hall_page.index + 1}.{cue.stream_page.hall_start // 4 + 1}'
        f' [{cue.navigation_id}]'
        for cue in plan.cues
    )


if __name__ == '__main__':
    print(format_timeline(generate_pages([
        LogicalSection('v1-first', tuple(SourceLine(str(i + 1), 'v1', i)
                                        for i in range(10))),
    ])))
