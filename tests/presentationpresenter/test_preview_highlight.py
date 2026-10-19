"""Exact preview spans remain a visual layer, never editable content or sel."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from dataclasses import replace
from presentationpresenter.domain import TextSection, TextBlock, TextRun, BlockKind
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow
from presentationpresenter.session import ProjectionSession

class HighlightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.w = MainWindow(self.root, AppSettings(), recovery_dir=Path(self.temp.name)/'recovery')
        self.root.after_cancel(self.w.autosave_job)
        self.w.autosave_job = None
        self.errors = []
        self.root.report_callback_exception = lambda *e: self.errors.append(e)
        first = TextSection('Přísloví 2:16', (TextBlock((TextRun('Dlouhá odrážka. '*180),), BlockKind.BULLET),
                                            TextBlock((TextRun('Závěrečný odstavec.'),))), break_before=True, break_after=False)
        second = TextSection('Další úsek', (TextBlock((TextRun('Jiný obsah'),)),), break_after=False)
        self.w.selected_id = first.id
        self.w.commit(replace(self.w.document, sections=(first, second)))
        self.w.rebuild()
        self.root.update()
    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()
        self.assertFalse(self.errors)
    def highlighted(self):
        ranges = self.w.text.tag_ranges('preview_content')
        return ''.join(self.w.text.get(a, b) for a, b in zip(ranges[::2], ranges[1::2]))
    def expected(self):
        w = self.w
        runs = {r.id: r.text for s in w.plan.source.sections for b in s.blocks for r in b.runs}
        return ''.join(runs[s.run_id][s.start:s.end] for s in w.plan.slides[w.current].ranges)
    def test_exact_continuations_selection_and_black(self):
        w = self.w
        indices = [i for i, s in enumerate(w.plan.slides) if not s.black and s.section_id == w.selected_id]
        self.assertGreater(len(indices), 1)
        w.text.tag_add('sel', '1.2', '1.8')
        w.text.mark_set('insert', '1.8')
        original, history = w.document, len(w.history.past)
        for i in indices:
            w.jump(i)
            self.assertEqual(self.highlighted(), self.expected())
            self.assertEqual(tuple(map(str, w.text.tag_ranges('sel'))), ('1.2', '1.8'))
            self.assertEqual(w.text.index('insert'), '1.8')
        self.assertEqual(w.document, original)
        self.assertEqual(len(w.history.past), history)
        w.jump(0)
        self.assertEqual(self.highlighted(), '')
        last = len(w.plan.slides)-2
        w.jump(last)
        self.assertEqual(w.selected_id, w.plan.slides[last].section_id)
        self.assertEqual(self.highlighted(), self.expected())
    def test_edit_rebuild_and_live_mismatch(self):
        w = self.w
        i = next(i for i, s in enumerate(w.plan.slides) if not s.black)
        w.jump(i)
        self.assertTrue(self.highlighted())
        w.session = ProjectionSession.confirm(w.plan)
        w.view_version.set('live')
        w.text.insert('1.0', 'Nový text. ')
        w.finish_editing()
        self.assertEqual(self.highlighted(), '')
        w.rebuild()
        self.assertEqual(self.highlighted(), '')
        w.view_version.set('draft')
        w.rebuild()
        w.jump(next(i for i, s in enumerate(w.plan.slides) if not s.black))
        self.assertEqual(self.highlighted(), self.expected())
        self.assertTrue(self.highlighted().startswith('Nový text.'))
