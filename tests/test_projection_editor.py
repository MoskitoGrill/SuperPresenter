"""Monitor editor model and transactional controller regression tests."""
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from superpresenter.services.projection_config import (
    ConfigError, load_styles, load_layout, monitor_identity, monitor_labels,
    save_layout, validate_layout,
)
from superpresenter.services.projection_editor_model import editor_cards, layout_from_cards

ROOT = Path(__file__).resolve().parents[1]


class ProjectionEditorModelTests(unittest.TestCase):
    def setUp(self):
        self.styles = load_styles(ROOT / 'projectors_styles.json')['styles']
        self.monitors = [SimpleNamespace(name='primary', x=0, y=0, width=1920, height=1080, is_primary=True),
                         SimpleNamespace(name='external', x=1920, y=0, width=1920, height=1080, is_primary=False)]
        self.output = dict(style=self.styles[0]['name'], monitor=monitor_identity(self.monitors[1]),
                           fullscreen=True, collection=True, window_position=None)
        self.old = dict(version=1, outputs=[self.output])

    def test_legacy_layout_becomes_independent_draft(self):
        cards = editor_cards(self.old, self.monitors)
        self.assertIsNone(cards[0]['outputs'][0]['style'])
        self.assertEqual(cards[1]['outputs'], [self.output])
        cards[1]['outputs'][0]['fullscreen'] = False
        self.assertTrue(self.output['fullscreen'])
        upgraded = layout_from_cards(cards, self.monitors, self.styles)
        self.assertEqual(upgraded['version'], 2)
        self.assertFalse(upgraded['outputs'][0]['fullscreen'])

    def test_names_include_disabled_monitors_and_survive_file_roundtrip(self):
        cards = editor_cards(self.old, self.monitors)
        cards[0]['label'] = ' Obsluha '
        cards[1]['label'] = 'Sál'
        data = layout_from_cards(cards, self.monitors, self.styles)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'named.json'
            save_layout(path, data, self.styles)
            restored = load_layout(path, self.styles)
        self.assertEqual(monitor_labels(self.monitors, restored['monitor_names']),
                         ['Obsluha (0, 0)', 'Sál (1920, 0)'])
        self.assertEqual(self.monitors[1].name, 'external')

    def test_all_disabled_is_valid_only_in_version_two(self):
        cards = editor_cards(self.old, self.monitors)
        cards[1]['outputs'][0]['style'] = None
        data = layout_from_cards(cards, self.monitors, self.styles)
        self.assertEqual(data['outputs'], [])
        with self.assertRaises(ConfigError):
            validate_layout(dict(data, version=1), self.styles)

    def test_multiple_outputs_on_same_monitor_reduced_to_first(self):
        data = deepcopy(self.old)
        second = deepcopy(self.output)
        second['style'] = self.styles[1]['name']
        data['outputs'].append(second)
        cards = editor_cards(data, self.monitors)
        self.assertEqual(len(cards[1]['outputs']), 1)
        self.assertEqual(layout_from_cards(cards, self.monitors, self.styles)['outputs'], [self.output])

    def test_bad_names_and_output_limit_rejected(self):
        cards = editor_cards(self.old, self.monitors)
        for name in ('x' * 81, 'a\nb'):
            cards[0]['label'] = name
            with self.assertRaises(ConfigError):
                layout_from_cards(cards, self.monitors, self.styles)
        cards[0]['label'] = ''
        cards[1]['outputs'] = [self.output] * 6
        with self.assertRaises(ConfigError):
            layout_from_cards(cards, self.monitors, self.styles)

    def test_alias_follows_monitor_when_moved(self):
        names = [dict(label='Sál', monitor=monitor_identity(self.monitors[1]))]
        self.monitors[1].x = -1920
        self.assertEqual(monitor_labels(self.monitors, names)[1], 'Sál (-1920, 0)')

    def test_disconnected_name_retained(self):
        identity = dict(monitor_identity(self.monitors[0]), name='missing', x=-1920)
        names = [dict(monitor=identity, label='Stream')]
        cards = editor_cards(self.old, self.monitors)
        data = layout_from_cards(cards, self.monitors, self.styles, names)
        self.assertIn(names[0], data['monitor_names'])

    def controller(self):
        from superpresenter.ui.projection_profiles import ProjectionProfiles
        owner = ProjectionProfiles()
        owner.monitors = self.monitors
        owner.monitor_names = []
        owner.projStyles = self.styles
        owner.chooseProj = {}
        owner.getMonitors = Mock()
        owner.openProjector = Mock()
        owner.projectors = [Mock()]
        owner.runState = False
        owner._profiles_ready = True
        owner._preserve_last = False
        owner._autosave_error = False
        return owner

    def test_apply_write_failure_does_not_replace_live_layout(self):
        owner = self.controller()
        original = owner.projectors
        owner.profile_dir = Path('unused-test-directory')
        data = layout_from_cards(editor_cards(self.old, self.monitors), self.monitors, self.styles)
        with patch('superpresenter.ui.projection_profiles.save_layout', side_effect=ConfigError('denied')):
            with self.assertRaises(ConfigError):
                owner.apply_editor_layout(data, self.monitors)
        self.assertIs(owner.projectors, original)

    def test_topology_change_rejects_apply_before_write(self):
        owner = self.controller()
        expected = deepcopy(self.monitors)
        expected[1].x = -1920
        data = layout_from_cards(editor_cards(self.old, self.monitors), self.monitors, self.styles)
        with patch('superpresenter.ui.projection_profiles.messagebox.showwarning'), patch('superpresenter.ui.projection_profiles.save_layout') as save:
            self.assertFalse(owner.apply_editor_layout(data, expected))
        save.assert_not_called()

    def test_apply_empty_layout_and_restore_it(self):
        owner = self.controller()
        data = dict(version=2, outputs=[], monitor_names=[])
        with tempfile.TemporaryDirectory() as directory:
            owner.profile_dir = Path(directory)
            self.assertTrue(owner.apply_editor_layout(data, self.monitors))
            self.assertEqual(owner.projectorID, -1)
            self.assertEqual(owner.projectors, [])
            owner.persist_layout()
            self.assertEqual(load_layout(Path(directory) / 'last-layout.json', self.styles), data)

    def test_editor_is_blocked_during_projection(self):
        owner = self.controller()
        owner.runState = True
        with patch('superpresenter.ui.projection_profiles.messagebox.showinfo') as info:
            owner.edit_profiles()
        info.assert_called_once()


