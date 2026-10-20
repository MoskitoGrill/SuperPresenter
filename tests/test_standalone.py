"""Source/frozen resource and subprocess boundaries."""
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

from superpresenter import processes


class StandaloneTests(unittest.TestCase):
    def test_frozen_data_root_is_executable_directory(self):
        source = Path(__file__).resolve().parents[1] / 'superpresenter' / 'paths.py'
        executable = str(Path.cwd() / 'Verze 3 žluťoučká' / 'SuperPresenter.exe')
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', executable):
            values = runpy.run_path(str(source))
        self.assertEqual(Path(values['PROJECT_ROOT']), Path(executable).parent)

    def test_frozen_companion_does_not_treat_exe_as_python(self):
        with patch.object(sys, 'frozen', True, create=True):
            self.assertEqual(processes.tool_command('presentation_presenter.py'),
                             [sys.executable, '--presentation-editor'])
            self.assertEqual(processes.tool_command('presentation_presenter_v2.py'),
                             [sys.executable, '--presentation-editor'])
            self.assertEqual(processes.tool_command('oprava_xml_tagu.py'),
                             [sys.executable, '--repair-xml'])

    def test_source_companion_uses_script_path(self):
        with patch.object(sys, 'frozen', False, create=True):
            command = processes.tool_command('presentation_presenter_v2.py')
        self.assertEqual(command[0], sys.executable)
        self.assertTrue(Path(command[1]).is_file())
        self.assertEqual(Path(command[1]).name, 'presentation_presenter_v2.py')

    def test_packaged_presentation_dispatch_uses_v2(self):
        import tempfile
        entry = Path(__file__).resolve().parents[1] / 'scripts' / 'standalone_entry.py'
        module = runpy.run_path(str(entry))
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(sys, 'argv', ['SuperPresenter.exe', '--presentation-editor']), \
             patch('os.chdir'), \
             patch('superpresenter.services.projection_config.user_config_dir', return_value=Path(temp)), \
             patch('presentationpresenter.app.main') as launch:
            self.assertEqual(module['main'](), 0)
            launch.assert_called_once_with()

    def test_unknown_companion_is_rejected(self):
        with self.assertRaises(ValueError):
            processes.tool_command('anything.py')
