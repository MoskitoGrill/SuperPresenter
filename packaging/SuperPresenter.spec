# Build on Windows with the pinned dependencies in requirements-build.txt.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent
icon = root / 'images' / 'ikona.ico'
if not icon.is_file():
    icon = root / 'images' / 'launcher-default.ico'
dnd_data, dnd_binaries, dnd_imports = collect_all('tkinterdnd2')
a = Analysis(
    [str(root / 'scripts' / 'standalone_entry.py')],
    pathex=[str(root)], binaries=dnd_binaries, datas=dnd_data,
    hiddenimports=['presentation_presenter'] + dnd_imports,
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='SuperPresenter',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, icon=str(icon), version=str(root / 'packaging' / 'version_info.txt'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SuperPresenter-v3')
