"""Launch companion tools in source and standalone distributions."""
from pathlib import Path
import sys

from superpresenter.paths import PROJECT_ROOT


def tool_command(script):
    flags = {'presentation_presenter.py': '--presentation-editor',
             'presentation_presenter_v2.py': '--presentation-editor',
             'oprava_xml_tagu.py': '--repair-xml'}
    if script not in flags:
        raise ValueError('Unknown companion tool: ' + script)
    if getattr(sys, 'frozen', False):
        return [sys.executable, flags[script]]
    return [sys.executable, str(Path(PROJECT_ROOT) / script)]
