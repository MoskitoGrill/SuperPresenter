import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
import tkinter as tk
from presentationpresenter.profiles import defaults, load_profiles, save_profiles, ProjectionPreset, OutputPreset, MonitorName
from presentationpresenter.projection import Monitor
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow


class CatalogTests(unittest.TestCase):
    def test_roundtrip_validation_and_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'profiles.json'
            self.assertEqual(load_profiles(path), defaults())
            profiles = (*defaults(), ProjectionPreset('Vlastní / stream', OutputPreset(False), OutputPreset(True, 'missing', '4:3', False), (MonitorName('missing', 'Stream monitor'),)))
            save_profiles(profiles, path)
            self.assertEqual(load_profiles(path), profiles)
            with self.assertRaises(ValueError):
                OutputPreset(fullscreen='false')
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                save_profiles((*profiles, replace(profiles[0], name='jen STREAM')), path)
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaises(ValueError):
                ProjectionPreset('Bez výstupů', OutputPreset(False), OutputPreset(False))
            path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_profiles(path)


class ProfileUITests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.inventory = [Monitor('A', 0, 0, 800, 600), Monitor('B', -640, 0, 640, 480)]
        self.patches = [patch('presentationpresenter.ui.monitors', return_value=self.inventory),
                        patch('presentationpresenter.projection_controls.load_profiles', return_value=defaults())]
        for p in self.patches:
            p.start()
        self.w = MainWindow(self.root, AppSettings())
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        for p in reversed(self.patches):
            p.stop()

    def test_select_start_and_live_guard(self):
        c = self.w.projection_controls
        c.selected.set('Jen stream')
        c.choose()
        self.assertTrue(c.start())
        self.assertEqual(set(self.w.projections), {'stream'})
        session = self.w.session
        c.selected.set('Jen sál')
        c.choose()
        self.assertEqual(c.selected.get(), 'Jen stream')
        c.open_editor()
        self.assertIsNone(c.editor)
        self.assertEqual(self.w.session, session)
        self.w.stop_projection()
        c.selected.set('Sál + stream')
        c.choose()
        self.assertTrue(c.start())
        self.assertEqual(set(self.w.projections), {'hall', 'stream'})

    def test_editor_two_windowed_outputs_on_same_monitor(self):
        c = self.w.projection_controls
        c.open_editor()
        e = c.editor
        e.add_second('A')
        draft = e.draft()
        self.assertEqual(draft.hall.monitor, draft.stream.monitor)
        self.assertFalse(draft.hall.fullscreen)
        self.assertFalse(draft.stream.fullscreen)
        e.cards['A']['fullscreen'].set(True)
        self.assertFalse(e.apply())
        e.cards['A']['fullscreen'].set(False)
        with patch('presentationpresenter.monitor_editor.save_profiles') as writer:
            self.assertTrue(e.apply())
            writer.assert_not_called()
        self.assertTrue(c.start())
        self.assertEqual(set(self.w.projections), {'hall', 'stream'})
        for window in self.w.projections.values():
            self.assertFalse(window.fullscreen)
        self.w.stop_projection()
        c.open_editor()
        e = c.editor
        self.assertEqual(e.cards['A']['second_style'].get(), 'Stream')
        self.assertFalse(e.cards['A']['second_fullscreen'].get())
        self.assertFalse(e.cards['A']['fullscreen'].get())
        e.cancel()

    def test_compact_output_counter_display_style_and_plus(self):
        c = self.w.projection_controls
        self.assertEqual(c.counter.get(), '1 / 1')
        self.assertEqual(c.style_value.get(), 'Sál')
        c.style_value.set('Stream')
        c.change_style()
        self.assertEqual(c.outputs(), ['stream'])
        label = next(s for s, mid in c.display_ids.items() if mid == 'B')
        c.display_value.set(label)
        c.change_display()
        self.assertEqual(self.w.monitor_choices['stream'].get(), 'B')
        c.add_output()
        self.assertEqual(c.counter.get(), '1 / 2')
        self.assertEqual(c.style_value.get(), 'Sál')
        c.browse(1)
        self.assertEqual(c.counter.get(), '2 / 2')
        self.assertEqual(c.style_value.get(), 'Stream')
        self.assertEqual(c.display_value.get(), label)
        c.add_output()
        self.assertEqual(len(c.outputs()), 2)
        self.assertTrue(c.start())
        self.assertEqual(str(c.display['state']), 'disabled')
        c.browse(-1)
        self.assertEqual(c.counter.get(), '1 / 2')
        c.toggle_run()
        self.assertIsNone(self.w.session)
        self.assertEqual(str(c.display['state']), 'readonly')

    def test_editor_cancel_save_rename_apply_and_failure(self):
        c = self.w.projection_controls
        baseline = c.snapshot()
        c.open_editor()
        e = c.editor
        e.cards['A']['style'].set('Stream')
        e.name.set('Návrh')
        e.cancel()
        self.assertEqual(c.snapshot(), baseline)
        c.open_editor()
        e = c.editor
        e.new()
        e.name.set('Můj stream')
        e.cards['A']['style'].set('Nepoužívat')
        e.cards['B']['style'].set('Stream')
        with patch('presentationpresenter.monitor_editor.save_profiles', side_effect=OSError('disk')):
            self.assertFalse(e.save())
        self.assertEqual(c.snapshot(), baseline)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'profiles.json'
            with patch('presentationpresenter.monitor_editor.save_profiles', side_effect=lambda profiles: save_profiles(profiles, path)):
                self.assertTrue(e.save())
                self.assertEqual(c.snapshot(), baseline)
                self.assertEqual(load_profiles(path)[-1].name, 'Můj stream')
                before = path.read_bytes()
                e.cards['B']['name'].set('Obrazovka streamu')
                self.assertTrue(e.apply())
                self.assertEqual(path.read_bytes(), before)
        self.assertIsNone(c.editor)
        self.assertEqual(c.selected.get(), 'Můj stream')
        self.assertFalse(c.enabled['hall'])
        self.assertIn('Obrazovka streamu', c.display_value.get())

    def test_missing_monitor_and_conflict_require_explicit_choice(self):
        c = self.w.projection_controls
        preset = ProjectionPreset('Odpojený', OutputPreset(False), OutputPreset(True, 'missing', '16:9'))
        self.assertTrue(c.apply(preset))
        self.assertFalse(c.start())
        c.open_editor()
        e = c.editor
        self.assertEqual(e.cards['missing']['label'], 'Odpojený monitor')
        self.assertFalse(e.apply())
        e.cards['missing']['style'].set('Nepoužívat')
        e.cards['A']['style'].set('Stream')
        e.cards['B']['style'].set('Stream')
        self.assertFalse(e.apply())
        self.assertIn('nejvýše', e.status.get())
        e.cancel()

    def test_delete_transaction_and_duplicate_name(self):
        c = self.w.projection_controls
        c.open_editor()
        e = c.editor
        e.name.set('Jen STREAM')
        self.assertFalse(e.save())
        self.assertIn('již existuje', e.status.get())
        e.name.set('Sál + stream')
        with patch('presentationpresenter.monitor_editor.messagebox.askyesno', return_value=True):
            e.delete()
        self.assertEqual(len(e.profiles), 2)
        self.assertEqual(len(c.profiles), 3)
        e.cancel()
        self.assertEqual(len(c.profiles), 3)

    def test_load_saved_profile_and_monitor_topology_draft(self):
        c = self.w.projection_controls
        c.load_profile()
        loader = c.editor
        loader.selection.set('Jen stream')
        with patch('presentationpresenter.monitor_editor.save_profiles') as writer:
            self.assertTrue(loader.apply())
            writer.assert_not_called()
        self.assertEqual(c.outputs(), ['stream'])
        c.open_editor()
        e = c.editor
        self.assertEqual(set(e.cards), {'A', 'B'})
        e.cards['B']['name'].set('Sál vlevo')
        self.inventory.pop()
        self.w.refresh_monitors_now()
        self.assertEqual(e.cards['B']['name'].get(), 'Sál vlevo')
        self.assertFalse(e.apply())
        e.cards['B']['style'].set('Nepoužívat')
        e.cards['A']['style'].set('Stream')
        with patch('presentationpresenter.monitor_editor.save_profiles') as writer:
            self.assertTrue(e.apply())
            writer.assert_not_called()
        self.assertEqual(self.w.monitor_choices['stream'].get(), 'A')
        self.assertEqual(len(c.profiles), 3)
