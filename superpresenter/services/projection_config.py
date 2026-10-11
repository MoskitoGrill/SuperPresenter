"""Versioned projection layouts and resource validation; no GUI dependencies."""
import json
import math
import os
from pathlib import Path, PureWindowsPath
import tempfile

from superpresenter.paths import PROJECT_ROOT
from .projection_limits import DEFAULT_HALL_ROWS, row_limits
from .stationary_navigation import style_mode


class ConfigError(ValueError):
    """A configuration problem suitable for display to the operator."""


def user_config_dir():
    if os.name == 'nt':
        return Path(os.environ.get('APPDATA', Path.home() / 'AppData/Roaming')) / 'SuperPresenter'
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'SuperPresenter'


def resource_path(value, root=PROJECT_ROOT):
    if not isinstance(value, str) or not value:
        raise ConfigError('Cesta obrázku musí být neprázdný text.')
    relative = Path(value.replace('\\', '/'))
    if relative.anchor or PureWindowsPath(value).drive or '..' in relative.parts:
        raise ConfigError(f'Obrázek musí mít cestu relativní ke kořeni aplikace: {value!r}')
    return Path(root) / relative


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise ConfigError(f'{path}: {exc}') from exc


def _require(condition, message):
    if not condition:
        raise ConfigError(message)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def load_styles(path, root=PROJECT_ROOT):
    data = read_json(path)
    _require(isinstance(data, dict), 'Styly: očekáván objekt.')
    styles = data.get('styles')
    _require(isinstance(styles, list) and styles, 'Styly: chybí neprázdný seznam styles.')
    animation = data.get('animation', {})
    _require(isinstance(animation, dict), 'animation: očekáván objekt.')
    for key in ('dt', 'anim_timeout'):
        _require(_number(animation.get(key)) and animation[key] > 0, f'animation.{key}: musí být kladné číslo.')
    names = set()
    for index, style in enumerate(styles):
        label = style.get('name', f'#{index + 1}') if isinstance(style, dict) else f'#{index + 1}'
        try:
            _require(isinstance(style, dict), 'očekáván objekt')
            _require(isinstance(label, str) and label.strip() and 'name' in style, 'chybí name')
            _require(label not in names, 'duplicitní name')
            names.add(label)
            _require(style.get('mode', 'legacy_scroll') in ('legacy_scroll', 'stationary_hall', 'stationary_stream'), 'neznámý mode')
            for key in ('win', 'canvas', 'canvas.place', 'fonts'):
                _require(isinstance(style.get(key), dict), f'{key}: očekáván objekt')
            for section in ('win', 'canvas'):
                for key in ('width', 'height'):
                    if key in style[section]:
                        _require(type(style[section][key]) is int and style[section][key] > 0, f'{section}.{key}: musí být kladné celé číslo')
            for font, spec in style['fonts'].items():
                _require(isinstance(spec, dict), f'font {font}: očekáván objekt')
                for key in ('family', 'weight', 'slant'):
                    _require(isinstance(spec.get(key), str), f'font {font}.{key}: očekáván text')
                _require(type(spec.get('size')) is int and spec['size'] != 0, f'font {font}.size: neplatná velikost')
            sources = style.get('sources')
            _require(isinstance(sources, list) and sources, 'sources: očekáván neprázdný seznam')
            source_names = set()
            for source in sources:
                _require(isinstance(source, dict) and source.get('type') in ('long', 'short', 'short2'), 'sources: neznámý typ')
                source_names.add(source['type'])
                for key in ('repeat_start', 'repeat_end'):
                    _require(isinstance(source.get(key), str), f'sources.{key}: očekáván text')
            _require(isinstance(style.get('widgets'), list), 'widgets: očekáván seznam')
            for i, widget in enumerate(style['widgets']):
                _require(isinstance(widget, dict), f'widgets[{i}]: očekáván objekt')
                kind = widget.get('type')
                _require(kind in ('image', 'one_line', 'flow_lines', 'stanza_paged'), f'widgets[{i}].type: neznámý typ {kind!r}')
                for key in ('x', 'y'):
                    _require(_number(widget.get(key)), f'widgets[{i}].{key}: očekáváno číslo')
                if kind == 'image':
                    _require(widget.get('anchor') in ('n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw', 'center'), f'widgets[{i}].anchor: neplatné ukotvení')
                    _require(resource_path(widget.get('source'), root).is_file(), f'widgets[{i}].source: obrázek neexistuje: {widget.get("source")}')
                    if 'resize' in widget:
                        _require(isinstance(widget['resize'], list) and len(widget['resize']) == 2 and all(type(v) is int and v > 0 for v in widget['resize']), f'widgets[{i}].resize: očekávány dvě kladné velikosti')
                else:
                    _require(isinstance(widget.get('fill'), str), f'widgets[{i}].fill: očekávána barva')
                    _require(widget.get('source') in source_names, f'widgets[{i}].source: neznámý zdroj')
                    for key in ('primaryFont', 'secondaryFont'):
                        _require(widget.get(key) in style['fonts'], f'widgets[{i}].{key}: neznámý font')
                    for key in ('y1', 'y2'):
                        _require(_number(widget.get(key)), f'widgets[{i}].{key}: očekáváno číslo')
                    if 'lines_per_page' in widget:
                        _require(type(widget['lines_per_page']) is int and widget['lines_per_page'] > 0, f'widgets[{i}].lines_per_page: musí být kladné celé číslo')
                    if kind == 'flow_lines':
                        for key in ('gap', 'stp_in', 'stp_out'):
                            _require(_number(widget.get(key)), f'widgets[{i}].{key}: očekáváno číslo')
                        _require(widget.get('path') in ('linear', 'cubic', 'sinusoidal', 'poly5'), f'widgets[{i}].path: neznámá animační cesta')
                        _require(type(widget.get('path_steps')) is int and widget['path_steps'] > 0, f'widgets[{i}].path_steps: musí být kladné celé číslo')
            if 'collection' in style:
                cfg = style['collection']
                _require(isinstance(cfg, dict), 'collection: očekáván objekt')
                _require(resource_path(cfg.get('source'), root).is_file(), f'collection.source: obrázek neexistuje: {cfg.get("source")}')
                _require(type(cfg.get('size', 360)) is int and cfg.get('size', 360) > 0, 'collection.size: musí být kladné celé číslo')
                for key in ('relx', 'rely'):
                    _require(_number(cfg.get(key, 0.5)), f'collection.{key}: očekáváno číslo')
                _require(cfg.get('anchor', 'center') in ('n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw', 'center'), 'collection.anchor: neplatné ukotvení')
        except (ConfigError, TypeError) as exc:
            raise ConfigError(f'Styl „{label}“: {exc}') from exc
    return data


