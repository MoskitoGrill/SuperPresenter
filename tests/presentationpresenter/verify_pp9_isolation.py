"""Run selected existing SuperPresenter regressions and hash protected files."""
from pathlib import Path
import hashlib
import sys
import unittest
import subprocess

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
# The bundled QA Python has Pillow; the project's existing venv supplies the
# pure-Python screeninfo package. Do not install or alter either environment.
project_packages = root / '.venv' / 'Lib' / 'site-packages'
if project_packages.is_dir():
    sys.path.append(str(project_packages))


def snapshot():
    paths = []
    for directory in ('superpresenter', 'songs', 'bible', 'presentation', 'profiles'):
        paths.extend(p for p in (root / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.extend(p for p in root.glob('*.json'))
    paths.extend(root / name for name in ('super_presenter.py', 'song_editor.py', 'presentation_presenter.py', 'requirements.txt', 'requirements-build.txt'))
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


before = snapshot()
suite = unittest.TestSuite()
for pattern in ('test_module_boundaries.py', 'test_song_repository.py', 'test_song_recovery.py',
                'test_projection_config.py', 'test_release_stability.py', 'test_window_lifecycle.py', 'test_main_controls.py'):
    suite.addTests(unittest.defaultTestLoader.discover(str(root / 'tests'), pattern=pattern))
result = unittest.TextTestRunner(verbosity=2).run(suite)
# Legacy suites temporarily replace imported modules; dispatch checks need a
# fresh import graph, like the actual separately launched companion process.
code = (f'import sys, unittest; sys.path.append({str(project_packages)!r}); '
        'import presentationpresenter.app, presentationpresenter.bible_window; '
        f'suite=unittest.defaultTestLoader.discover({str(root / "tests")!r}, pattern="test_standalone.py"); '
        'result=unittest.TextTestRunner(verbosity=2).run(suite); sys.exit(not result.wasSuccessful())')
standalone = subprocess.run([sys.executable, '-B', '-c', code], cwd=root)
after = snapshot()
changed = [p for p in before.keys() | after.keys() if before.get(p) != after.get(p)]
print('Protected files:', len(before), 'changed:', changed)
sys.exit(0 if result.wasSuccessful() and standalone.returncode == 0 and not changed else 1)
