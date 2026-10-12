"""Draft editing commands and immutable history, independent of projection."""
from dataclasses import replace
from .domain import Presentation, TextSection, TextBlock, TextRun, new_id


def duplicate_section(section, slide=None):
    """Copy source or only the exact source spans of one generated slide."""
    if slide is not None and (slide.black or slide.section_id != section.id):
        raise ValueError('Vyberte obsahový snímek tohoto úseku.')
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
    return replace(section, blocks=tuple(blocks), id=new_id(), origin=None)


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


def blank_document():
    return Presentation(black_start=False, black_end=True,
                        sections=(TextSection('', (TextBlock((TextRun(''),)),), break_after=False, break_before=True),))
