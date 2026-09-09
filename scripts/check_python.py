"""Compile active sources in memory and check availability of imported modules."""
import ast
import importlib.util
import os
from pathlib import Path
import sys
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    files = [ROOT / 'super_presenter.py', ROOT / 'song_editor.py']
    for directory in ('superpresenter', 'scripts', 'tests'):
        files.extend(sorted((ROOT / directory).rglob('*.py')))
    errors = []
    modules = set()
    for path in files:
        try:
            source = path.read_text(encoding='utf-8-sig')
            with warnings.catch_warnings():
                warnings.simplefilter('error', SyntaxWarning)
                compile(source, str(path), 'exec')
            for node in ast.walk(ast.parse(source, filename=str(path))):
                if isinstance(node, ast.Import):
                    modules.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    modules.add(node.module)
        except (SyntaxError, SyntaxWarning, UnicodeError) as exc:
            errors.append(f'{path.relative_to(ROOT)}: {exc}')
    for module in sorted(modules):
        # RecoveryLease selects the appropriate platform-specific stdlib module.
        if module == ('fcntl' if os.name == 'nt' else 'msvcrt'):
            continue
        if module.split('.')[0] == 'fixtures' or (ROOT / 'tests' / (module + '.py')).exists():
            continue
        try:
            if importlib.util.find_spec(module) is None:
                errors.append(f'Import not found: {module}')
        except (ImportError, ValueError, AttributeError) as exc:
            errors.append(f'Import {module}: {exc}')
    for error in errors:
        print(error)
    print(f'Python files: {len(files)}; imported modules: {len(modules)}; errors: {len(errors)}')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