class ProfileCatalogTests(unittest.TestCase):
    def setUp(self):
        from superpresenter.services.projection_profile_catalog import save_named_profile
        self.save = save_named_profile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.styles = load_styles(ROOT / 'projectors_styles.json')['styles']
        self.data = dict(version=2, outputs=[], monitor_names=[])

    def test_delete_rejects_file_outside_profile_directory(self):
        from superpresenter.services.projection_profile_catalog import delete_named_profile
        with tempfile.TemporaryDirectory() as other:
            path = Path(other) / 'outside.json'
            path.write_text('{}', encoding='utf-8')
            with self.assertRaises(ConfigError):
                delete_named_profile(self.folder, dict(path=path, name='Outside'))
            self.assertTrue(path.exists())

    def test_default_numbers_skip_existing_names(self):
        from superpresenter.services.projection_profile_catalog import next_profile_name
        self.assertEqual(next_profile_name([]), 'Profil 1')
        self.assertEqual(next_profile_name([dict(name='Profil 1'), dict(name='profil 2')]), 'Profil 3')

    def test_rename_updates_one_file_and_catalog(self):
        from superpresenter.services.projection_profile_catalog import profile_catalog
        entry = self.save(self.folder, dict(path=None), 'Profil 1', self.data, self.styles)
        renamed = self.save(self.folder, entry, 'Velikonoce', self.data, self.styles)
        self.assertEqual(entry['path'], renamed['path'])
        self.assertEqual(profile_catalog(self.folder), [renamed])
        self.assertEqual(len(list(self.folder.glob('*.json'))), 1)

    def test_duplicate_names_rejected_without_overwrite(self):
        first = self.save(self.folder, dict(path=None), 'Sál', self.data, self.styles)
        before = first['path'].read_bytes()
        with self.assertRaises(ConfigError):
            self.save(self.folder, dict(path=None), 'sál', self.data, self.styles)
        self.assertEqual(first['path'].read_bytes(), before)

    def test_legacy_and_broken_files_remain_listed(self):
        from superpresenter.services.projection_profile_catalog import profile_catalog
        save_layout(self.folder / 'Starý profil.json', self.data, self.styles)
        (self.folder / 'Chybný.json').write_text('broken', encoding='utf-8')
        self.assertEqual({entry['name'] for entry in profile_catalog(self.folder)}, {'Starý profil', 'Chybný'})

    def test_profile_title_cannot_escape_storage_folder(self):
        for title in ('../Mimo', 'CON', 'Sál / stream'):
            entry = self.save(self.folder, dict(path=None), title, self.data, self.styles)
            self.assertEqual(entry['path'].parent, self.folder)
            self.assertEqual(load_layout(entry['path'], self.styles)['profile_name'], title)


class ProjectionEditorWidgetTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from superpresenter.ui.projection_editor import ProjectionEditor
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        styles = load_styles(ROOT / 'projectors_styles.json')['styles']
        monitors = [SimpleNamespace(name='primary', x=0, y=0, width=1920, height=1080, is_primary=True),
                    SimpleNamespace(name='external', x=1920, y=0, width=1920, height=1080, is_primary=False)]
        self.original = dict(version=1, outputs=[dict(style=styles[0]['name'],
            monitor=monitor_identity(monitors[1]), fullscreen=True, collection=True, window_position=None)])
        self.owner = SimpleNamespace(win=self.root, monitors=monitors, projStyles=styles,
            profile_dir=Path(self.temporary.name), layout_snapshot=Mock(return_value=deepcopy(self.original)),
            apply_editor_layout=Mock(return_value=True))
        self.editor = ProjectionEditor(self.owner)
        self.editor.win.withdraw()
        self.root.update_idletasks()

    def test_names_disabled_outputs_and_cancel_do_not_apply(self):
        self.editor.cards[0]['label'].set('Obsluha')
        self.editor.cards[1]['outputs'][0]['combo'].current(0)
        data = self.editor.draft()
        self.assertEqual(data['outputs'], [])
        self.assertEqual(data['monitor_names'][0]['label'], 'Obsluha')
        with patch('superpresenter.ui.projection_editor.messagebox.askyesnocancel', return_value=False):
            self.editor.cancel()
        self.owner.apply_editor_layout.assert_not_called()

    def test_save_applies_draft_and_closes(self):
        self.editor.cards[1]['label'].set('Sál')
        self.editor.apply()
        data, monitors = self.owner.apply_editor_layout.call_args.args
        self.assertEqual(data['monitor_names'][1]['label'], 'Sál')
        self.assertEqual(len(data['outputs']), 1)
        self.assertEqual(self.editor.win.winfo_exists(), 0)

    def test_failed_save_keeps_draft_open(self):
        self.owner.apply_editor_layout.side_effect = ConfigError('write failed')
        self.editor.cards[1]['label'].set('Draft')
        with patch('superpresenter.ui.projection_editor.messagebox.showerror') as error:
            self.editor.apply()
        error.assert_called_once()
        self.assertTrue(self.editor.win.winfo_exists())
        self.assertEqual(self.editor.cards[1]['label'].get(), 'Draft')

    def test_profile_export_saves_draft_without_applying(self):
        self.editor.profile_name.set('Velikonoce')
        self.editor.cards[1]['label'].set('Velikonoční sál')
        self.assertTrue(self.editor.save_profile())
        path = self.editor.entries[self.editor.selected_profile]['path']
        data = load_layout(path, self.owner.projStyles)
        self.assertEqual(data['monitor_names'][1]['label'], 'Velikonoční sál')
        self.assertEqual(data['profile_name'], 'Velikonoce')
        self.owner.apply_editor_layout.assert_not_called()

    def test_edit_multiple_profiles_and_rename_without_duplicates(self):
        self.assertEqual(self.editor.profile_name.get(), 'Profil 1')
        self.editor.cards[1]['label'].set('Sál')
        self.assertTrue(self.editor.save_profile())
        first_path = self.editor.entries[0]['path']
        self.editor.new_profile()
        self.assertEqual(self.editor.profile_name.get(), 'Profil 2')
        self.editor.profile_name.set('Velikonoce')
        self.editor.cards[1]['outputs'][0]['combo'].current(0)
        self.assertTrue(self.editor.save_profile())
        self.editor.profile_choice.current(0)
        self.editor.switch_profile()
        self.assertEqual(self.editor.cards[1]['label'].get(), 'Sál')
        self.assertGreater(self.editor.cards[1]['outputs'][0]['combo'].current(), 0)
        self.editor.profile_name.set('Bohoslužba')
        self.assertTrue(self.editor.save_profile())
        self.assertEqual(self.editor.entries[0]['path'], first_path)
        self.assertEqual(len(list((self.owner.profile_dir / 'profiles').glob('*.json'))), 2)
        self.owner.apply_editor_layout.assert_not_called()

    def test_cancelled_switch_preserves_dirty_draft(self):
        self.assertTrue(self.editor.save_profile())
        self.editor.new_profile()
        self.editor.cards[1]['label'].set('Neuloženo')
        self.editor.profile_choice.current(0)
        with patch('superpresenter.ui.projection_editor.messagebox.askyesnocancel', return_value=None):
            self.editor.switch_profile()
        self.assertEqual(self.editor.selected_profile, 1)
        self.assertEqual(self.editor.profile_choice.current(), 1)
        self.assertEqual(self.editor.cards[1]['label'].get(), 'Neuloženo')

    def test_failed_save_blocks_switch(self):
        self.assertTrue(self.editor.save_profile())
        self.editor.new_profile()
        self.editor.profile_name.set('Profil 1')
        self.editor.profile_choice.current(0)
        with patch('superpresenter.ui.projection_editor.messagebox.askyesnocancel', return_value=True), patch('superpresenter.ui.projection_editor.messagebox.showerror'):
            self.editor.switch_profile()
        self.assertEqual(self.editor.selected_profile, 1)
        self.assertEqual(self.editor.profile_name.get(), 'Profil 1')

    def test_profile_selection_does_not_apply_live_layout(self):
        self.assertTrue(self.editor.save_profile())
        self.editor.new_profile()
        self.assertTrue(self.editor.save_profile())
        self.editor.profile_choice.current(0)
        self.editor.switch_profile()
        self.owner.apply_editor_layout.assert_not_called()

    def test_hotplug_preserves_dirty_draft_and_adds_disabled_monitor(self):
        self.editor.cards[1]['label'].set('Rozpracovaný sál')
        extra = SimpleNamespace(name='new', x=-1920, y=0, width=1920, height=1080, is_primary=False)
        self.editor.refresh_topology([extra] + self.owner.monitors)
        self.assertEqual(len(self.editor.cards), 3)
        self.assertEqual(self.editor.cards[2]['label'].get(), 'Rozpracovaný sál')
        self.assertEqual(self.editor.cards[0]['outputs'][0]['combo'].current(), 0)
        self.assertIsNone(self.editor.baseline)
        self.owner.apply_editor_layout.assert_not_called()

    def test_hotplug_disconnect_and_reconnect_retains_output(self):
        self.editor.refresh_topology(self.owner.monitors[:1])
        self.assertEqual(len(self.editor.cards), 1)
        self.assertEqual(len(self.editor.draft()['outputs']), 1)
        self.editor.refresh_topology(self.owner.monitors)
        self.assertEqual(len(self.editor.cards), 2)
        self.assertGreater(self.editor.cards[1]['outputs'][0]['combo'].current(), 0)

    def test_qr_control_removed_but_fullscreen_and_saved_preference_remain(self):
        def labels(widget):
            found = []
            for child in widget.winfo_children():
                if child.winfo_class() == 'TCheckbutton':
                    found.append(child.cget('text'))
                found.extend(labels(child))
            return found
        self.assertEqual(labels(self.editor.body), ['Celá obrazovka', 'Celá obrazovka'])
        self.assertTrue(self.editor.draft()['outputs'][0]['collection'])

    def test_delete_last_profile_keeps_live_layout_and_creates_draft(self):
        self.editor.save_profile()
        path = self.editor.entries[0]['path']
        with patch('superpresenter.ui.projection_editor.messagebox.askyesno', return_value=True):
            self.editor.delete_profile()
        self.assertFalse(path.exists())
        self.assertEqual(self.editor.profile_name.get(), 'Profil 1')
        self.assertIsNone(self.editor.entries[0]['path'])
        self.owner.apply_editor_layout.assert_not_called()

    def test_cancel_delete_keeps_file_and_edits(self):
        self.editor.save_profile()
        path = self.editor.entries[0]['path']
        self.editor.cards[1]['label'].set('Draft')
        with patch('superpresenter.ui.projection_editor.messagebox.askyesno', return_value=False):
            self.editor.delete_profile()
        self.assertTrue(path.exists())
        self.assertEqual(self.editor.cards[1]['label'].get(), 'Draft')

    def test_delete_selects_remaining_profile(self):
        self.editor.save_profile()
        self.editor.new_profile()
        self.editor.save_profile()
        with patch('superpresenter.ui.projection_editor.messagebox.askyesno', return_value=True):
            self.editor.delete_profile()
        self.assertEqual(len(self.editor.entries), 1)
        self.assertEqual(self.editor.profile_name.get(), 'Profil 1')

    def test_failed_delete_keeps_selection(self):
        self.editor.save_profile()
        path = self.editor.entries[0]['path']
        with patch('superpresenter.ui.projection_editor.messagebox.askyesno', return_value=True), patch('superpresenter.ui.projection_editor.delete_named_profile', side_effect=ConfigError('denied')), patch('superpresenter.ui.projection_editor.messagebox.showerror') as error:
            self.editor.delete_profile()
        error.assert_called_once()
        self.assertEqual(self.editor.entries[0]['path'], path)
        self.assertTrue(path.exists())

    def test_cards_and_map_follow_horizontal_positions(self):
        cards = list(self.editor.body.winfo_children())
        self.assertLess(cards[0].grid_info()['column'], cards[1].grid_info()['column'])
        self.editor.draw_map()
        for card in self.editor.cards:
            preview = card['preview']
            rectangles = [item for item in preview.find_all() if preview.type(item) == 'rectangle']
            self.assertEqual(len(rectangles), 1)
            self.assertEqual(preview.pack_info()['padx'], 12)

    def test_editor_uses_large_fonts_and_gray_theme(self):
        import tkinter.font as tkfont
        font = tkfont.Font(self.root, font=self.editor.font)
        self.assertEqual(font.actual('size'), 14)
        self.assertEqual(font.actual('family'), 'Courier New')
        self.assertEqual(self.editor.win.cget('background'), '#555555')

    def test_single_monitor_window_is_narrower_than_two(self):
        from superpresenter.ui.projection_editor import ProjectionEditor
        self.root.geometry('+30000+30000')
        self.root.deiconify()
        self.editor.win.geometry('+30000+30000')
        self.editor.win.deiconify()
        self.root.update()
        two_width = self.editor.win.winfo_width()
        self.owner.monitors = self.owner.monitors[:1]
        one = ProjectionEditor(self.owner)
        try:
            one.win.geometry('+30000+30000')
            one.win.deiconify()
            self.root.update()
            one_width = one.win.winfo_width()
            self.assertLess(one_width, two_width)
            self.assertLess(one_width, 800)
        finally:
            one.close()

    def test_preview_is_centered_and_only_slightly_narrower(self):
        self.editor.win.geometry('+30000+30000')
        self.root.deiconify()
        self.root.geometry('+30000+30000')
        self.editor.win.deiconify()
        self.root.update()
        for card in self.editor.cards:
            preview = card['preview']
            tile = preview.master
            frame = card['rows'].master
            self.assertEqual(frame.winfo_width() - preview.winfo_width(), 24)
            self.assertEqual(preview.winfo_x() - frame.winfo_x(), 12)
            self.assertEqual(tile.winfo_width(), frame.winfo_width())




if __name__ == '__main__':
    unittest.main()
