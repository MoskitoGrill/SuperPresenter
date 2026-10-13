"""Versioned source codec. Portable envelopes and atomic file actions: storage."""
import json
from dataclasses import asdict
from .domain import (Presentation, TextSection, ImageSection, TextBlock, TextRun,
                     TextStyle, ImportOrigin, MediaAsset, OutputConfig, Aspect,
                     BlockKind, CameraRegion, SCHEMA_VERSION, ImageItem, ImagePlacement)

def dumps(document: Presentation) -> str:
    data = asdict(document)
    for section, encoded in zip(document.sections, data['sections']):
        encoded['type'] = 'text' if isinstance(section, TextSection) else 'image'
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)

def loads(payload: str) -> Presentation:
    try:
        data = json.loads(payload)
        if type(data['schema_version']) is not int or data['schema_version'] not in (1, SCHEMA_VERSION):
            raise ValueError('Unsupported presentation schema')
        data['schema_version'] = SCHEMA_VERSION
        def output(raw):
            raw = dict(raw)
            raw['aspect'] = Aspect(raw['aspect'])
            if raw.get('camera') is not None:
                raw['camera'] = CameraRegion(**raw['camera'])
            return OutputConfig(**raw)
        sections = []
        for raw in data['sections']:
            raw = dict(raw)
            kind = raw.pop('type')
            if raw.get('origin') is not None:
                raw['origin'] = ImportOrigin(**raw['origin'])
            if kind == 'text':
                images = []
                for item in raw.get('images', []):
                    item = dict(item)
                    for field in ('hall', 'stream'):
                        if item.get(field) is not None:
                            item[field] = ImagePlacement(**item[field])
                    images.append(ImageItem(**item))
                raw['images'] = tuple(images)
                blocks = []
                for block in raw['blocks']:
                    block = dict(block)
                    block['kind'] = BlockKind(block['kind'])
                    block['runs'] = tuple(TextRun(**{**r, 'style': TextStyle(**r['style'])}) for r in block['runs'])
                    blocks.append(TextBlock(**block))
                raw['blocks'] = tuple(blocks)
                sections.append(TextSection(**raw))
            elif kind == 'image':
                sections.append(ImageSection(**raw))
            else:
                raise ValueError('Unknown section type')
        data['sections'] = tuple(sections)
        data['media'] = tuple(MediaAsset(**m) for m in data['media'])
        data['hall'] = output(data['hall'])
        data['stream'] = output(data['stream'])
        return Presentation(**data)
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise ValueError(f'Invalid presentation: {exc}') from exc
