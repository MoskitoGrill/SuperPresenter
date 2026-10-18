"""Isolated PP9 snapshots, actual timer loop and larger-document timings.

Run each scaling in a fresh process. No user documents/preferences are written.
"""
from pathlib import Path
import sys
import tempfile
import time
import json
import ctypes
from ctypes import wintypes
from dataclasses import replace
import tkinter as tk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import ImageGrab
from presentationpresenter.domain import TextSection, TextBlock, TextRun
from presentationpresenter.projection import configure_dpi, Monitor
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow

configure_dpi()


def capture(widget, path):
    """Expose only our QA window; verify coverage before taking its crop."""
    widget.attributes('-topmost', True)
    widget.lift()
    widget.update()
    time.sleep(.15)
    widget.update()
    user = ctypes.windll.user32
    user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user.GetAncestor.restype = wintypes.HWND
    user.WindowFromPoint.argtypes = [wintypes.POINT]
    user.WindowFromPoint.restype = wintypes.HWND
    expected = user.GetAncestor(widget.winfo_id(), 2)
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    width, height = widget.winfo_width(), widget.winfo_height()
    for px, py in ((x+3,y+3), (x+width-4,y+3), (x+3,y+height-4), (x+width-4,y+height-4), (x+width//2,y+height//2)):
        assert user.GetAncestor(user.WindowFromPoint(wintypes.POINT(px, py)), 2) == expected, 'QA window is covered'
    ImageGrab.grab(bbox=(x, y, x+width, y+height)).save(path)
    widget.attributes('-topmost', False)
scale = int(sys.argv[1]) if len(sys.argv) > 1 else 100
out = Path(__file__).parent / 'previews'
with tempfile.TemporaryDirectory() as recovery:
    root = tk.Tk()
    root.tk.call('tk', 'scaling', scale / 75)
    errors = []
    root.report_callback_exception = lambda *args: errors.append(str(args))
    with patch('presentationpresenter.ui.monitors', return_value=[Monitor('QA', 0, 0, 1280, 900)]):
        w = MainWindow(root, AppSettings(), recovery_dir=recovery)
        root.after_cancel(w.autosave_job)
        w.autosave_job = None
        root.geometry('1100x720+10+10')
        root.update()
        w.projection_controls.fullscreen = dict(hall=False, stream=False)
        sections = tuple(TextSection(f'Úsek {n+1}', (TextBlock((TextRun('Český text pro kontrolu. '*12),)),), break_after=False, break_before=True) for n in range(100))
        started = time.perf_counter()
        w.commit(replace(w.document, sections=sections))
        w.rebuild()
        root.update()
        rebuild = time.perf_counter()-started
        started = time.perf_counter()
        for n in range(100):
            w.jump(n % len(w.plan.slides))
        navigate = time.perf_counter()-started
        assert not w.collect_preflight()
        assert w.start_projection(('hall', 'stream'))
        for window in w.projections.values():
            window.window.withdraw()
        w.playback.start(.1, True)
        initial = w.session.current_slide_id
        stop_at = time.monotonic()+.65
        while time.monotonic() < stop_at:
            root.update()
            time.sleep(.005)
        assert w.session.current_slide_id != initial
        w.toggle_blackout()
        paused = w.session.current_slide_id
        stop_at = time.monotonic()+.25
        while time.monotonic() < stop_at:
            root.update()
            time.sleep(.005)
        assert w.session.current_slide_id == paused and w.playback.job is None
        w.stop_projection()
        assert w.playback.job is None
        # A concrete report with both a section and a monitor problem.
        bad = TextSection('Příliš dlouhý název '*400, (TextBlock((TextRun('Obsah lze opravit v editoru.'),)),))
        w.commit(replace(w.document, sections=(sections[0], bad)))
        w.monitor_choices['hall'].set('Odpojený monitor')
        w.ribbon.show('Soubor')
        w.show_preflight()
        root.update()
        win = w.preflight_window.win
        win.geometry('860x480+30+30')
        root.update()
        capture(win, out/f'pp9-report-{scale}.png')
        assert w.preflight_window.go.winfo_rooty()+w.preflight_window.go.winfo_height() <= win.winfo_rooty()+win.winfo_height(), 'Report actions clipped'
        assert w.preflight_window.tree.bbox('0')[3] >= int(root.tk.call('font', 'metrics', w.appearance.text, '-linespace')), 'Report rows clipped'
        win.destroy()
        w.undo()
        w.rebuild()
        w.ribbon.show('Nastavení')
        root.geometry('920x650+10+10')
        root.update()
        capture(root, out/f'pp9-settings-{scale}.png')
        assert w.text.winfo_height() > 1, 'Editor is inaccessible'
        assert w.location_label.winfo_reqwidth() >= w.navigation_layout.counter_font.measure('99999/99999')+2
        print(json.dumps(dict(scale=scale, sections=100, slides=len(w.plan.slides), rebuild_seconds=round(rebuild, 3), navigation_100_seconds=round(navigate, 3), window=[root.winfo_width(),root.winfo_height()], editor=[w.text.winfo_width(), w.text.winfo_height()], callback_errors=errors)))
        root.destroy()
        assert not errors
