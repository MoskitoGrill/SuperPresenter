"""Stable section/block anchors, mapped through individual draft revisions."""
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
import re


def text(block):
    return ''.join(r.text for r in block.runs)


@dataclass(frozen=True)
class Anchor:
    section_id: str | None
    block_id: str | None = None
    offset: int = 0
    black_id: str | None = None


def capture(plan, slide):
    if slide.black:
        return Anchor(slide.section_id, black_id=slide.id)
    if not slide.ranges:
        return Anchor(slide.section_id)
    span = slide.ranges[0]
    section = next(s for s in plan.source.sections if s.id == span.section_id)
    block = next(b for b in section.blocks if b.id == span.block_id)
    offset = span.start
    for run in block.runs:
        if run.id == span.run_id:
            break
        offset += len(run.text)
    return Anchor(section.id, block.id, offset)


def sentence(value, offset):
    starts = [0] + [m.end() for m in re.finditer(r'[.!?]\s*|\n', value)]
    start = max((p for p in starts if p <= offset), default=0)
    end = next((p for p in starts if p > offset), len(value))
    return start, end


def edit(anchor, value, start, end, inserted):
    """Exact editor operation; repeated strings never choose an occurrence."""
    a, b = sentence(value, anchor.offset)
    following = value[:start] + inserted + value[end:]
    if start == end and start <= anchor.offset:
        return replace(anchor, offset=anchor.offset + len(inserted))
    if start <= a and end >= b and not inserted:
        offset = start
        while offset < len(following) and following[offset].isspace():
            offset += 1
        return replace(anchor, offset=offset if offset < len(following) else 0)
    if start < b and end > a:
        mapped_start = a if start >= a else start
        return replace(anchor, offset=sentence(following, mapped_start)[0])
    if end <= anchor.offset:
        return replace(anchor, offset=anchor.offset + len(inserted) - (end-start))
    return anchor


def first(section):
    blocks = getattr(section, 'blocks', ())
    return Anchor(section.id, blocks[0].id if blocks else None)


def relocate(anchor, old, new):
    if anchor is None:
        return None
    sections = {s.id: s for s in new.sections}
    section = sections.get(anchor.section_id)
    if anchor.section_id is not None and section is None:
        ids = [s.id for s in old.sections]
        index = ids.index(anchor.section_id) if anchor.section_id in ids else -1
        section = next((sections[sid] for sid in ids[index+1:] if sid in sections),
                       new.sections[0] if new.sections else None)
        return first(section) if section else Anchor(None)
    if anchor.black_id or not anchor.block_id or section is None:
        return anchor
    previous = next((s for s in old.sections if s.id == anchor.section_id), None)
    old_blocks = getattr(previous, 'blocks', ())
    blocks = {b.id: b for b in getattr(section, 'blocks', ())}
    block = blocks.get(anchor.block_id)
    if block is None:
        ids = [b.id for b in old_blocks]
        index = ids.index(anchor.block_id) if anchor.block_id in ids else -1
        block = next((blocks[bid] for bid in ids[index+1:] if bid in blocks), None)
        return Anchor(section.id, block.id) if block else first(section)
    old_block = next((b for b in old_blocks if b.id == anchor.block_id), None)
    if old_block is None:
        return replace(anchor, offset=min(anchor.offset, len(text(block))))
    before, after = text(old_block), text(block)
    # Structural commands/history fallback. Normal typing uses exact operations.
    delta = 0
    for op, a, b, c, d in SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
        if op != 'equal':
            anchor = edit(anchor, before, a+delta, b+delta, after[c:d])
            before = before[:a+delta] + after[c:d] + before[b+delta:]
            delta += (d-c)-(b-a)
    return anchor


def position(source, anchor):
    """Comparable source position; identity selects the section and block."""
    section = next((s for s in source.sections if s.id == anchor.section_id), None)
    for index, block in enumerate(getattr(section, 'blocks', ())):
        if block.id == anchor.block_id:
            return index, anchor.offset
    return None


def locate(plan, anchor, mapped=None, mapped_source=None):
    """Find the naturally paginated slide containing a stable text anchor.

    For draft-to-live previews, mapped live starts describe their positions in
    the draft without ambiguous reverse text matching.
    """
    if not plan.slides:
        return None
    if anchor and anchor.black_id:
        exact = next((s for s in plan.slides if s.id == anchor.black_id), None)
        if exact:
            return exact.id
        if anchor.black_id.endswith(':end'):
            return plan.slides[-1].id
    if anchor:
        source = mapped_source or plan.source
        target = position(source, anchor)
        candidate = None
        for slide in plan.slides:
            start = mapped.get(slide.id) if mapped else capture(plan, slide)
            if slide.black or start is None or start.section_id != anchor.section_id:
                continue
            if not anchor.block_id:
                return slide.id
            beginning = position(source, start)
            if target is not None and beginning is not None and beginning <= target:
                candidate = slide.id
        if candidate:
            return candidate
        return next((s.id for s in plan.slides if s.section_id == anchor.section_id and not s.black), plan.slides[0].id)
    return plan.slides[0].id


def confirmed_position(previous, current_slide_id, plan, anchor):
    """Keep the same continuation of a surviving section, clamped to its end.

    This applies only to publication. Preview mapping still follows text anchors.
    Stable section identity avoids shifts caused by other sections or black slides.
    """
    current = next((s for s in previous.slides if s.id == current_slide_id), None)
    if current and not current.black:
        before = [s for s in previous.slides if s.section_id == current.section_id and not s.black]
        after = [s for s in plan.slides if s.section_id == current.section_id and not s.black]
        if after:
            ordinal = next(i for i, s in enumerate(before) if s.id == current.id)
            return after[min(ordinal, len(after)-1)].id
    return locate(plan, anchor)
