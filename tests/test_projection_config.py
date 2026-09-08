"""Projection configuration regressions without opening Tk windows."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from superpresenter.services.projection_config import (
    ConfigError, default_monitor, load_layout, load_styles, match_monitor,
    monitor_identity, monitor_labels, resource_path, save_layout, validate_layout,
)

ROOT = Path(__file__).resolve().parents[1]


def monitor(name='Projector', x=1920, primary=False):
    return SimpleNamespace(name=name, x=x, y=0, width=1920, height=1080, is_primary=primary)


class ProjectionConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'layout.json'
        self.styles = load_styles(ROOT / 'projectors_styles.json')['styles']
        self.data = dict(version=1, outputs=[dict(style=self.styles[0]['name'],
            monitor=monitor_identity(monitor()), fullscreen=True, collection=True,
            window_position=[1920, 20])])

    def test_round_trip_and_unicode_profile(self):
        path = self.path.parent / 'Velikonoce – sál.json'
        save_layout(path, self.data, self.styles)
        self.assertEqual(load_layout(path, self.styles), self.data)

    def test_invalid_profiles(self):
        for key, value in [('version', 99), ('version', True), ('outputs', []), ('outputs', [{}] * 6)]:
            data = deepcopy(self.data)
            data[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ConfigError):
                validate_layout(data, self.styles)
        for key, value in [('style', 'missing'), ('fullscreen', 1), ('collection', 'yes'),
                           ('monitor', {}), ('window_position', 'bad')]:
            data = deepcopy(self.data)
            data['outputs'][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ConfigError, 'Výstup 1'):
                validate_layout(data, self.styles)

    def test_missing_and_broken_json(self):
        with self.assertRaises(ConfigError):
            load_layout(self.path, self.styles)
        self.path.write_text('{broken', encoding='utf-8')
        with self.assertRaisesRegex(ConfigError, 'layout.json'):
            load_layout(self.path, self.styles)

    def test_invalid_save_preserves_previous_file(self):
        save_layout(self.path, self.data, self.styles)
        before = self.path.read_bytes()
        with self.assertRaises(ConfigError):
            save_layout(self.path, {'version': 99}, self.styles)
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_replace_preserves_previous_file_and_cleans_temp(self):
        save_layout(self.path, self.data, self.styles)
        before = self.path.read_bytes()
        with patch.object(Path, 'replace', side_effect=OSError('write denied')):
            with self.assertRaisesRegex(ConfigError, 'write denied'):
                save_layout(self.path, self.data, self.styles)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_monitor_reordering_and_repositioning(self):
        saved = monitor_identity(monitor())
        self.assertEqual(match_monitor(saved, [monitor(), monitor('Primary', 0, True)]), 0)
        self.assertEqual(match_monitor(saved, [monitor('Primary', 0, True), monitor(x=-1920)]), 1)
        self.assertEqual(default_monitor([monitor('Primary', 0, True), monitor()]), 1)
        self.assertEqual(default_monitor([monitor('Primary', 0, True)]), 0)

    def test_missing_and_ambiguous_monitor(self):
        saved = monitor_identity(monitor())
        self.assertIsNone(match_monitor(saved, [monitor('Other', 0, True)]))
        self.assertIsNone(match_monitor(saved, [monitor(x=-1920), monitor(x=3840)]))
        self.assertIsNone(match_monitor(saved, []))
        self.assertIsNone(match_monitor(saved, [monitor('Replacement')]))

    def test_image_paths_independent_of_cwd(self):
        self.assertEqual(resource_path('images/stream_bg.png'), ROOT / 'images/stream_bg.png')
        for path in ['/images/a.png', r'C:\images\a.png', '../a.png', r'\images\a.png']:
            with self.subTest(path=path), self.assertRaises(ConfigError):
                resource_path(path)

    def test_style_errors_identify_style_and_field(self):
        original = json.loads((ROOT / 'projectors_styles.json').read_text(encoding='utf-8'))
        for field, value in [('mode', 'unknown'), ('fonts', []), ('widgets', [{}]),
                             ('collection', {'source': 'images/missing.png'}), ('sources', None)]:
            data = deepcopy(original)
            data['styles'][0][field] = value
            self.path.write_text(json.dumps(data), encoding='utf-8')
            with self.subTest(field=field), self.assertRaisesRegex(ConfigError, 'Styl „' + self.styles[0]['name']):
                load_styles(self.path)

    def test_duplicate_style_rejected(self):
        data = json.loads((ROOT / 'projectors_styles.json').read_text(encoding='utf-8'))
        data['styles'].append(data['styles'][0])
        self.path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ConfigError, 'duplicitní'):
            load_styles(self.path)

    def test_service_imports_without_gui(self):
        code = "import sys; sys.modules.update({x: None for x in ('tkinter', 'PIL', 'screeninfo')}); from superpresenter.services.projection_config import load_styles; load_styles('projectors_styles.json')"
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def controller(self):
        from superpresenter.ui.projection_profiles import ProjectionProfiles
        obj = ProjectionProfiles()
        obj.monitors = [monitor('Primary', 0, True)]
        obj.projStyles = self.styles
        obj.projectors = [Mock()]
        obj.projectorID = 0
        obj.chooseProj = {}
        obj.openProjector = Mock()
        obj.getMonitors = Mock()
        obj.runState = False
        return obj

    def test_missing_monitor_fallback_is_windowed(self):
        obj = self.controller()
        save_layout(self.path, self.data, self.styles)
        with patch('superpresenter.ui.projection_profiles.messagebox.askyesno', return_value=True):
            self.assertTrue(obj.restore_profile(self.path))
        self.assertFalse(obj.projectors[0].fullscreen)
        self.assertEqual(obj.projectors[0].monitor, 0)
        self.assertEqual(obj.projectors[0].winPlacement, '')
        self.assertTrue(obj.projectors[0].collection)

    def test_cancelled_fallback_keeps_layout(self):
        obj = self.controller()
        original = obj.projectors
        save_layout(self.path, self.data, self.styles)
        with patch('superpresenter.ui.projection_profiles.messagebox.askyesno', return_value=False):
            self.assertFalse(obj.restore_profile(self.path))
        self.assertIs(obj.projectors, original)

    def test_invalid_load_keeps_layout(self):
        obj = self.controller()
        original = obj.projectors
        with patch('superpresenter.ui.projection_profiles.messagebox.showerror') as error:
            self.assertFalse(obj.restore_profile(self.path))
        error.assert_called_once()
        self.assertIs(obj.projectors, original)

    def test_first_start_keeps_defaults_and_does_not_write(self):
        obj = self.controller()
        original = obj.projectors
        with patch('superpresenter.ui.projection_profiles.user_config_dir', return_value=self.path.parent):
            obj.init_profiles()
        self.assertIs(obj.projectors, original)
        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_invalid_last_layout_not_overwritten_on_close(self):
        obj = self.controller()
        last = self.path.parent / 'last-layout.json'
        last.write_text('broken', encoding='utf-8')
        with patch('superpresenter.ui.projection_profiles.user_config_dir', return_value=self.path.parent), patch('superpresenter.ui.projection_profiles.messagebox.showerror'):
            obj.init_profiles()
            obj.persist_layout(explicit=False)
        self.assertEqual(last.read_text(encoding='utf-8'), 'broken')

    def test_restore_resolves_style_name_and_each_output(self):
        obj = self.controller()
        obj.monitors = [monitor(), monitor('Primary', 0, True)]
        obj.projStyles = list(reversed(self.styles))
        second = deepcopy(self.data['outputs'][0])
        second.update(style=self.styles[1]['name'], collection=False, fullscreen=False,
                      monitor=monitor_identity(obj.monitors[1]), window_position=[50, 50])
        self.data['outputs'].append(second)
        save_layout(self.path, self.data, self.styles)
        self.assertTrue(obj.restore_profile(self.path))
        self.assertEqual(obj.projectors[0].style, len(self.styles) - 1)
        self.assertEqual(obj.projectors[1].monitor, 1)
        self.assertFalse(obj.projectors[1].collection)
        self.assertEqual(obj.projectors[1].winPlacement, '+50+50')
        self.assertEqual(obj.layout_snapshot(), dict(self.data, version=2, monitor_names=[]))

    def test_monitor_labels_do_not_replace_hardware_names(self):
        from superpresenter.ui.projection_profiles import ProjectionProfiles
        obj = self.controller()
        hardware = monitor('Original name', -1920)
        with patch('superpresenter.ui.projection_profiles.get_monitors', return_value=[hardware]):
            ProjectionProfiles.getMonitors(obj)
        self.assertEqual(hardware.name, 'Original name')
        self.assertEqual(obj.chooseProj['values'], ['Hlavní (-1920, 0)'])

    def test_position_labels_follow_connected_layout(self):
        main = monitor('Primary', 0, True)
        left = monitor(x=-1920)
        right = monitor(x=1920)
        self.assertEqual(monitor_labels([main]), ['Hlavní (0, 0)'])
        self.assertEqual(monitor_labels([right, main, left]),
                         ['Vpravo (1920, 0)', 'Hlavní (0, 0)', 'Vlevo (-1920, 0)'])
        self.assertEqual(monitor_labels([left, monitor(x=-3840), main]),
                         ['Vlevo – 2. zleva (-1920, 0)', 'Vlevo – 1. zleva (-3840, 0)', 'Hlavní (0, 0)'])
        self.assertEqual(monitor_labels([left, main])[0], 'Vlevo (-1920, 0)')

    def test_vertical_and_diagonal_monitor_labels(self):
        above = monitor(x=0)
        above.y = -1080
        diagonal = monitor(x=1920)
        diagonal.y = 1080
        self.assertEqual(monitor_labels([monitor('Primary', 0, True), above, diagonal]),
                         ['Hlavní (0, 0)', 'Nahoře (0, -1080)', 'Vpravo dole (1920, 1080)'])
        self.assertEqual(monitor_labels([]), [])

    def test_dropdown_refresh_preserves_selected_output(self):
        obj = self.controller()
        obj.projectorID = 1
        obj.projectors = [Mock(), Mock()]
        obj.layout_snapshot = Mock(return_value=self.data)
        def restore(*args, **kwargs):
            obj.projectorID = 0
            return True
        obj.restore_profile = Mock(side_effect=restore)
        obj.refresh_monitor_choices()
        obj.restore_profile.assert_called_once_with(None, data=self.data)
        self.assertEqual(obj.projectorID, 1)
        obj.runState = True
        obj.refresh_monitor_choices()
        self.assertEqual(obj.restore_profile.call_count, 1)

    def test_load_blocked_during_projection(self):
        obj = self.controller()
        obj.runState = True
        with patch('superpresenter.ui.projection_profiles.messagebox.showinfo'), patch('superpresenter.ui.projection_profiles.filedialog.askopenfilename') as dialog:
            obj.load_profile()
        dialog.assert_not_called()


if __name__ == '__main__':
    unittest.main()