def monitor_labels(monitors, names=()):
    """Human labels follow desktop coordinates; hardware names stay untouched."""
    if not monitors:
        return []
    primary = next((i for i, m in enumerate(monitors) if getattr(m, 'is_primary', False)),
                   next((i for i, m in enumerate(monitors) if (m.x, m.y) == (0, 0)), 0))
    origin = monitors[primary]
    groups = {}
    directions = []
    for i, mon in enumerate(monitors):
        if i == primary:
            direction = 'Hlavní'
        else:
            horizontal = 'Vlevo' if mon.x < origin.x else 'Vpravo' if mon.x > origin.x else ''
            vertical = 'nahoře' if mon.y < origin.y else 'dole' if mon.y > origin.y else ''
            direction = ' '.join(part for part in (horizontal, vertical) if part).capitalize() or 'Stejná pozice'
        directions.append(direction)
        groups.setdefault(direction, []).append(i)
    labels = []
    for i, mon in enumerate(monitors):
        direction = directions[i]
        group = sorted(groups[direction], key=lambda idx: (monitors[idx].x, monitors[idx].y, idx))
        suffix = ''
        if len(group) > 1:
            axis = 'zleva' if direction.startswith(('Vlevo', 'Vpravo')) else 'shora'
            suffix = f' – {group.index(i) + 1}. {axis}'
        custom = next((entry['label'] for entry in names
                       if match_monitor(entry['monitor'], monitors) == i and entry['label']), '')
        labels.append(f'{custom or (direction + suffix)} ({mon.x}, {mon.y})')
    return labels


def monitor_identity(monitor):
    return {key: getattr(monitor, key, None) for key in ('name', 'x', 'y', 'width', 'height')}


def default_monitor(monitors):
    primary = next((i for i, m in enumerate(monitors) if getattr(m, 'is_primary', False)), 0)
    return next((i for i, m in enumerate(monitors) if getattr(m, 'is_primary', None) is False), primary)


