"""Draft editing commands and immutable history, independent of projection."""
from dataclasses import replace
from .domain import Presentation, TextSection, ImageSection, ImageItem, TextBlock, TextRun, TextStyle, DEFAULT_CONTENT_FONT, new_id


def duplicate_section(section, slide=None):
    """Copy source or only the exact source spans of one generated slide."""
    if slide is not None and (slide.black or slide.section_id != section.id):
        raise ValueError('Vyberte obsahový snímek tohoto úseku.')
    if isinstance(section, ImageSection):
        return replace(section, id=new_id(), origin=None)
    blocks = []
    for block in section.blocks:
        if slide is not None and block.id not in slide.block_ids:
            continue
        runs = []
        for run in block.runs:
            text = run.text if slide is None else ''.join(
                run.text[r.start:r.end] for r in slide.ranges if r.run_id == run.id)
            if text or slide is None:
                runs.append(replace(run, text=text, id=new_id()))
        blocks.append(replace(block, runs=tuple(runs), id=new_id()))
    images = section.images
    if slide is not None and images and slide.hall is not None:
        visible = {image.item_id for image in slide.hall.images}
        images = tuple(i for i in images if i.id in visible)
    return replace(section, blocks=tuple(blocks), images=tuple(replace(i, id=new_id()) for i in images), id=new_id(), origin=None)


def editable_section(section):
    """Legacy single-image section becomes editable mixed content without new ID."""
    if isinstance(section, ImageSection):
        return TextSection(section.title, (TextBlock((TextRun(''),)),), reference=section.reference,
                           break_after=section.break_after, break_before=section.break_before,
                           origin=section.origin, id=section.id, images=(ImageItem(section.media_id, alt_text=section.alt_text),))
    return section


def merge_sections(first, second):
    """Explicit merge: keep first identity/header and outer boundaries."""
    first, second = editable_section(first), editable_section(second)
    images = first.images + second.images
    if len(images) > 64:
        raise ValueError('Sloučený úsek by obsahoval více než 64 obrázků.')
    # Reset placement: a new composition must use the automatic grid.
    images = tuple(replace(i, hall=None, stream=None) for i in images)
    return replace(first, blocks=first.blocks + second.blocks, images=images,
                   break_after=second.break_after, stream_linked=True, origin=None)


class History:
    def __init__(self, document):
        self.document = document
        self.past, self.future = [], []
        self.group = None

    def apply(self, document, group=None):
        if document == self.document:
            return False
        if group is None or group != self.group:
            self.past.append(self.document)
        self.document = document
        self.future.clear()
        self.group = group
        return True

    def undo(self):
        self.group = None
        if self.past:
            self.future.append(self.document)
            self.document = self.past.pop()
        return self.document

    def redo(self):
        self.group = None
        if self.future:
            self.past.append(self.document)
            self.document = self.future.pop()
        return self.document


def blank_document(style=None):
    return Presentation(black_start=False, black_end=True,
                        sections=(TextSection('', (TextBlock((TextRun('', style or TextStyle(family=DEFAULT_CONTENT_FONT)),)),), break_after=False, break_before=True),))
