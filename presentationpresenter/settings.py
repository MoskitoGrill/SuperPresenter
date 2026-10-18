"""Own application preferences; never reads SuperPresenter settings/styles."""
from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path

@dataclass(frozen=True)
class AppSettings:
    geometry: str = '1100x720'
    background: str = '#555555'
    panel: str = '#444444'
    foreground: str = '#ffffff'
    font_family: str = 'Courier New'
    content_font_family: str = 'Calibri'
    content_font_size: int = 36
    show_projection_button: bool = True
    show_apply_button: bool = True
    show_navigation_buttons: bool = True
    temporary_ribbon_tabs: bool = False

def settings_path() -> Path:
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.config'))) / 'PresentationPresenter' / 'settings.json'

def load_settings(path: Path | None = None) -> AppSettings:
    try:
        data = json.loads((path or settings_path()).read_text(encoding='utf-8'))
        settings = AppSettings(**data)
        import re
        if not re.fullmatch(r'\d{2,5}x\d{2,5}(?:[+-]\d+[+-]\d+)?', settings.geometry):
            raise ValueError('Invalid geometry')
        if any(not re.fullmatch(r'#[0-9a-fA-F]{6}', c) for c in (settings.background, settings.panel, settings.foreground)):
            raise ValueError('Invalid color')
        if type(settings.font_family) is not str or not settings.font_family.strip():
            raise ValueError('Invalid font')
        if (type(settings.content_font_family) is not str or not settings.content_font_family.strip()
                or settings.content_font_family != settings.content_font_family.strip()
                or len(settings.content_font_family) > 128
                or any(ord(c) < 32 for c in settings.content_font_family)):
            raise ValueError('Invalid content font')
        if type(settings.content_font_size) is not int or not 8 <= settings.content_font_size <= 144:
            raise ValueError('Invalid content size')
        if any(type(value) is not bool for value in (settings.show_projection_button,
                settings.show_apply_button, settings.show_navigation_buttons, settings.temporary_ribbon_tabs)):
            raise ValueError('Invalid control visibility')
        return settings
    except (OSError, ValueError, TypeError, AttributeError):
        return AppSettings()

def save_settings(settings: AppSettings, path: Path | None = None):
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)
