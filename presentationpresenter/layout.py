"""Derived plan contracts. Font measurement and pagination belong to PP2."""
from dataclasses import dataclass
from .domain import Presentation

@dataclass(frozen=True)
class ContentRange:
    section_id: str
    block_id: str
    run_id: str
    start: int
    end: int

    def __post_init__(self):
        if type(self.start) is not int or type(self.end) is not int or not 0 <= self.start <= self.end:
            raise ValueError('Invalid source range')

@dataclass(frozen=True)
class Slide:
    id: str
    section_id: str | None = None
    ranges: tuple[ContentRange, ...] = ()
    media_id: str | None = None
    black: bool = False

    def __post_init__(self):
        if type(self.id) is not str or not self.id or type(self.ranges) is not tuple or type(self.black) is not bool:
            raise ValueError('Invalid slide')
        if any(not isinstance(span, ContentRange) for span in self.ranges):
            raise ValueError('Invalid slide ranges')

@dataclass(frozen=True)
class SlidePlan:
    source: Presentation
    slides: tuple[Slide, ...]

    def __post_init__(self):
        if type(self.slides) is not tuple or len({s.id for s in self.slides}) != len(self.slides):
            raise ValueError('Slides must have unique IDs and immutable storage')
        sections = {s.id: s for s in self.source.sections}
        for slide in self.slides:
            if slide.black:
                if slide.section_id is not None and slide.section_id not in sections:
                    raise ValueError('Black slide references unknown section')
                if slide.ranges or slide.media_id:
                    raise ValueError('Black slide cannot contain content')
                continue
            section = sections.get(slide.section_id)
            if section is None:
                raise ValueError('Slide references unknown section')
            if hasattr(section, 'media_id') and (slide.media_id != section.media_id or slide.ranges):
                raise ValueError('Image slide must reference section media only')
            if slide.media_id is not None and slide.media_id != getattr(section, 'media_id', None):
                raise ValueError('Slide references wrong media')
            runs = {(b.id, r.id): r for b in getattr(section, 'blocks', ()) for r in b.runs}
            for span in slide.ranges:
                run = runs.get((span.block_id, span.run_id))
                if span.section_id != section.id or run is None or span.end > len(run.text):
                    raise ValueError('Slide range outside source')

def with_black_breaks(source: Presentation, content: tuple[Slide, ...]) -> SlidePlan:
    """Wrap already paginated content. Never creates adjacent black slides."""
    result = []
    def black(key, section_id=None):
        if not result or not result[-1].black:
            result.append(Slide(key, section_id, black=True))
    if source.black_start:
        black(f'{source.id}:start')
    if any(s.black for s in content):
        raise ValueError('Expected content slides only')
    ordered = []
    for section in source.sections:
        section_slides = [s for s in content if s.section_id == section.id]
        ordered.extend(section_slides)
        result.extend(section_slides)
        if section.break_after:
            black(f'{section.id}:after', section.id)
    if tuple(ordered) != content:
        raise ValueError('Content must follow source section order')
    return SlidePlan(source, tuple(result))
