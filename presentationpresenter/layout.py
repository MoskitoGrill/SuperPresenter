"""Immutable common slides and independent measured output layouts."""
from __future__ import annotations
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
    hall: OutputLayout | None = None
    stream: OutputLayout | None = None
    block_ids: tuple[str, ...] = ()

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
        if section.break_before:
            black(f'{section.id}:before', section.id)
        section_slides = [s for s in content if s.section_id == section.id]
        ordered.extend(section_slides)
        result.extend(section_slides)
        if section.break_after:
            black(f'{section.id}:after', section.id)
    if source.black_end and source.sections:
        black(f'{source.id}:end')
    if tuple(ordered) != content:
        raise ValueError('Content must follow source section order')
    return SlidePlan(source, tuple(result))

# PP2: measurement is injected; this module remains independent of Tk/UI.
from .domain import Aspect, BlockKind, TextSection, TextStyle

class LayoutError(ValueError):
    pass

@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    def intersects(self, other):
        return (self.x < other.x + other.width and other.x < self.x + self.width
                and self.y < other.y + other.height and other.y < self.y + self.height)

@dataclass(frozen=True)
class Piece:
    text: str
    style: TextStyle
    box: Rect
    source: ContentRange | None = None
    font_size: int = 36

@dataclass(frozen=True)
class OutputLayout:
    width: int
    height: int
    pieces: tuple[Piece, ...]
    camera: Rect | None
    exclusion: Rect | None
    image_box: Rect | None = None
    image_locator: str | None = None
    images: tuple[PlacedImage, ...] = ()
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class PlacedImage:
    item_id: str
    locator: str
    box: Rect

@dataclass(frozen=True)
class Typography:
    body: int = 36
    heading: int = 24
    margin: int = 32
    paragraph_gap: int = 16
    bullet_indent: int = 40


def geometry(config):
    width, height = (960 if config.aspect == Aspect.STANDARD else 1280), 720
    c = config.camera
    camera = Rect(c.x * width, c.y * height, c.width * width, c.height * height) if c else None
    exclusion = Rect((c.x-c.gap)*width, (c.y-c.gap)*height,
                     (c.width+2*c.gap)*width, (c.height+2*c.gap)*height) if c else None
    return width, height, camera, exclusion


def _ranges(chars):
    result = []
    for text, style, span in chars:
        if result and result[-1].run_id == span.run_id and result[-1].end == span.start:
            previous = result[-1]
            result[-1] = ContentRange(previous.section_id, previous.block_id, previous.run_id, previous.start, span.end)
        else:
            result.append(span)
    return tuple(result)


def _chars(section, block):
    return [(char, run.style, ContentRange(section.id, block.id, run.id, i, i+1))
            for run in block.runs for i, char in enumerate(run.text)]


def _groups(chars):
    groups = []
    for char, style, span in chars:
        if groups and groups[-1][1] == style and groups[-1][2].run_id == span.run_id:
            text, _, old = groups[-1]
            groups[-1] = (text+char, style, ContentRange(old.section_id, old.block_id, old.run_id, old.start, span.end))
        else:
            groups.append((char, style, span))
    return groups


