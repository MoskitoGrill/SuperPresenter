import json
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from presentationpresenter.settings import AppSettings, load_settings, save_settings
from presentationpresenter.ui import MainWindow
from presentationpresenter.domain import TextSection, TextBlock, TextRun


class ContentDefaultsTests(unittest.TestCase):
    def test_control_visibility_persists_and_survives_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'settings.json'
            root = tk.Tk()
            try:
                w = MainWindow(root, AppSettings(), recovery_dir=tmp)
                root.after_cancel(w.autosave_job)
                w.autosave_job = None
                root.update()
                original = w.document
                with patch('presentationpresenter.ui.save_settings', side_effect=lambda s: save_settings(s, path)) as save:
                    for field in w.visibility_vars:
                        w.visibility_buttons[field].invoke()
                    save.assert_not_called()
                    self.assertTrue(w.settings.show_projection_button)
                    w.visibility_save_button.invoke()
                    save.assert_called_once()
                w.update_version_status()
                w.projection_controls.update_summary()
                root.update()
                w.flush_workspace_resize()
                root.update()
                self.assertEqual(w.preview_navigation.winfo_height(), 8)
                self.assertFalse(w.editor_apply_row.winfo_ismapped())
                preview_bottom = w.preview.winfo_y()+w.preview.winfo_height()
                self.assertEqual(w.preview.master.winfo_height()-preview_bottom, 8)
                editor_bottom = w.editor_text_frame.winfo_y()+w.editor_text_frame.winfo_height()
                self.assertEqual(w.editor_text_frame.master.winfo_height()-editor_bottom, 8)
                w.unapplied_changes.set('Nepoužité změny')
                w.flush_workspace_resize()
                root.update()
                self.assertTrue(w.unapplied_label.winfo_ismapped())
                w.unapplied_changes.set('')
                w.flush_workspace_resize()
                root.update()
                self.assertFalse(w.projection_controls.play.winfo_ismapped())
                self.assertFalse(w.apply_button.winfo_ismapped())
                for button in w.navigation_layout.buttons:
                    self.assertFalse(button.winfo_ismapped())
                self.assertFalse(w.location_label.winfo_ismapped())
                self.assertTrue(w.header_location_label.winfo_ismapped())
                self.assertEqual(w.header_location_label.cget('textvariable'), w.location_label.cget('textvariable'))
                self.assertEqual(w.header_location_label.winfo_rooty(), w.preview_output_bar.winfo_rooty())
                self.assertEqual(w.header_location_label.winfo_rootx()+w.header_location_label.winfo_width(),
                    w.preview_output_bar.winfo_rootx()+w.preview_output_bar.winfo_width()-4)
                self.assertEqual(w.document, original)
                restored = load_settings(path)
                self.assertFalse(restored.show_projection_button)
                self.assertFalse(restored.show_apply_button)
                self.assertFalse(restored.show_navigation_buttons)
                root.destroy()
                root = tk.Tk()
                w = MainWindow(root, restored, recovery_dir=tmp)
                root.after_cancel(w.autosave_job)
                w.autosave_job = None
                root.update()
                self.assertFalse(w.apply_button.winfo_ismapped())
                self.assertFalse(w.projection_controls.play.winfo_ismapped())
                self.assertTrue(w.header_location_label.winfo_ismapped())
                with patch('presentationpresenter.ui.save_settings', side_effect=lambda s: save_settings(s, path)):
                    for field in w.visibility_vars:
                        w.visibility_buttons[field].invoke()
                root.update()
                self.assertTrue(w.apply_button.winfo_ismapped())
                self.assertTrue(w.projection_controls.play.winfo_ismapped())
                self.assertFalse(w.header_location_label.winfo_ismapped())
                self.assertTrue(w.location_label.winfo_ismapped())
                w.flush_workspace_resize()
                root.update()
                self.assertEqual(w.preview_navigation.winfo_height(), w.navigation_layout.normal_height)
                for button in w.navigation_layout.buttons:
                    self.assertTrue(button.winfo_ismapped())
                # Temporary changes must not leak through saving the font or closing.
                with patch('presentationpresenter.ui.save_settings', side_effect=lambda s: save_settings(s, path)):
                    w.save_content_defaults()
                    w.close()
                root = None
                restored = load_settings(path)
                self.assertFalse(restored.show_projection_button)
                self.assertFalse(restored.show_apply_button)
                self.assertFalse(restored.show_navigation_buttons)
            finally:
                if root is not None:
                    root.destroy()

    def test_settings_roundtrip_legacy_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'settings.json'
            settings = AppSettings(content_font_family='Arial', content_font_size=8)
            save_settings(settings, path)
            self.assertEqual(load_settings(path), settings)
            path.write_text(json.dumps({'geometry': '1000x700'}), encoding='utf-8')
            self.assertEqual(load_settings(path).content_font_size, 36)
            self.assertEqual(load_settings(path).content_font_family, 'Calibri')
            for bad in (True, 7, 145, '8'):
                path.write_text(json.dumps({'content_font_size': bad}), encoding='utf-8')
                self.assertEqual(load_settings(path), AppSettings())

    def test_save_new_content_restart_and_existing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'settings.json'
            root = tk.Tk()
            try:
                w = MainWindow(root, AppSettings(), recovery_dir=Path(tmp)/'recovery')
                root.after_cancel(w.autosave_job)
                w.autosave_job = None
                root.update()
                w.ribbon.show('Nastavení')
                root.update()
                self.assertTrue(w.default_save_button.winfo_viewable())
                original = w.document
                family = w.metrics.available_families.get('arial', next(iter(w.metrics.available_families.values())))
                w.default_family.set(family.lower())
                w.default_size.set('8')
                with patch('presentationpresenter.ui.save_settings', side_effect=lambda s: save_settings(s, path)):
                    w.default_save_button.invoke()
                self.assertEqual(w.document, original)
                self.assertIsNone(w.session)
                restored = load_settings(path)
                self.assertEqual((restored.content_font_family, restored.content_font_size), (family, 8))
                w.add_section()
                self.assertEqual(w.section().blocks[0].runs[0].style, w.default_content_style())
                w.insert_bible_section(TextSection('Bible', (TextBlock((TextRun('Text Bible'),)),)))
                self.assertEqual(w.section().blocks[0].runs[0].style.size, 8)
                self.assertEqual(w.section().blocks[0].runs[0].style.family, family)
                self.assertEqual(w.document.sections[0], original.sections[0])
                with patch('presentationpresenter.ui.messagebox.askyesnocancel', return_value=False):
                    w.new_document()
                self.assertEqual(w.section().blocks[0].runs[0].style.size, 8)
                root.destroy()
                root = tk.Tk()
                w = MainWindow(root, restored, recovery_dir=Path(tmp)/'restart')
                root.after_cancel(w.autosave_job)
                w.autosave_job = None
                self.assertEqual(w.section().blocks[0].runs[0].style.family, family)
                self.assertEqual(w.section().blocks[0].runs[0].style.size, 8)
            finally:
                root.destroy()

    def test_invalid_or_failed_save_keeps_previous_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tk.Tk()
            try:
                w = MainWindow(root, AppSettings(), recovery_dir=tmp)
                root.after_cancel(w.autosave_job)
                w.autosave_job = None
                previous = w.settings
                with patch('presentationpresenter.ui.save_settings') as save:
                    for size in ('7', '145', 'abc', '8.5'):
                        w.default_size.set(size)
                        w.save_content_defaults()
                    w.default_size.set('8')
                    w.default_family.set('not an installed font')
                    w.save_content_defaults()
                    save.assert_not_called()
                w.default_family.set(next(iter(w.metrics.available_families.values())))
                with patch('presentationpresenter.ui.save_settings', side_effect=OSError('test')), patch('presentationpresenter.ui.messagebox.showerror') as error:
                    w.save_content_defaults()
                    error.assert_called_once()
                self.assertEqual(w.settings, previous)
            finally:
                root.destroy()
