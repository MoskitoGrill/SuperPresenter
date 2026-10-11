"""Bounded real-Tk refresh comparison with HEAD's pre-stage-3 search loop."""
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'tests'))
from test_release_stability import ReleaseTests
from superpresenter.ui.song_search_window import SongSearchWindow

baseline = {'__name__': 'stage3_baseline'}
exec(compile(subprocess.check_output(
    ['git', 'show', 'HEAD:superpresenter/ui/song_search_window.py']).decode('utf-8'),
    '<HEAD song_search_window>', 'exec'), baseline)
fixture = ReleaseTests()
try:
    fixture.setUp()
    gui = fixture.gui
    window = SongSearchWindow(gui)
    fixture.addCleanup(window.close)
    window.future.result(timeout=10)
    window.check_index()
    # 100 results and 100 playlist positions, including duplicate source indices.
    gui.sources = [SimpleNamespace(path=Path(fixture.tmp.name) / f'{i}.xml') for i in range(50)]
    gui.sourceList = list(range(50)) * 2
    results = [SimpleNamespace(path=Path(fixture.tmp.name) / f'{i}.xml',
                               display_title=f'Song {i}', snippet='sample') for i in range(100)]
    samples = {'before': [], 'after': []}
    with patch.object(window.search_index, 'search', return_value=results):
        for iteration in range(8):
            order = [('before', baseline['SongSearchWindow'].search),
                     ('after', SongSearchWindow.search)]
            if iteration % 2:
                order.reverse()
            for label, refresh in order:
                start = time.perf_counter()
                refresh(window)
                gui.win.update_idletasks()
                elapsed = (time.perf_counter() - start) * 1000
                if iteration:
                    samples[label].append(elapsed)
    print('Python:', sys.version.split()[0], 'OS:', os.name)
    print('100 results; 50 unique sources, 100 playlist positions; real Tk insert + idle layout;')
    print('index/search mocked identically; 1 warm-up + 7 alternating samples, milliseconds')
    for label, values in samples.items():
        print(label, 'median=', round(statistics.median(values), 3),
              'range=', tuple(round(v, 3) for v in (min(values), max(values))))
finally:
    fixture.doCleanups()
