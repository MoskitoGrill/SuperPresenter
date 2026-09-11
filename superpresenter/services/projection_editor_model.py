"""Draft conversion for the monitor editor, independent of Tk."""
from copy import deepcopy
from superpresenter.services.projection_config import (
    match_monitor, monitor_identity, validate_layout,
)


def editor_cards(layout, monitors):
    cards = []
    for index, monitor in enumerate(monitors):
        rows = [deepcopy(output) for output in layout['outputs']
                if match_monitor(output['monitor'], monitors) == index]
        name = next((entry['label'] for entry in layout.get('monitor_names', [])
                     if match_monitor(entry['monitor'], monitors) == index), '')
        cards.append(dict(label=name, outputs=rows[:1] or [dict(
            style=None, fullscreen=True, collection=False, window_position=None)]))
    return cards


def layout_from_cards(cards, monitors, styles, previous_names=(), previous_outputs=()):
    # Retain names of currently disconnected monitors for later reconnection.
    names = [deepcopy(entry) for entry in previous_names
             if match_monitor(entry['monitor'], monitors) is None]
    outputs = [deepcopy(output) for output in previous_outputs
               if match_monitor(output['monitor'], monitors) is None]
    for card, monitor in zip(cards, monitors):
        identity = monitor_identity(monitor)
        names.append(dict(monitor=identity, label=card['label'].strip()))
        for row in card['outputs']:
            if row['style'] is not None:
                output = deepcopy(row)
                output['monitor'] = identity
                outputs.append(output)
    return validate_layout(dict(version=2, outputs=outputs, monitor_names=names), styles)