def match_monitor(saved, monitors):
    """Do not guess when identical displays cannot be distinguished."""
    identities = [monitor_identity(m) for m in monitors]
    for keys in (('name', 'x', 'y', 'width', 'height'), ('name', 'width', 'height'), ('x', 'y', 'width', 'height')):
        if keys[0] == 'name' and not saved.get('name'):
            continue
        matches = [i for i, item in enumerate(identities)
                   if not (keys[0] == 'x' and saved.get('name') and item.get('name') and saved['name'] != item['name'])
                   and all(item[k] == saved[k] for k in keys)]
        if len(matches) == 1:
            return matches[0]
    return None


def _validate_monitor(monitor, prefix):
    _require(isinstance(monitor, dict), f'{prefix}: očekáván objekt.')
    _require(monitor.get('name') is None or isinstance(monitor.get('name'), str), f'{prefix}.name: očekáván text.')
    for key in ('x', 'y', 'width', 'height'):
        _require(type(monitor.get(key)) is int and (key in ('x', 'y') or monitor[key] > 0), f'{prefix}.{key}: neplatné celé číslo.')


def layout_row_limit(data, styles):
    """Migrate per-output draft settings to the shared hall capacity.

    Earlier per-output drafts used the lowest active hall limit. Retain that
    effective value on load; all later saves use the explicit shared setting.
    """
    if 'hall_max_rows' in data:
        value = data['hall_max_rows']
    else:
        hall_names = {s['name'] for s in styles if style_mode(s) == 'stationary_hall'}
        limits = [row_limits(output.get('lines_per_page', DEFAULT_HALL_ROWS))[0]
                  for output in data.get('outputs', []) if output.get('style') in hall_names]
        value = min(limits, default=DEFAULT_HALL_ROWS)
    return row_limits(value)[0]


def validate_layout(data, styles):
    _require(isinstance(data, dict) and type(data.get('version')) is int and data['version'] in (1, 2), 'Profil: nepodporovaná verze (podporovány 1 a 2).')
    try:
        row_limits(data.get('hall_max_rows', DEFAULT_HALL_ROWS))
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    if 'profile_name' in data:
        name = data['profile_name']
        _require(isinstance(name, str) and 0 < len(name.strip()) <= 80 and not any(ord(c) < 32 for c in name), 'Neplatný název profilu.')
    outputs = data.get('outputs')
    minimum = 1 if data['version'] == 1 else 0
    _require(isinstance(outputs, list) and minimum <= len(outputs) <= 5, f'Profil: outputs musí obsahovat {minimum} až 5 výstupů.')
    names = data.get('monitor_names', [])
    _require(isinstance(names, list), 'monitor_names: očekáván seznam.')
    for entry in names:
        _require(isinstance(entry, dict), 'monitor_names: očekáván objekt.')
        _require(isinstance(entry.get('label'), str) and len(entry['label']) <= 80 and not any(ord(c) < 32 for c in entry['label']), 'Název monitoru: nejvýše 80 znaků bez řídicích znaků.')
        _validate_monitor(entry.get('monitor'), 'monitor_names.monitor')
    for i, output in enumerate(outputs):
        prefix = f'Výstup {i + 1}'
        _require(isinstance(output, dict), f'{prefix}: očekáván objekt.')
        if 'collection_settings' in output:
            from .collection_qr import validate_settings
            try:
                validate_settings(output['collection_settings'])
            except ValueError as exc:
                raise ConfigError(f'{prefix}: {exc}') from exc
        _require(type(output.get('lines_per_page', DEFAULT_HALL_ROWS)) is int and output.get('lines_per_page', DEFAULT_HALL_ROWS) > 0, f'{prefix}: počet řádků musí být kladné celé číslo.')
        _require(output.get('style') in [s['name'] for s in styles], f'{prefix}: neznámý styl {output.get("style")!r}.')
        for key in ('fullscreen', 'collection'):
            _require(type(output.get(key)) is bool, f'{prefix}.{key}: očekáván boolean.')
        _validate_monitor(output.get('monitor'), f'{prefix}.monitor')
        position = output.get('window_position')
        _require(position is None or isinstance(position, list) and len(position) == 2 and all(type(v) is int for v in position), f'{prefix}.window_position: očekávána dvojice souřadnic nebo null.')
    return data


def load_layout(path, styles):
    return validate_layout(read_json(path), styles)


def save_layout(path, data, styles):
    validate_layout(data, styles)
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        temporary.replace(path)
    except OSError as exc:
        raise ConfigError(f'Nelze uložit {path}: {exc}') from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
