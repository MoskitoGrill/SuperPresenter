import json
import tkinter as tk
import unittest
from dataclasses import replace
from types import SimpleNamespace
from presentationpresenter.domain import *
from presentationpresenter.editor import blank_document
from presentationpresenter.persistence import dumps, loads
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow


class BeforeBreakTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.window = MainWindow(self.root, AppSettings())
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_break_follows_its_section_and_terminal_black(self):
        w = self.window
        first = w.section()
        w.add_section()
        second = w.section()
        w.break_before.set(False)
        w.change_break()
        w.rebuild()
        self.assertEqual([s.id for s in w.plan.slides if s.black], [first.id+':before', w.document.id+':end'])
        w.move_section(-1)
        w.rebuild()
        self.assertEqual(w.plan.slides[0].section_id, second.id)
        self.assertFalse(w.plan.slides[0].black)
        self.assertEqual(w.plan.slides[1].id, first.id+':before')
        w.undo()
        self.assertEqual(w.document.sections[0].id, first.id)
        w.redo()
        self.assertEqual(w.document.sections[0].id, second.id)

    def test_delete_before_final_and_undo_redo(self):
        w = self.window
        original = w.document
        w.thumbnail_clicked(0)
        w.delete_black_slide(SimpleNamespace(widget=w.thumbnails[0]))
        self.assertFalse(w.section().break_before)
        self.assertFalse(w.plan.slides[0].black)
        self.assertTrue(w.plan.slides[-1].black)
        deleted = w.document
        w.undo()
        self.assertEqual(w.document, original)
        w.redo()
        self.assertEqual(w.document, deleted)
        w.thumbnail_clicked(len(w.plan.slides)-1)
        w.delete_black_slide(SimpleNamespace(widget=w.thumbnails[-1]))
        self.assertFalse(w.document.black_end)
        self.assertFalse(any(s.black for s in w.plan.slides))
        w.undo()
        self.assertTrue(w.document.black_end)

    def test_delete_in_text_entry_or_on_content_does_not_remove_slide(self):
        w = self.window
        original = w.document
        w.jump(0)
        for widget in (w.text, w.title_entry, w.sections):
            w.delete_black_slide(SimpleNamespace(widget=widget))
            self.assertEqual(w.document, original)
        w.jump(1)
        w.delete_black_slide(SimpleNamespace(widget=w.thumbnails[1]))
        self.assertEqual(w.document, original)

    def test_collapsed_black_removes_all_contributors(self):
        w = self.window
        w.commit(replace(w.document, black_start=True))
        w.rebuild()
        w.jump(0)
        w.delete_black_slide(SimpleNamespace(widget=w.preview))
        self.assertFalse(w.document.black_start)
        self.assertFalse(w.section().break_before)
        self.assertFalse(w.plan.slides[0].black)

    def test_codec_optional_flags_and_old_v1_compatibility(self):
        source = blank_document()
        self.assertEqual(loads(dumps(source)), source)
        data = json.loads(dumps(source))
        del data['black_end']
        del data['sections'][0]['break_before']
        old = loads(json.dumps(data))
        self.assertFalse(old.black_end)
        self.assertFalse(old.sections[0].break_before)
        with self.assertRaises(ValueError):
            replace(source, black_end='yes')
        with self.assertRaises(ValueError):
            replace(source, sections=(replace(source.sections[0], break_before='yes'),))


if __name__ == '__main__':
    unittest.main()
