"""Build a fresh portable Windows release; never overwrite an existing release."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from superpresenter.version import VERSION, RELEASE_STAGE


def main():
    if sys.platform != 'win32':
        raise SystemExit('Build this release on Windows x64 with Python 3.13.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    output = ROOT / 'dist' / (VERSION + '-' + stamp)
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean',
                    '--distpath', str(output), '--workpath', str(ROOT / 'build' / stamp),
                    str(ROOT / 'packaging' / 'SuperPresenter.spec')], cwd=ROOT, check=True)
    app = output / 'SuperPresenter-v3'
    for name in ('songs', 'images', 'bible', 'presentations', 'presentation'):
        shutil.copytree(ROOT / name, app / name,
                        ignore=shutil.ignore_patterns('__pycache__', '.song-recovery', '*.tmp', '*.temp'))
    for name in ('gui_style.json', 'projectors_styles.json', 'settings.json',
                 'presentation_presenter.py', 'presentation_presenter_v2.py', 'oprava_xml_tagu.py'):
        shutil.copy2(ROOT / name, app / name)
    shutil.copy2(ROOT / 'docs' / 'windows-release.md', app / 'CTI-ME.md')
    packages = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    (app / 'build-dependencies.txt').write_text(packages, encoding='utf-8')
    metadata = {'version': VERSION, 'stage': RELEASE_STAGE, 'built_utc': stamp,
                'python': sys.version, 'platform': sys.platform}
    try:
        metadata['git_commit'] = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        metadata['git_dirty'] = bool(subprocess.check_output(
            ['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        metadata['git_commit'] = None
    metadata['sha256'] = {str(p.relative_to(app)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(app.rglob('*')) if p.is_file()}
    (app / 'release.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    archive = shutil.make_archive(str(output / ('SuperPresenter-' + VERSION + '-win64')), 'zip',
                                 root_dir=output, base_dir=app.name)
    print('\nRelease folder:', app)
    print('ZIP:', archive)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
