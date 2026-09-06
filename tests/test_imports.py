"""Import checks in fresh processes, without creating a Tk window."""

from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ImportSmokeTests(unittest.TestCase):
    def test_imports_without_gui(self):
        for module_name in ("super_presenter", "song_editor"):
            with self.subTest(module=module_name):
                # Keep real imports/dependencies; fail if an import starts Tk.
                code = """
import importlib
import sys
from unittest.mock import patch
import tkinter

with patch.object(tkinter, 'Tk', side_effect=AssertionError('Import started Tk')), \
     patch.object(tkinter, 'mainloop', side_effect=AssertionError('Import started mainloop')):
    importlib.import_module(sys.argv[1])
"""
                result = subprocess.run(
                    [sys.executable, "-B", "-c", code, module_name],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(
                    result.returncode, 0, result.stdout + result.stderr
                )


if __name__ == "__main__":
    unittest.main()
