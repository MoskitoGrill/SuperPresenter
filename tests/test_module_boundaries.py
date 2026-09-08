"""Regression checks for the extracted application boundaries."""
import ast
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


class ModuleBoundaryTests(unittest.TestCase):
    def test_services_import_without_ui_dependencies(self):
        code = """
import importlib, sys
for name in ('tkinter', 'PIL', 'screeninfo', 'super_presenter', 'song_editor'):
    sys.modules[name] = None
for name in ('presentation_session', 'construct_parser', 'stationary_pages',
             'stationary_navigation', 'song_repository', 'song_edit_session'):
    importlib.import_module('superpresenter.services.' + name)
"""
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_exports_are_same_objects(self):
        import super_presenter as legacy
        from superpresenter.ui.main_window import GUI
        from superpresenter.ui.projector_window import ProjWindow
        from superpresenter.ui.source_sorter import SortingWin
        from superpresenter.services.presentation_session import WidgetSource
        from superpresenter.ui import projector_widgets
        for obj in (GUI, ProjWindow, SortingWin, WidgetSource,
                    projector_widgets.Widget_OneLine,
                    projector_widgets.Widget_FlowLines,
                    projector_widgets.Widget_StanzaPaged,
                    projector_widgets.Widget_Image):
            self.assertIs(getattr(legacy, obj.__name__), obj)

    def test_startup_keeps_recovery_before_mainloop(self):
        from superpresenter import app
        gui = Mock()
        calls = Mock()
        calls.attach_mock(gui.song_editor_widget.start_recovery, 'recovery')
        calls.attach_mock(gui.run, 'run')
        with patch.object(app, 'GUI', return_value=gui), patch.object(app.logging, 'basicConfig'):
            app.main()
        self.assertEqual([call[0] for call in calls.mock_calls], ['recovery', 'run'])
        gui.song_editor_widget.start_recovery.assert_called_once_with(
            on_restored=gui.on_editor_restored)

    def test_resource_root_and_image_path(self):
        from superpresenter.paths import PROJECT_ROOT
        from superpresenter.ui import projector_widgets
        self.assertEqual(Path(PROJECT_ROOT), ROOT)
        style = {'source': 'images/test.png', 'x': 0, 'y': 0, 'anchor': 'center'}
        with patch.object(projector_widgets.Image, 'open') as open_image, \
             patch.object(projector_widgets.ImageTk, 'PhotoImage'):
            projector_widgets.Widget_Image(Mock(), style, Mock())
        self.assertEqual(Path(open_image.call_args.args[0]), ROOT / 'images/test.png')

    def test_no_data_imports_tk_and_no_back_import_to_launcher(self):
        for path in (ROOT / 'superpresenter').rglob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8-sig'))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or '')
            with self.subTest(path=path):
                self.assertNotIn('super_presenter', imports)
                if path.parent.name in ('domain', 'services'):
                    self.assertFalse(any(name.startswith('tkinter') for name in imports))


if __name__ == '__main__':
    unittest.main()
