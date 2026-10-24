import unittest
import tkinter as tk
from dataclasses import replace
from unittest.mock import patch
from presentationpresenter.domain import *
from presentationpresenter.editor import History, duplicate_section, blank_document
from presentationpresenter.layout import paginate
from presentationpresenter.rendering import TkMetrics
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow
from presentationpresenter.session import ProjectionSession


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.window = MainWindow(self.root, AppSettings())
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def enter(self, text):
        self.window.text.insert('1.0', text)
        self.root.update()
        self.window.rebuild()

    def test_typing_formatting_focus_and_history(self):
        w = self.window
        sid, bid, rid = w.section().id, w.section().blocks[0].id, w.section().blocks[0].runs[0].id
        w.title.set('Žalm 23')
        self.enter('Hospodin je můj pastýř.\nNic mi neschází.')
        self.assertEqual(w.section().id, sid)
        self.assertEqual(w.section().blocks[0].id, bid)
        self.assertEqual(w.section().blocks[0].runs[0].id, rid)
        self.assertEqual(len(w.section().blocks), 2)
        w.text.tag_add('sel', '1.0', '1.8')
        for field in ('bold', 'italic', 'underline'):
            w.format_selection(field)
        w.format_selection('color', '#ffcc00')
        style = w.section().blocks[0].runs[0].style
        self.assertEqual(style, TextStyle(True, True, True, '#ffcc00'))
        formatted = w.document
        w.undo()
        self.assertEqual(w.section().blocks[0].runs[0].style.color, '#ffffff')
        w.redo()
        self.assertEqual(w.document, formatted)
        w.text.tag_remove('sel', '1.0', 'end')
        w.text.mark_set('insert', '2.0')
        w.toggle_bullets()
        self.assertEqual(w.section().blocks[1].kind, BlockKind.BULLET)
        w.undo()
        self.assertEqual(w.section().blocks[1].kind, BlockKind.PARAGRAPH)

    def test_section_commands_and_complete_undo_redo(self):
        w = self.window
        initial = w.document
        self.enter('První obsah')
        original = w.document
        w.add_section()
        w.title.set('Druhý')
        self.enter('Další obsah')
        w.break_before.set(False)
        w.change_break()
        second = w.section()
        w.copy_section()
        self.assertEqual(len(w.document.sections), 3)
        self.assertFalse(w.section().break_after)
        self.assertFalse(w.section().break_before)
        self.assertNotEqual(w.section().id, second.id)
        self.assertNotEqual(w.section().blocks[0].runs[0].id, second.blocks[0].runs[0].id)
        before_move = w.document
        w.move_section(-1)
        moved = w.document
        w.undo()
        self.assertEqual(w.document, before_move)
        w.redo()
        self.assertEqual(w.document, moved)
        w.delete_section()
        deleted = w.document
        w.undo()
        self.assertEqual(w.document, moved)
        w.redo()
        self.assertEqual(w.document, deleted)
        while w.history.past:
            w.undo()
        self.assertEqual(w.document, initial)
        while w.history.future:
            w.redo()
        self.assertEqual(w.document, deleted)

    def test_exact_continuation_copy_and_thumbnail_navigation_cache(self):
        w = self.window
        self.enter('Dlouhá odrážka '+('český text '*250))
        w.text.mark_set('insert', '1.0')
        w.toggle_bullets()
        w.rebuild()
        session = ProjectionSession.confirm(w.plan)
        indices = [i for i, s in enumerate(w.plan.slides) if not s.black]
        self.assertGreater(len(indices), 1)
        widgets = tuple(w.thumbnails)
        items = [c.find_all() for c in widgets]
        with patch('presentationpresenter.ui.paginate', side_effect=AssertionError('Navigation must not paginate')):
            w.jump(indices[1], select=True)
            w.output.set('stream')
            w.render_preview()
        self.assertEqual(tuple(w.thumbnails), widgets)
        self.assertEqual([c.find_all() for c in widgets], items)
        slide = w.plan.slides[indices[1]]
        section = w.section()
        expected = ''.join(r.text[span.start:span.end] for span in slide.ranges for b in section.blocks for r in b.runs if r.id == span.run_id)
        w.copy_slide()
        self.assertEqual(''.join(r.text for b in w.section().blocks for r in b.runs), expected)
        self.assertEqual(w.section().blocks[0].kind, BlockKind.BULLET)
        self.assertNotEqual(w.section().id, section.id)
        self.assertEqual(session.plan.source.sections, (section,))
        duplicate = w.document
        w.undo()
        self.assertEqual(len(w.document.sections), 1)
        w.redo()
        self.assertEqual(w.document, duplicate)

    def test_stable_ids_and_embedded_newlines(self):
        w = self.window
        section = TextSection('Importovaný', (TextBlock((TextRun('První\nřádek'), TextRun(' barevně', TextStyle(color='#ff0000')))), TextBlock((TextRun('Další'),), BlockKind.BULLET)))
        w.selected_id = section.id
        w.commit(replace(w.document, sections=(section,)))
        self.assertEqual(w.read_blocks(), section.blocks)
        w.text.insert('1.2', 'X')
        self.root.update()
        edited = w.section()
        self.assertEqual([b.id for b in edited.blocks], [b.id for b in section.blocks])
        self.assertEqual([r.id for b in edited.blocks for r in b.runs], [r.id for b in section.blocks for r in b.runs])
        w.text.mark_set('insert', '2.2')
        w.insert_newline()
        self.root.update()
        self.assertEqual(len(w.section().blocks), 3)
        Presentation(sections=(w.section(),))

    def test_empty_delete_new_and_layout_error_recovery(self):
        w = self.window
        w.delete_section()
        w.black_start.set(False)
        w.commit(replace(w.document, black_start=False))
        w.rebuild()
        self.assertEqual(w.plan.slides, ())
        w.add_section()
        w.title.set('W'*10000)
        w.rebuild()
        self.assertIn('není aktuální', w.status.get())
        w.undo()
        self.assertEqual(w.plan.source, w.document)
        with patch('presentationpresenter.ui.messagebox.askyesno', return_value=True), patch('presentationpresenter.ui.messagebox.askyesnocancel', return_value=False):
            before = w.document
            w.new_document()
        w.undo()
        self.assertEqual(w.document, before)

    def test_paste_paragraphs_delete_and_identity(self):
        w = self.window
        self.enter('První\nDruhý\nTřetí')
        before = w.section()
        w.text.delete('1.0', '2.0')
        self.root.update()
        self.assertEqual(w.section().blocks[0].id, before.blocks[1].id)
        self.assertEqual(w.section().blocks[1].id, before.blocks[2].id)
        w.text.mark_set('insert', 'end-1c')
        with patch.object(self.root, 'clipboard_get', return_value='\r\nNový\r\nOdstavec'):
            w.paste_text()
        self.root.update()
        self.assertEqual(len(w.section().blocks), 4)
        source = w.document
        w.undo()
        w.redo()
        self.assertEqual(w.document, source)

    def test_trailing_source_newline_and_empty_block_roundtrip(self):
        w = self.window
        section = TextSection('Okraje bloků', (TextBlock((TextRun('Konec\n'),)), TextBlock(()), TextBlock((TextRun('Další'),))))
        w.selected_id = section.id
        w.commit(replace(w.document, sections=(section,)))
        self.assertEqual(w.read_blocks(), section.blocks)


class HistoryTests(unittest.TestCase):
    def test_coalescing_and_redo_branch(self):
        initial = blank_document()
        history = History(initial)
        one, two = replace(initial, title='a'), replace(initial, title='ab')
        history.apply(one, 'typing')
        history.apply(two, 'typing')
        self.assertEqual(len(history.past), 1)
        self.assertEqual(history.undo(), initial)
        self.assertEqual(history.redo(), two)
        history.undo()
        history.apply(replace(initial, title='new'))
        self.assertFalse(history.future)


if __name__ == '__main__':
    unittest.main()
