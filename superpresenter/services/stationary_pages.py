"""Pure stationary pagination. All indexes are zero-based; ranges are half-open.

The caller resolves construct order and language before pagination. Each section
occurrence needs a persistent unique ID (including repeated occurrences).
Explicit pinned/repeated copies are ordinary capacity-consuming input rows.
"""
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote

from superpresenter.domain.song import SongVariant
from superpresenter.services.construct_parser import (
    Construct, RepeatGroup, InvalidPinError,
)


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
    # An ordinary construct row selection may extend its own preceding verse.
    # Whole sections and explicit forward pins retain their original semantics.
    append_to_previous: bool = False

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
    """Append same-section selections and forward pins only when they fit 8.

    Empty sections produce no pages. Blank text rows count toward capacity.
    Navigation IDs survive unrelated section insertion and text-only edits;
    changing row order or count may change the meaning of an ID.
    """
    halls, streams, cues = [], [], []
    seen = set()
    blocks = []
    for section in sections:
        if section.occurrence_id in seen:
            raise ValueError('Duplicate section occurrence ID: ' + section.occurrence_id)
        seen.add(section.occurrence_id)
        if section.lines:
            blocks.append((section.lines, tuple((section.occurrence_id, i)
                                                for i in range(len(section.lines))),
                           section.append_to_previous))
    # First collect each uninterrupted run of ordinary selections of the same
    # source section. Treat the entire run as one block so 5 + 4 stays 5 / 4,
    # rather than filling the first page with only three repeated copies.
    selected_blocks = []
    for rows, owners, append in blocks:
        source_ids = {row.section_id for row in rows}
        if (append and selected_blocks and selected_blocks[-1][2]
                and len(source_ids) == 1
                and source_ids == {row.section_id for row in selected_blocks[-1][0]}):
            previous_rows, previous_owners, _ = selected_blocks[-1]
            selected_blocks[-1] = (previous_rows + rows, previous_owners + owners, True)
        else:
            selected_blocks.append((rows, owners, append))
    blocks = []
    for rows, owners, append in selected_blocks:
        source_ids = {row.section_id for row in rows}
        explicit_append = all(row.pinned for row in rows)
        automatic_append = (append and blocks and len(source_ids) == 1
                            and source_ids == {row.section_id for row in blocks[-1][0]}
                            and not any(row.pinned for row in blocks[-1][0]))
        if (blocks and (explicit_append or automatic_append)
                and len(blocks[-1][0]) + len(rows) <= 8):
            previous_rows, previous_owners = blocks[-1]
            blocks[-1] = (previous_rows + rows, previous_owners + owners)
        else:
            blocks.append((rows, owners))
    for rows, owners in blocks:
        for start in range(0, len(rows), 8):
            hall = HallPage(len(halls), rows[start:start + 8])
            halls.append(hall)
            for offset in range(0, len(hall.lines), 4):
                stream = StreamPage(len(streams), hall.index, offset,
                                    hall.lines[offset:offset + 4])
                streams.append(stream)
                occurrence_id, source_offset = owners[start + offset]
                cues.append(PresentationCue(
                    len(cues), hall, stream, occurrence_id,
                    _source_ranges(stream.lines),
                    f'{quote(occurrence_id, safe="")}:row:{source_offset}',
                ))
    return PresentationPlan(tuple(halls), tuple(streams), tuple(cues))


def presentation_lines(lines: Iterable[str]) -> tuple[str, ...]:
    """Legacy song display numbering: nonblank LF rows with outer space removed.

    Repository text is preserved; this is an explicit projection-only view.
    """
    return tuple(line.strip() for line in lines if line.strip())


def resolve_sections(construct: Construct, variant: SongVariant) -> Iterable[LogicalSection]:
    """Resolve one language and expand occurrences lazily, without text matching.

    Pinned steps are explicit extra occurrences, never implicit tail copies.
    IDs use instruction position and repeat path, not text or global page index.
    """
    sections = {}
    for section in variant.sections:
        if section.identifier in sections:
            raise ValueError('Duplicate section ID: ' + section.identifier)
        sections[section.identifier] = presentation_lines(section.lines)
    pending = [(iter(construct.instructions), '', False)]
    while pending:
        nodes, path, repeated = pending[-1]
        node = next(nodes, None)
        if node is None:
            pending.pop()
            continue
        if isinstance(node, RepeatGroup):
            # A generator avoids allocating one entry per repetition.
            def children(group, parent_path, parent_repeated):
                for iteration in range(group.repeat):
                    yield (iter(group.children),
                           f'{parent_path}g{group.position}.{iteration}/',
                           parent_repeated or iteration > 0)
            # Process group iterations via a separate iterator frame.
            pending.append((iter(children(node, path, repeated)), path, repeated))
            continue
        if isinstance(node, tuple):
            pending.append(node)
            continue
        rows = sections[node.section]
        indices = (range(len(rows)) if node.start_line is None else
                   range(node.start_line - 1, (node.end_line or node.start_line)))
        if node.pinned and any(i < 0 or i >= len(rows) for i in indices):
            raise InvalidPinError('Připnutý řádek neexistuje ve vybrané variantě', node.position)
        selected = tuple(SourceLine(rows[i] if -len(rows) <= i < len(rows) else '',
                                    node.section, i if i >= 0 else max(len(rows) - 1, 0),
                                    node.pinned, node.pinned or repeated) for i in indices)
        yield LogicalSection(f'{path}s{node.position}', selected,
                             append_to_previous=node.start_line is not None and not node.pinned)


def format_timeline(plan: PresentationPlan) -> str:
    """Human-readable diagnostics, with one-based display numbering."""
    return '\n'.join(
        f'cue {cue.step_index + 1} -> hall {cue.hall_page.index + 1} / '
        f'stream {cue.hall_page.index + 1}.{cue.stream_page.hall_start // 4 + 1}'
        f' [{cue.navigation_id}]'
        for cue in plan.cues
    )