def _flow(section, chunks, config, metrics, typography, image_layout=None):
    w, h, camera, exclusion = geometry(config)
    t = typography
    pieces = []
    y = t.margin
    obstacles = ([exclusion] if exclusion else [])
    if image_layout:
        obstacles += [Rect(i.box.x-12, i.box.y-12, i.box.width+24, i.box.height+24) for i in image_layout.images]
    def band(y, height, indent=0):
        intervals = [(t.margin, w-t.margin)]
        for obstacle in obstacles:
            if y < obstacle.y+obstacle.height and y+height > obstacle.y:
                intervals = [(a, min(b, obstacle.x)) for a, b in intervals if a < obstacle.x] + [(max(a, obstacle.x+obstacle.width), b) for a, b in intervals if b > obstacle.x+obstacle.width]
        left, right = max(intervals, key=lambda pair: pair[1]-pair[0], default=(t.margin, t.margin))
        return left+indent, right
    heading_style = TextStyle(bold=True)
    heading = ' • '.join(part for part in (section.title, section.reference) if part)
    # Heading also wraps safely around arbitrary future camera geometry.
    remaining = heading
    line_h = metrics.height(heading_style, t.heading)+4
    while remaining:
        x, right = band(y, line_h)
        if y+line_h > h-t.margin:
            raise LayoutError('Název/odkaz zabírá celý snímek')
        n = 0
        while n < len(remaining) and metrics.width(remaining[:n+1].replace('\n', ''), heading_style, t.heading) <= right-x:
            n += 1
            if remaining[n-1] == '\n':
                break
        if not n:
            y += line_h
            continue
        cut = remaining.rfind(' ', 0, n) if n < len(remaining) and remaining[n-1] != '\n' else -1
        if cut > 0:
            n = cut+1
        text = remaining[:n].replace('\n', '')
        size = metrics.width(text, heading_style, t.heading)
        pieces.append(Piece(text, heading_style, Rect(right-size, y, size, line_h), font_size=t.heading))
        remaining = remaining[n:]
        y += line_h
    y += t.paragraph_gap
    numbers = {}
    counts = [0, 0, 0]
    for item in section.blocks:
        depth = item.level
        counts[depth+1:] = [0] * (2-depth)
        if item.kind == BlockKind.NUMBERED:
            counts[depth] += 1
            numbers[item.id] = '.'.join(str(n) for n in counts[:depth+1] if n)
        else:
            counts[depth] = 0
    for block, chars, continued in chunks:
        line_h = max([metrics.height(s, t.body) for _, s, _ in chars] or [metrics.height(TextStyle(), t.body)])+6
        marker = ('↳' if continued else ('•', '◦', '▪')[block.level]) if block.kind == BlockKind.BULLET else ''
        if block.kind == BlockKind.NUMBERED:
            marker = f'{numbers[block.id]}.' + (' ↳' if continued else '')
        marker_indent = max(t.bullet_indent, metrics.width(marker, TextStyle(), t.body)+12) if marker else 0
        indent = marker_indent + block.level*t.bullet_indent
        first = True
        cursor = 0
        while cursor < len(chars) or (first and not chars):
            x, right = band(y, line_h, indent)
            if y+line_h > h-t.margin:
                return None
            if not chars and right-x < (metrics.width('•', TextStyle(), t.body) if indent else 1):
                y += line_h
                continue
            n = 0
            committed_width = 0
            group_text = ''
            group_key = None
            while cursor+n < len(chars):
                char, style, span = chars[cursor+n]
                if char == '\n':
                    n += 1
                    break
                key = (style, span.run_id)
                if key != group_key:
                    if group_key is not None:
                        committed_width += metrics.width(group_text, group_key[0], t.body)
                    group_key, group_text = key, ''
                group_text += char
                width = committed_width + metrics.width(group_text, style, t.body)
                if width > right-x:
                    break
                n += 1
            if not n and cursor < len(chars):
                # An obstructed band can be skipped; an oversized glyph is an explicit error.
                if any(y < o.y+o.height and y+line_h > o.y for o in obstacles):
                    y += line_h
                    continue
                raise LayoutError('Znak se nevejde do dostupné šířky')
            if cursor+n < len(chars) and n and chars[cursor+n-1][0] != '\n':
                boundary = next((i+1 for i in range(n-1, -1, -1) if chars[cursor+i][0].isspace()), 0)
                if boundary:
                    n = boundary
            if first and indent:
                pieces.append(Piece(marker, TextStyle(), Rect(x-marker_indent, y, metrics.width(marker, TextStyle(), t.body), line_h), font_size=t.body))
            for text, style, span in _groups(chars[cursor:cursor+n]):
                # Newlines belong to source ranges but have no visible glyph.
                visible = text.replace('\n', '')
                size = metrics.width(visible, style, t.body)
                pieces.append(Piece(visible, style, Rect(x, y, size, line_h), span, t.body))
                x += size
            cursor += n
            first = False
            y += line_h
        y += t.paragraph_gap
    return OutputLayout(w, h, tuple(pieces), camera, exclusion,
                        images=image_layout.images if image_layout else (), warnings=image_layout.warnings if image_layout else ())


