"""Cached plans must match a fresh layout after every source/output change."""
import io
import json
import tkinter as tk
import unittest
from dataclasses import replace
from unittest.mock import patch
from PIL import Image

from presentationpresenter import layout, media, storage, persistence
from presentationpresenter.domain import *
from presentationpresenter.rendering import TkMetrics


class IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.metrics = TkMetrics(self.root)
        self.fresh = TkMetrics(self.root)

    def tearDown(self):
        self.metrics.clear()
        self.fresh.clear()
        self.root.destroy()

    def document(self):
        return Presentation(sections=tuple(TextSection(str(i), (
            TextBlock((TextRun('Slova pro dělení. '*12),)),)) for i in range(6)))

    def verify(self, document):
        self.fresh.clear()
        self.assertEqual(layout.paginate(document, self.metrics), layout.paginate(document, self.fresh))

    def test_only_changed_section_is_recomputed(self):
        doc = self.document()
        layout.paginate(doc, self.metrics)
        changed = replace(doc, sections=(replace(doc.sections[0], title='Nový název'),)+doc.sections[1:])
        with patch('presentationpresenter.layout._paginate_content', wraps=layout._paginate_content) as compute:
            plan = layout.paginate(changed, self.metrics)
        self.assertEqual(compute.call_count, 1)
        self.verify(changed)
        with patch('presentationpresenter.layout._flow', side_effect=AssertionError('Unchanged layout')):
            self.assertEqual(layout.paginate(changed, self.metrics), plan)

    def test_aspects_camera_reorder_breaks_and_undo_match_fresh_layout(self):
        doc = self.document()
        self.verify(doc)
        for hall in Aspect:
            for stream in Aspect:
                self.verify(replace(doc, hall=replace(doc.hall, aspect=hall),
                                    stream=replace(doc.stream, aspect=stream)))
        self.verify(replace(doc, stream=replace(doc.stream, camera=None)))
        self.verify(replace(doc, sections=doc.sections[::-1], black_start=False, black_end=True))
        self.verify(replace(doc, sections=doc.sections[1:]))
        self.verify(doc)
        section = doc.sections[0]
        block = section.blocks[0]
        run = block.runs[0]
        edited = replace(section, blocks=(replace(block, runs=(replace(run,
            text=run.text*3, style=replace(run.style, bold=True, size=48)),)),))
        self.verify(replace(doc, sections=(edited,)+doc.sections[1:]))
        self.verify(doc)
        self.verify(doc)
        self.fresh.clear()
        self.assertEqual(layout.paginate(doc, self.metrics, layout.Typography(margin=48)),
                         layout.paginate(doc, self.fresh, layout.Typography(margin=48)))

    def test_media_change_invalidates_layout_and_validation_cache_is_safe(self):
        def asset(color):
            stream = io.BytesIO()
            Image.new('RGB', (30, 20), color).save(stream, format='PNG')
            return media.from_bytes(stream.getvalue())
        first, second = asset('red'), asset('blue')
        doc = Presentation(sections=(ImageSection('', first.id),), media=(first,))
        self.verify(doc)
        self.verify(replace(doc, media=(replace(second, id=first.id),)))
        storage._validated_media.clear()
        with patch('presentationpresenter.storage.decode', wraps=media.decode) as decode:
            storage.encode(doc)
            storage.encode(doc)
            self.assertEqual(decode.call_count, 1)
        self.assertEqual(json.loads(storage.encode(doc))['document'], json.loads(persistence.dumps(doc)))
        damaged = replace(doc, media=(replace(first, locator='data:image/png;base64,broken'),))
        for _ in range(2):
            with self.assertRaises(ValueError):
                storage.validate(damaged)


if __name__ == '__main__':
    unittest.main()
