"""Immutable source model. IDs survive editing; duplication must allocate new IDs."""
from dataclasses import dataclass, field
from enum import Enum
import re
from uuid import uuid4

SCHEMA_VERSION = 1

def new_id() -> str:
    return str(uuid4())

class Aspect(str, Enum):
    STANDARD = '4:3'
    WIDE = '16:9'

class BlockKind(str, Enum):
    PARAGRAPH = 'paragraph'
    BULLET = 'bullet'

@dataclass(frozen=True)
class TextStyle:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str = '#ffffff'

    def __post_init__(self):
        if any(type(v) is not bool for v in (self.bold, self.italic, self.underline)):
            raise ValueError('Formatting flags must be boolean')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', self.color):
            raise ValueError('Color must be #RRGGBB')

@dataclass(frozen=True)
class TextRun:
    text: str
    style: TextStyle = field(default_factory=TextStyle)
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        if type(self.text) is not str or not isinstance(self.style, TextStyle):
            raise ValueError('Invalid text run')

@dataclass(frozen=True)
class TextBlock:
    runs: tuple[TextRun, ...]
    kind: BlockKind = BlockKind.PARAGRAPH
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        if type(self.runs) is not tuple or not isinstance(self.kind, BlockKind) or any(not isinstance(r, TextRun) for r in self.runs):
            raise ValueError('Invalid text block')

@dataclass(frozen=True)
class ImportOrigin:
    """Optional provenance for future adapters; no PPTX importer in PP1."""
    format: str
    source: str
    item_key: str

@dataclass(frozen=True)
class TextSection:
    title: str
    blocks: tuple[TextBlock, ...]
    reference: str = ''
    break_after: bool = True
    origin: ImportOrigin | None = None
    id: str = field(default_factory=new_id)
    break_before: bool = False

    def __post_init__(self):
        if type(self.blocks) is not tuple or any(not isinstance(b, TextBlock) for b in self.blocks):
            raise ValueError('Invalid section blocks')

@dataclass(frozen=True)
class ImageSection:
    title: str
    media_id: str
    alt_text: str = ''
    reference: str = ''
    break_after: bool = True
    origin: ImportOrigin | None = None
    id: str = field(default_factory=new_id)
    break_before: bool = False

@dataclass(frozen=True)
class MediaAsset:
    """Logical media identity; locator is not yet a portable embedded asset."""
    locator: str
    mime_type: str
    id: str = field(default_factory=new_id)

@dataclass(frozen=True)
class CameraRegion:
    x: float = .5
    y: float = .5
    width: float = .5
    height: float = .5
    gap: float = .02

    def __post_init__(self):
        values = (self.x, self.y, self.width, self.height, self.gap)
        if any(type(v) not in (int, float) or not 0 <= v <= 1 for v in values):
            raise ValueError('Camera geometry must be normalized')
        if self.width == 0 or self.height == 0 or self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError('Camera rectangle outside output')

@dataclass(frozen=True)
class OutputConfig:
    aspect: Aspect
    camera: CameraRegion | None = None

    def __post_init__(self):
        if not isinstance(self.aspect, Aspect) or (self.camera is not None and not isinstance(self.camera, CameraRegion)):
            raise ValueError('Invalid output configuration')

@dataclass(frozen=True)
class Presentation:
    title: str = 'Nová prezentace'
    sections: tuple[TextSection | ImageSection, ...] = ()
    media: tuple[MediaAsset, ...] = ()
    hall: OutputConfig = field(default_factory=lambda: OutputConfig(Aspect.STANDARD))
    stream: OutputConfig = field(default_factory=lambda: OutputConfig(Aspect.WIDE, CameraRegion()))
    black_start: bool = True
    id: str = field(default_factory=new_id)
    schema_version: int = SCHEMA_VERSION
    black_end: bool = False

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION:
            raise ValueError('Unsupported presentation schema')
        ids = [self.id]
        for sequence in (self.sections, self.media):
            if type(sequence) is not tuple:
                raise ValueError('Source collections must be immutable tuples')
            if any(not isinstance(item, (TextSection, ImageSection, MediaAsset)) for item in sequence):
                raise ValueError('Invalid source item')
            ids.extend(item.id for item in sequence)
        if any(not isinstance(asset, MediaAsset) for asset in self.media):
            raise ValueError('Invalid media asset')
        assets = {asset.id for asset in self.media}
        for section in self.sections:
            if type(section.title) is not str or type(section.reference) is not str:
                raise ValueError('Section title and reference must be strings')
            if section.origin is not None and not isinstance(section.origin, ImportOrigin):
                raise ValueError('Invalid import provenance')
            if type(section.break_after) is not bool:
                raise ValueError('break_after must be boolean')
            if type(section.break_before) is not bool:
                raise ValueError('break_before must be boolean')
            if isinstance(section, TextSection):
                if type(section.blocks) is not tuple:
                    raise ValueError('Blocks must be immutable tuples')
                for block in section.blocks:
                    if type(block.runs) is not tuple or not isinstance(block.kind, BlockKind):
                        raise ValueError('Invalid text block')
                    ids.append(block.id)
                    ids.extend(run.id for run in block.runs)
                    if any(type(run.text) is not str for run in block.runs):
                        raise ValueError('Text must be a string')
            elif isinstance(section, ImageSection):
                if section.media_id not in assets:
                    raise ValueError('Image references unknown media')
            else:
                raise ValueError('Unknown section type')
        if any(type(i) is not str or not i.strip() for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('Content IDs must be nonempty and globally unique')
        if type(self.black_start) is not bool:
            raise ValueError('black_start must be boolean')
        if type(self.black_end) is not bool:
            raise ValueError('black_end must be boolean')
        for output in (self.hall, self.stream):
            if not isinstance(output, OutputConfig):
                raise ValueError('Invalid aspect ratio')