def paginate(source, metrics, typography=Typography()):
    """Greedy common source slices; each output independently wraps those slices."""
    slides = []
    for section in source.sections:
        if not isinstance(section, TextSection):
            from .media import dimensions
            asset = next(a for a in source.media if a.id == section.media_id)
            size = dimensions(asset.locator)
            hall, stream = (image_layout(config, size, asset.locator) for config in (source.hall, source.stream))
            slides.append(Slide(section.id+':media', section.id, media_id=section.media_id, hall=hall, stream=stream))
            continue
        pending = []
        emitted = 0
        from .composition import compose_pair
        first_images = compose_pair(source, section, first=True) if section.images else (None, None)
        other_images = compose_pair(source, section, first=False) if section.images else (None, None)
        def layouts(chunks):
            image_pair = first_images if emitted == 0 else other_images
            if section.images and not any(run.text for b in section.blocks for run in b.runs):
                return image_pair
            return tuple(_flow(section, chunks, output, metrics, typography, images) for output, images in zip((source.hall, source.stream), image_pair))
        def fits(chunks):
            return all(item is not None for item in layouts(chunks))
        def emit(chunks):
            nonlocal emitted
            hall, stream = layouts(chunks)
            spans = tuple(span for _, chars, _ in chunks for span in _ranges(chars))
            anchor = f'{spans[0].run_id}:{spans[0].start}' if spans else (chunks[0][0].id if chunks else 'empty')
            slides.append(Slide(section.id+':'+anchor, section.id, spans, hall=hall, stream=stream,
                                block_ids=tuple(block.id for block, _, _ in chunks)))
            emitted += 1
        for block in section.blocks:
            chars = _chars(section, block)
            continued = False
            pending = _paginate_chunk(block, chars, continued, pending, fits, emit,
                                      lambda: emitted == 0 and any(not i.repeat for i in section.images))
        if pending or not section.blocks:
            emit(pending)
    return with_black_breaks(source, tuple(slides))


def image_layout(config, size, locator):
    """Maximize fitted image area among maximal rectangles outside exclusion."""
    w, h, camera, exclusion = geometry(config)
    candidates = [Rect(0, 0, w, h)]
    if exclusion:
        x = max(0, min(w, exclusion.x))
        y = max(0, min(h, exclusion.y))
        right = max(0, min(w, exclusion.x + exclusion.width))
        bottom = max(0, min(h, exclusion.y + exclusion.height))
        candidates = [Rect(0, 0, x, h), Rect(0, 0, w, y),
                      Rect(right, 0, w-right, h), Rect(0, bottom, w, h-bottom)]
    def fit(box):
        factor = min(box.width/size[0], box.height/size[1])
        iw, ih = size[0]*factor, size[1]*factor
        return Rect(box.x+(box.width-iw)/2, box.y+(box.height-ih)/2, iw, ih)
    fitted = [fit(box) for box in candidates if box.width > 0 and box.height > 0]
    if not fitted:
        raise LayoutError('Kamera nezanechává plochu pro obrázek')
    box = max(fitted, key=lambda b: b.width*b.height)
    return OutputLayout(w, h, (), camera, exclusion, box, locator)


def _paginate_chunk(block, chars, continued, pending, fits, emit, can_advance=lambda: False):
    if pending and block.kind in (BlockKind.BULLET, BlockKind.NUMBERED) and not fits(pending+[(block, chars, False)]) and fits([(block, chars, False)]):
        emit(pending)
        pending = []
    while True:
        if fits(pending+[(block, chars, continued)]):
            pending.append((block, chars, continued))
            break
        low, high = 0, len(chars)
        while low < high:
            mid = (low+high+1)//2
            if fits(pending+[(block, chars[:mid], continued)]):
                low = mid
            else:
                high = mid-1
        if not low:
            if pending:
                emit(pending)
                pending = []
                continue
            if can_advance():
                emit([])
                continue
            raise LayoutError('Obsah nemá místo pod názvem a mimo kameru')
        # Prefer a word boundary, retaining every source character.
        boundary = next((i+1 for i in range(low-1, -1, -1) if chars[i][0].isspace()), 0)
        if boundary:
            low = boundary
        pending.append((block, chars[:low], continued))
        emit(pending)
        pending = []
        chars = chars[low:]
        continued = True
    return pending
