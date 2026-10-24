"""Formatting spans preserves mixed styles, selection and source identities."""
import tkinter as tk
import unittest
from dataclasses import replace
from unittest.mock import patch

from presentationpresenter.domain import TextSection, TextBlock, TextRun, TextStyle
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow


class FormattingTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.w = MainWindow(self.root, AppSettings())
        self.root.after_cancel(self.w.autosave_job)
        self.w.autosave_job = None

    def tearDown(self):
        self.root.destroy()

    def test_partial_mixed_selection_preserves_other_styles_and_undo(self):
        w = self.w
        section = TextSection('Mixed', (TextBlock((
            TextRun('abc', TextStyle(color='#ff0000')),
            TextRun('def', TextStyle(italic=True)),
            TextRun('ghi', TextStyle(underline=True)),
        )),))
        w.commit(replace(w.document, sections=(section,)))
        w.selected_id = section.id
        w.load_editor()
        before = w.document
        w.text.tag_add('sel', '1.1', '1.8')
        w.format_selection('bold')
        self.assertEqual(tuple(map(str, w.text.tag_ranges('sel'))), ('1.1', '1.8'))
        runs = w.section().blocks[0].runs
        chars = [(c, r.style) for r in runs for c in r.text]
        self.assertEqual(''.join(c for c, _ in chars), 'abcdefghi')
        self.assertEqual([s.bold for _, s in chars], [False]+[True]*7+[False])
        self.assertTrue(all(s.italic for _, s in chars[3:6]))
        self.assertTrue(all(s.underline for _, s in chars[6:]))
        self.assertTrue(all(s.color == '#ff0000' for _, s in chars[:3]))
        after = w.document
        w.undo()
        self.assertEqual(w.document, before)
        w.redo()
        self.assertEqual(w.document, after)

    def test_uniform_long_selection_uses_one_style_operation(self):
        w = self.w
        section = TextSection('', (TextBlock((TextRun('Text '*2000),)),))
        w.commit(replace(w.document, sections=(section,)))
        w.selected_id = section.id
        w.load_editor()
        w.text.tag_add('sel', '1.0', 'end-1c')
        with patch.object(w.text, 'tag_add', wraps=w.text.tag_add) as add:
            w.format_selection('underline')
        style_calls = [c for c in add.call_args_list if c.args[0].startswith('style')]
        self.assertEqual(len(style_calls), 1)
        self.assertEqual(w.section().blocks[0].runs[0].id, section.blocks[0].runs[0].id)
        self.assertTrue(w.section().blocks[0].runs[0].style.underline)

    def test_preview_keeps_validation_message_until_corrected(self):
        w = self.w
        w.text.insert('1.0', 'Text')
        w.text_changed()
        w.font_size.set('999')
        w.apply_font_size()
        w.rebuild()
        self.assertIn('8 do 144', w.status.get())
        w.font_size.set('32')
        w.apply_font_size()
        w.rebuild()
        self.assertNotIn('8 do 144', w.status.get())


if __name__ == '__main__':
    unittest.main()
