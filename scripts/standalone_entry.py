"""Standalone entry point, including existing companion tools and diagnostics."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import runpy
import sys
import traceback

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from superpresenter.paths import PROJECT_ROOT
from superpresenter.version import VERSION


def main():
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--presentation-editor', action='store_true')
    modes.add_argument('--repair-xml', action='store_true')
    modes.add_argument('--smoke-test', metavar='REPORT_JSON')
    parser.add_argument('--version', action='version', version=VERSION)
    args = parser.parse_args()
    report = Path(args.smoke_test).resolve() if args.smoke_test else None
    os.chdir(PROJECT_ROOT)
    try:
        if report:
            from superpresenter.release_check import run_check
            result = run_check()
            report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        else:
            from superpresenter.services.projection_config import user_config_dir
            log_dir = user_config_dir() / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            # Some legacy tools print diagnostics even in a windowed executable.
            with (log_dir / 'standalone-console.log').open('w', encoding='utf-8') as stream:
                original_streams = sys.stdout, sys.stderr
                try:
                    sys.stdout = sys.stderr = stream
                    if args.presentation_editor or args.repair_xml:
                        script = 'presentation_presenter.py' if args.presentation_editor else 'oprava_xml_tagu.py'
                        runpy.run_path(str(Path(PROJECT_ROOT) / script), run_name='__main__')
                    else:
                        from superpresenter.app import main as run_app
                        run_app()
                finally:
                    sys.stdout, sys.stderr = original_streams
        return 0
    except Exception:
        detail = traceback.format_exc()
        if report:
            report.write_text(json.dumps({'ok': False, 'error': detail}, indent=2), encoding='utf-8')
        else:
            ctypes.windll.user32.MessageBoxW(None, detail, 'SuperPresenter – chyba spuštění', 0x10)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

