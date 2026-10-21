"""Source/frozen resource and subprocess boundaries."""
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

from superpresenter import processes


class StandaloneTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Windows launcher process family')
    def test_v2_launcher_child_closes_and_preserves_save_cancel(self):
        import json
        import subprocess
        import tempfile
        import time
        fixture = Path(__file__).parent / 'presentationpresenter' / 'companion_close_fixture.py'
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with (folder / 'log').open('w', encoding='utf-8') as log:
                process = subprocess.Popen([sys.executable, '-B', str(fixture), 'launcher', temp],
                                           stdout=log, stderr=log)
                try:
                    deadline = time.monotonic() + 15
                    ready = folder / 'ready.json'
                    while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                        time.sleep(.03)
                    self.assertTrue(ready.exists(), (folder / 'log').read_text(encoding='utf-8'))
                    info = json.loads(ready.read_text(encoding='utf-8'))
                    self.assertNotEqual(info['pid'], process.pid)
                    self.assertIn(info['pid'], processes._process_family(process.pid))
                    self.assertTrue(processes.request_tool_close(process, 'PresentationPresenter —'))
                    deadline = time.monotonic() + 5
                    while not (folder / 'asked').exists() and time.monotonic() < deadline:
                        time.sleep(.03)
                    self.assertTrue((folder / 'asked').exists())
                    self.assertIsNone(process.poll())  # Cancelling save keeps v2 alive.
                    (folder / 'allow-close').touch()
                    self.assertTrue(processes.request_tool_close(process, 'PresentationPresenter —'))
                    self.assertEqual(process.wait(timeout=8), 0)
                finally:
                    if process.poll() is None:
                        (folder / 'allow-close').touch()
                        processes.request_tool_close(process, 'PresentationPresenter —')
                        process.wait(timeout=25)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows close message')
    def test_normal_close_calls_window_protocol(self):
        import os
        import tkinter as tk
        from types import SimpleNamespace
        root = tk.Tk()
        calls = []
        title = 'SuperPresenter own close test ' + str(os.getpid())
        root.title(title)
        root.protocol('WM_DELETE_WINDOW', lambda: calls.append('close'))
        try:
            root.update()
            process = SimpleNamespace(pid=os.getpid(), poll=lambda: None)
            self.assertTrue(processes.request_tool_close(process, title))
            root.update()
            self.assertEqual(calls, ['close'])
            self.assertTrue(root.winfo_exists())
            self.assertFalse(processes.request_tool_close(process, 'Nonexistent companion QA title'))
        finally:
            root.destroy()

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
            self.assertEqual(processes.tool_command('presentation_bible.py'),
                             [sys.executable, '--bible'])
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

    def test_bible_source_and_packaged_dispatch(self):
        import tempfile
        with patch.object(sys, 'frozen', False, create=True):
            command = processes.tool_command('presentation_bible.py')
        self.assertEqual(Path(command[1]).name, 'presentation_bible.py')
        self.assertTrue(Path(command[1]).is_file())
        entry = Path(__file__).resolve().parents[1] / 'scripts' / 'standalone_entry.py'
        module = runpy.run_path(str(entry))
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(sys, 'argv', ['SuperPresenter.exe', '--bible']), \
             patch('os.chdir'), \
             patch('superpresenter.services.projection_config.user_config_dir', return_value=Path(temp)), \
             patch('presentationpresenter.bible_window.main') as bible, \
             patch('presentationpresenter.app.main') as presenter:
            self.assertEqual(module['main'](), 0)
            bible.assert_called_once_with()
            presenter.assert_not_called()
