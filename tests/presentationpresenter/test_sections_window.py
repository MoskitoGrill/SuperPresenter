from dataclasses import replace
from types import SimpleNamespace
import tempfile
import tkinter as tk
import unittest

from presentationpresenter.domain import TextSection, TextBlock, TextRun
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow
from presentationpresenter.session import ProjectionSession


class SectionsWindowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.editor = MainWindow(self.root, AppSettings(), recovery_dir=self.tmp.name)
        self.editor.commit(replace(self.editor.document, sections=tuple(
            TextSection(title, (TextBlock((TextRun('Obsah'),)),), reference=reference)
            for title, reference in [('První', 'Jiný odkaz'), ('', 'Jan 3:16 (CSP)'), ('Třetí', '')])))
        self.editor.rebuild()
        self.overview = self.editor.show_sections_window()
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()
        self.assertEqual(self.errors, [])

    def event(self, index, after=False):
        box = self.overview.listbox.bbox(index)
        return SimpleNamespace(x=20, y=box[1] + box[3] - 1 if after else box[1] + 1)

    def test_drag_undo_and_live_isolation(self):
        editor, overview = self.editor, self.overview
        editor.session = ProjectionSession.confirm(editor.plan)
        live = editor.session.plan
        original = editor.document
        overview.press(self.event(0))
        overview.motion(self.event(2, True))
        self.assertEqual(editor.document, original)
        overview.release(self.event(2, True))
        self.assertEqual([s.title for s in editor.document.sections], ['', 'Třetí', 'První'])
        self.assertEqual(editor.selected_id, original.sections[0].id)
        self.assertIs(editor.session.plan, live)
        editor.undo()
        self.assertEqual(editor.document, original)
        editor.redo()
        self.assertEqual(overview.ids[-1], original.sections[0].id)
        # Existing movement still updates the open overview.
        editor.move_section(-1)
        self.assertEqual(overview.ids[1], original.sections[0].id)

    def test_labels_selection_cancel_and_lifecycle(self):
        overview, editor = self.overview, self.editor
        self.assertEqual(overview.listbox.get(0), '1. První')
        self.assertEqual(overview.listbox.get(1), '2. Jan 3:16 (CSP)')
        self.assertIs(editor.show_sections_window(), overview)
        overview.press(self.event(1))
        overview.release(self.event(1))
        self.assertEqual(editor.selected_id, editor.document.sections[1].id)
        original = editor.document
        overview.press(self.event(0))
        overview.motion(self.event(2, True))
        overview.cancel()
        overview.release(self.event(2, True))
        self.assertEqual(editor.document, original)
        overview.close()
        self.assertFalse(overview.alive())
        self.assertIsNot(editor.show_sections_window(), overview)

    def test_stale_drag_and_empty_list(self):
        overview, editor = self.overview, self.editor
        overview.press(self.event(0))
        overview.motion(self.event(2, True))
        editor.add_section()
        original = editor.document
        overview.release(SimpleNamespace(x=20, y=30))
        self.assertEqual(editor.document, original)
        editor.commit(replace(editor.document, sections=()))
        overview.press(SimpleNamespace(x=20, y=30))
        overview.release(SimpleNamespace(x=20, y=30))
        self.assertEqual(overview.ids, ())

    def test_autoscroll_and_close_cancels_timer(self):
        editor, overview = self.editor, self.overview
        editor.commit(replace(editor.document, sections=tuple(
            TextSection(str(i), ()) for i in range(45))))
        self.root.update()
        overview.press(self.event(0))
        overview.motion(SimpleNamespace(x=20, y=overview.listbox.winfo_height()-2))
        self.assertIsNotNone(overview.timer)
        self.assertGreater(overview.listbox.yview()[0], 0)
        overview.close()
        self.root.update()
        self.assertIsNone(overview.timer)


if __name__ == '__main__':
    unittest.main()
