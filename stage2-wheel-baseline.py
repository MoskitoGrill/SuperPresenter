"""Run the existing wheel test against the unmodified HEAD song editor."""
import subprocess
import sys
import types
import unittest
from pathlib import Path

baseline = len(sys.argv) == 1
if baseline:
    source = subprocess.check_output(['git', 'show', 'HEAD:song_editor.py']).decode('utf-8')
    module = types.ModuleType('song_editor')
    module.__file__ = str(Path('song_editor.py').resolve())
    sys.modules['song_editor'] = module
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
sys.path.insert(0, 'tests')
from test_song_editor_integration import EditorIntegrationTests

print(('HEAD' if baseline else 'Current') + ' song_editor.py, three repetitions', flush=True)
result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
    EditorIntegrationTests('test_wheel_over_expanding_verse_scrolls_editor')
    for _ in range(3)]))
sys.exit(not result.wasSuccessful())
