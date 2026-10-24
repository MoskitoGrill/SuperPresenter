import json
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from presentationpresenter.settings import AppSettings, FOLDER_LABELS, load_settings, save_settings
from presentationpresenter.folder_settings_window import FolderSettingsWindow
from presentationpresenter.ui import MainWindow

class FolderDefaultsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.values = {field: str(self.base/field) for field in FOLDER_LABELS}
        for path in self.values.values():
            Path(path).mkdir()
        self.root = tk.Tk()
        self.w = MainWindow(self.root, AppSettings(), recovery_dir=self.base/'recovery')
        self.root.after_cancel(self.w.autosave_job)
        self.w.autosave_job = None
        self.errors = []
        self.root.report_callback_exception = lambda *e: self.errors.append(e)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()
        self.assertFalse(self.errors)

    def test_roundtrip_legacy_invalid_and_unavailable_fallback(self):
        path = self.base/'preferences.json'
        settings = replace(AppSettings(), **self.values)
        save_settings(settings, path)
        self.assertEqual(load_settings(path), settings)
        path.write_text(json.dumps({'geometry': '1000x700'}), encoding='utf8')
        self.assertEqual(load_settings(path).import_directory, '')
        for invalid in (123, 'relative/path', 'bad\npath'):
            path.write_text(json.dumps({'open_directory': invalid}), encoding='utf8')
            self.assertEqual(load_settings(path), AppSettings())
        missing = str(self.base/'not-created')
        self.w.settings = replace(settings, open_directory=missing)
        with patch('presentationpresenter.ui.presentation_directory', return_value=self.base):
            self.assertEqual(self.w.file_dialog_directory(), self.base)
        self.assertFalse(Path(missing).exists())
        self.assertEqual(self.w.settings.open_directory, missing)

    def test_all_dialogs_use_their_purpose_and_save_keeps_existing_file(self):
        w = self.w
        w.settings = replace(w.settings, **self.values)
        with patch('presentationpresenter.ui.filedialog.askopenfilename', return_value='') as choose:
            for command, field in ((w.open_document, 'open_directory'), (w.import_document, 'import_directory'),
                                   (w.import_pptx, 'import_directory'), (w.choose_image, 'image_directory')):
                command()
                self.assertEqual(choose.call_args.kwargs['initialdir'], self.values[field])
        with patch('presentationpresenter.ui.filedialog.asksaveasfilename', return_value='') as choose:
            self.assertFalse(w.save_document(True))
            self.assertEqual(choose.call_args.kwargs['initialdir'], self.values['save_directory'])
        original = str(self.base/'existing.ppres')
        w.file_path = original
        with patch('presentationpresenter.ui.storage.save') as save, patch('presentationpresenter.ui.filedialog.asksaveasfilename') as choose:
            self.assertTrue(w.save_document())
            save.assert_called_once_with(original, w.document)
            choose.assert_not_called()

    def test_dialog_cancel_validation_failed_save_and_persistence(self):
        w = self.w
        original, document = w.settings, w.document
        dialog = FolderSettingsWindow(w)
        with patch('presentationpresenter.folder_settings_window.filedialog.askdirectory', return_value=''):
            dialog.browse('import_directory')
        self.assertEqual(dialog.values['import_directory'].get(), '')
        for field, value in self.values.items():
            dialog.values[field].set(value)
        dialog.values['open_directory'].set(str(self.base/'missing'))
        with patch('presentationpresenter.folder_settings_window.messagebox.showerror') as error:
            dialog.save()
            error.assert_called_once()
        self.assertEqual(w.settings, original)
        dialog.values['open_directory'].set(self.values['open_directory'])
        with patch('presentationpresenter.folder_settings_window.save_settings', side_effect=OSError('disk full')), \
             patch('presentationpresenter.folder_settings_window.messagebox.showerror'):
            dialog.save()
        self.assertEqual(w.settings, original)
        path = self.base/'preferences.json'
        with patch('presentationpresenter.folder_settings_window.save_settings', side_effect=lambda s: save_settings(s, path)):
            dialog.save()
        self.assertEqual(load_settings(path), w.settings)
        self.assertEqual(w.document, document)
        self.assertEqual(w.settings.import_directory, self.values['import_directory'])
        dialog = FolderSettingsWindow(w)
        dialog.values['open_directory'].set('')
        dialog.window.destroy()
        self.assertEqual(w.settings.open_directory, self.values['open_directory'])
