"""Named profile catalog; display names are independent of file paths."""
from pathlib import Path
import re
from superpresenter.services.projection_config import ConfigError, read_json, save_layout


def profile_catalog(folder):
    entries = []
    for path in sorted(Path(folder).glob('*.json')):
        try:
            data = read_json(path)
            name = data.get('profile_name', path.stem) if isinstance(data, dict) else path.stem
            if not isinstance(name, str) or not name.strip():
                name = path.stem
        except ConfigError:
            name = path.stem
        entries.append(dict(path=path, name=name))
    return entries


def next_profile_name(entries):
    names = {entry['name'].casefold() for entry in entries}
    index = 1
    while f'profil {index}' in names:
        index += 1
    return f'Profil {index}'


def save_named_profile(folder, entry, name, data, styles):
    name = name.strip()
    if not name or len(name) > 80 or any(ord(c) < 32 for c in name):
        raise ConfigError('Název profilu musí mít 1–80 znaků bez řídicích znaků.')
    for other in profile_catalog(folder):
        if other['path'] != entry['path'] and other['name'].casefold() == name.casefold():
            raise ConfigError(f'Profil „{name}“ již existuje. Zvolte jiný název.')
    path = entry['path']
    if path is None:
        stem = re.sub(r'[<>:"/\\|?*]', '_', name).rstrip(' .') or 'Profil'
        if stem.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
            stem = 'Profil ' + stem
        path = Path(folder) / f'{stem}.json'
        number = 2
        while path.exists():
            path = Path(folder) / f'{stem} ({number}).json'
            number += 1
    save_layout(path, dict(data, profile_name=name), styles)
    return dict(path=path, name=name)


def delete_named_profile(folder, entry):
    """Delete only the selected JSON inside the managed profile directory."""
    if entry['path'] is None:
        return
    path = Path(entry['path'])
    if path.resolve().parent != Path(folder).resolve() or path.suffix.lower() != '.json':
        raise ConfigError('Profil nelze smazat mimo složku profilů.')
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise ConfigError(f'Nelze smazat profil „{entry["name"]}“: {exc}') from exc
