"""Own local projection presets, independent of presentation files and SuperPresenter."""
from dataclasses import dataclass, asdict
import json
from .settings import settings_path
from .domain import Aspect


@dataclass(frozen=True)
class OutputPreset:
    enabled: bool = True
    monitor: str = ''
    aspect: str = '4:3'
    fullscreen: bool = True

    def __post_init__(self):
        if type(self.enabled) is not bool or type(self.monitor) is not str or type(self.fullscreen) is not bool:
            raise ValueError('Neplatný výstup profilu.')
        Aspect(self.aspect)


@dataclass(frozen=True)
class MonitorName:
    monitor: str
    label: str

    def __post_init__(self):
        if type(self.monitor) is not str or not self.monitor or type(self.label) is not str or len(self.label) > 80 or any(ord(c) < 32 for c in self.label):
            raise ValueError('Vlastní název monitoru musí mít nejvýše 80 znaků bez řídicích znaků.')


@dataclass(frozen=True)
class ProjectionPreset:
    name: str
    hall: OutputPreset
    stream: OutputPreset
    monitor_names: tuple[MonitorName, ...] = ()

    def __post_init__(self):
        if type(self.name) is not str or not self.name.strip() or len(self.name) > 80 or any(ord(c) < 32 for c in self.name):
            raise ValueError('Název profilu musí mít 1–80 znaků bez řídicích znaků.')
        if not isinstance(self.hall, OutputPreset) or not isinstance(self.stream, OutputPreset):
            raise ValueError('Neplatný profil.')
        if not self.hall.enabled and not self.stream.enabled:
            raise ValueError('Zapněte alespoň jeden výstup.')
        if type(self.monitor_names) is not tuple or any(not isinstance(n, MonitorName) for n in self.monitor_names) or len({n.monitor for n in self.monitor_names}) != len(self.monitor_names):
            raise ValueError('Neplatné vlastní názvy monitorů.')


def defaults():
    return (ProjectionPreset('Jen stream', OutputPreset(False), OutputPreset(True, aspect='16:9')),
            ProjectionPreset('Sál + stream', OutputPreset(), OutputPreset(True, aspect='16:9')),
            ProjectionPreset('Jen sál', OutputPreset(), OutputPreset(False, aspect='16:9')))


def profile_path():
    return settings_path().with_name('projection-profiles.json')


def validate_catalog(profiles):
    if not profiles or any(not isinstance(p, ProjectionPreset) for p in profiles):
        raise ValueError('Katalog profilů je prázdný nebo neplatný.')
    if len({p.name.strip().casefold() for p in profiles}) != len(profiles):
        raise ValueError('Profil s tímto názvem již existuje.')


def load_profiles(path=None):
    from .atomic_file import read_text
    path = path or profile_path()
    if not path.exists():
        return defaults()
    try:
        data = json.loads(read_text(path))
        if type(data.get('version')) is not int or data['version'] != 1:
            raise ValueError('Nepodporovaná verze profilů.')
        profiles = tuple(ProjectionPreset(p['name'], OutputPreset(**p['hall']), OutputPreset(**p['stream']),
                                         tuple(MonitorName(**n) for n in p.get('monitor_names', []))) for p in data['profiles'])
        validate_catalog(profiles)
        return profiles
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError('Soubor projekčních profilů je poškozený.') from exc


def save_profiles(profiles, path=None):
    from .atomic_file import atomic_write
    validate_catalog(profiles)
    path = path or profile_path()
    atomic_write(path, json.dumps(dict(version=1, profiles=[asdict(p) for p in profiles]), ensure_ascii=False, indent=2).encode('utf-8'))
