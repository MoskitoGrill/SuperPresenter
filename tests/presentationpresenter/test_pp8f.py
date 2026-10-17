"""Approved PP8F safeguards and real Tk keyboard events, with isolated files."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch

from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings
from presentationpresenter.domain import TextSection, TextBlock, TextRun
from presentationpresenter.session import ProjectionSession
from presentationpresenter import storage


class FinalizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.w = MainWindow(self.root, AppSettings(), recovery_dir=Path(self.temp.name)/'recovery')
        self.root.after_cancel(self.w.autosave_job)
        self.w.autosave_job = None
        self.root.update()
        self.errors = []
        self.root.report_callback_exception = lambda *error: self.errors.append(error)

    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()
        self.assertFalse(self.errors)

    def key(self, widget, sequence):
        widget.focus_force()
        self.root.update()
        widget.event_generate(sequence)
        self.root.update()

    def type_text(self, value):
        self.w.text.insert('end', value)
        self.w.finish_editing()

    def test_cancel_and_failed_save_block_all_replacements(self):
        w = self.w
        self.type_text('Rozpracováno')
        original = w.document
        for action in (w.new_document, w.open_document, w.import_document):
            with self.subTest(action=action.__name__):
                with patch('presentationpresenter.ui.messagebox.askyesnocancel', return_value=None), \
                     patch('presentationpresenter.ui.filedialog.askopenfilename') as choose:
                    action()
                    choose.assert_not_called()
                self.assertEqual(w.document, original)
                with patch('presentationpresenter.ui.messagebox.askyesnocancel', return_value=True), \
                     patch('presentationpresenter.ui.filedialog.asksaveasfilename', return_value=''):
                    action()
                self.assertEqual(w.document, original)
        path = Path(self.temp.name)/'failed.ppres'
        with patch('presentationpresenter.ui.messagebox.askyesnocancel', return_value=True), \
             patch('presentationpresenter.ui.filedialog.asksaveasfilename', return_value=str(path)), \
             patch('presentationpresenter.ui.storage.save', side_effect=OSError('disk full')), \
             patch('presentationpresenter.ui.messagebox.showerror'):
            w.open_document()
        self.assertEqual(w.document, original)
        self.assertIsNone(w.file_path)

    def test_open_save_and_undo_restore_file_identity(self):
        w = self.w
        self.type_text('Soubor A')
        a = Path(self.temp.name)/'A.ppres'
        b = Path(self.temp.name)/'B.ppres'
        with patch('presentationpresenter.ui.filedialog.asksaveasfilename', return_value=str(a)):
            w.save_document()
        saved_a = w.document
        self.type_text(' poslední znak')
        edited_a = w.document
        # Save-as copies can share the document ID but need separate file contexts.
        other = replace(w.document, title='B')
        storage.save(b, other)
        with patch('presentationpresenter.ui.messagebox.askyesnocancel', return_value=True), \
             patch('presentationpresenter.ui.filedialog.askopenfilename', return_value=str(b)):
            w.open_document()
        self.assertEqual(storage.load(a), edited_a)
        self.assertIn('B.ppres • uloženo', w.file_status.get())
        w.undo()
        self.assertEqual(w.document, edited_a)
        self.assertEqual(w.file_path, str(a))
        self.assertEqual(w.saved_document, edited_a)
        w.undo()
        self.assertEqual(w.document, saved_a)
        self.assertIn('neuložené změny', w.file_status.get())
        w.redo()
        w.redo()
        self.assertEqual(w.file_path, str(b))

    def test_format_keys_preserve_text_selection_and_are_undoable(self):
        w = self.w
        self.type_text('Výběr textu')
        w.text.tag_add('sel', '1.0', '1.5')
        for key, field in (('b', 'bold'), ('i', 'italic'), ('u', 'underline')):
            self.key(w.text, '<Control-'+key+'>')
            self.assertTrue(getattr(w.document.sections[0].blocks[0].runs[0].style, field))
            self.assertEqual(w.text.get('1.0', 'end-1c'), 'Výběr textu')
            self.assertTrue(w.text.tag_ranges('sel'))
        self.key(w.text, '<Control-z>')
        self.assertFalse(w.document.sections[0].blocks[0].runs[0].style.underline)
        self.assertTrue(w.document.sections[0].blocks[0].runs[0].style.italic)
        w.text.tag_remove('sel', '1.0', 'end')
        w.text.mark_set('insert', 'end-1c')
        self.key(w.text, '<KeyPress-b>')
        self.assertTrue(w.text.get('1.0', 'end-1c').endswith('b'))

    def test_new_section_and_slide_copy_do_not_insert_control_characters(self):
        w = self.w
        self.type_text('dlouhý text ' * 450)
        w.rebuild()
        source = w.document.sections[0]
        contents = [i for i, s in enumerate(w.plan.slides) if not s.black]
        self.assertGreater(len(contents), 1)
        w.jump(contents[1], select=True)
        self.key(w.text, '<Control-Shift-D>')
        self.assertEqual(len(w.document.sections), 2)
        copied = w.document.sections[1]
        self.assertNotEqual(copied.id, source.id)
        self.assertLess(sum(len(r.text) for b in copied.blocks for r in b.runs),
                        sum(len(r.text) for b in source.blocks for r in b.runs))
        self.key(w.title_entry, '<Control-m>')
        self.assertEqual(len(w.document.sections), 3)
        self.assertEqual(w.document.sections[-1].blocks[0].runs[0].text, '')
        self.assertEqual(self.root.focus_get(), w.title_entry)
        # Copying a black slide remains a no-op.
        w.rebuild()
        w.jump(0)
        self.key(w.preview, '<Control-Shift-D>')
        self.assertEqual(len(w.document.sections), 3)

    def test_list_operations_keep_focus_and_do_not_publish(self):
        w = self.w
        self.type_text('První')
        w.add_section(TextSection(title='Druhý', blocks=(TextBlock(runs=(TextRun('Druhý'),)),)))
        w.rebuild()
        w.session = ProjectionSession.confirm(w.draft_plan)
        session = w.session
        self.key(w.preview, '<Control-b>')
        self.assertFalse(w.session.blackout)
        self.key(w.preview, '<KeyPress-b>')
        self.assertTrue(w.session.blackout)
        self.key(w.preview, '<KeyPress-b>')
        self.assertFalse(w.session.blackout)
        session = w.session
        w.ribbon.show('Úseky')
        self.key(w.sections, '<Control-d>')
        self.assertEqual(len(w.document.sections), 3)
        selected = w.selected_id
        self.assertEqual(w.document.sections[-1].id, selected)
        self.assertEqual(self.root.focus_get(), w.sections)
        self.key(w.sections, '<Alt-Up>')
        self.assertEqual(w.document.sections[1].id, selected)
        self.key(w.sections, '<Alt-Down>')
        self.assertEqual(w.document.sections[2].id, selected)
        self.key(w.sections, '<Alt-Down>')
        self.assertEqual(w.document.sections[2].id, selected)
        self.assertIs(w.session, session)
        self.key(w.text, '<Control-Return>')
        self.assertEqual(w.session.plan.source, w.document)
        self.assertNotIn('\n', w.text.get('1.0', 'end-1c'))

    def test_file_shortcuts_and_dialog_scope(self):
        w = self.w
        path = Path(self.temp.name)/'shortcut.ppres'
        w.text.insert('end', 'Poslední znak')  # No Modified event loop before save.
        with patch('presentationpresenter.ui.filedialog.asksaveasfilename', return_value=str(path)):
            self.key(w.text, '<Control-Shift-S>')
        self.assertEqual(storage.load(path).sections[0].blocks[0].runs[0].text, 'Poslední znak')
        self.assertIn('uloženo', w.file_status.get())
        dialog = tk.Toplevel(self.root)
        entry = tk.Entry(dialog)
        entry.pack()
        before = w.document
        self.key(entry, '<Control-m>')
        self.key(entry, '<Control-Shift-D>')
        self.assertEqual(w.document, before)
        dialog.destroy()
        with patch('presentationpresenter.ui.messagebox.askyesno', return_value=True):
            self.key(w.text, '<Control-n>')
        self.assertIsNone(w.file_path)
        self.assertIn('dosud neuloženo', w.file_status.get())

    def test_import_discard_is_unsaved_and_preserves_live_and_original(self):
        w = self.w
        self.type_text('Původní obsah')
        w.rebuild()
        w.session = ProjectionSession.confirm(w.draft_plan)
        live = w.session
        before = w.document
        source = Path(self.temp.name)/'legacy.json'
        original = '[{"link": "Import", "text": "Nový obsah"}]'
        source.write_text(original, encoding='utf-8')
        with patch('presentationpresenter.ui.messagebox.askyesnocancel', return_value=False), \
             patch('presentationpresenter.ui.filedialog.askopenfilename', return_value=str(source)), \
             patch('presentationpresenter.ui.messagebox.showwarning'):
            w.import_document()
        self.assertIsNone(w.file_path)
        self.assertNotEqual(w.document, w.saved_document)
        self.assertIn('dosud neuloženo', w.file_status.get())
        self.assertEqual(source.read_text(encoding='utf-8'), original)
        self.assertIs(w.session, live)
        w.undo()
        self.assertEqual(w.document, before)
        self.assertIs(w.session, live)

    def test_publish_shortcut_rejects_invalid_layout_and_dialog_cannot_publish(self):
        w = self.w
        self.type_text('Živý text')
        w.rebuild()
        w.session = ProjectionSession.confirm(w.draft_plan)
        live = w.session
        w.title.set('W' * 10000)
        self.key(w.title_entry, '<Control-Return>')
        self.assertIs(w.session, live)
        self.assertIn('nebyly použity', w.status.get())
        w.undo()
        self.type_text(' oprava')
        dialog = tk.Toplevel(self.root)
        entry = tk.Entry(dialog)
        entry.pack()
        self.key(entry, '<Control-Return>')
        self.assertIs(w.session, live)
        dialog.destroy()
        self.key(w.text, '<Control-Return>')
        self.assertEqual(w.session.plan.source, w.document)


if __name__ == '__main__':
    unittest.main()
