"""Isolated PP8L screenshots and measurements; never saves user preferences."""
from pathlib import Path
import sys
import tempfile
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import ImageGrab
from presentationpresenter.domain import TextSection, TextBlock, TextRun
from presentationpresenter.projection import configure_dpi
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow

configure_dpi()
out = Path(__file__).parent / 'previews'
with tempfile.TemporaryDirectory() as recovery:
    root = tk.Tk()
    if len(sys.argv) > 1:
        root.tk.call('tk', 'scaling', float(sys.argv[1]) / 75)
    app = MainWindow(root, AppSettings(), recovery_dir=recovery)
    root.after_cancel(app.autosave_job)
    app.autosave_job = None
    app.text.insert('1.0', 'Neboť tak Bůh miluje svět, že dal svého jediného Syna.\nZde lze pohodlně upravovat text prezentace.')
    app.title.set('Jan 3:16 (CSP)')
    app.rebuild()

    def capture(name, width, height, tab, collapsed=False):
        root.geometry(f'{width}x{height}+25+25')
        app.ribbon.show(tab)
        if collapsed:
            app.ribbon.toggle()
        root.update()
        if len(sys.argv) > 1:
            name = 'scale-'+sys.argv[1]+'-'+name
        ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(),
                            root.winfo_rootx()+root.winfo_width(),
                            root.winfo_rooty()+root.winfo_height())).save(out/name)
        print(name, 'window', root.winfo_width(), root.winfo_height(),
              'preview', app.preview.winfo_width(), app.preview.winfo_height(),
              'text', app.text.winfo_width(), app.text.winfo_height())

    capture('pp8l-home.png', 1280, 900, 'Domů')
    capture('pp8l-small.png', 1024, 768, 'Domů')
    capture('pp8l-collapsed.png', 1100, 720, 'Domů', True)
    # Long list without producing many expensive intermediate layouts.
    from dataclasses import replace
    sections = tuple(TextSection(title=f'Úsek {i+1}', blocks=(TextBlock(runs=(TextRun(f'Obsah {i+1}'),)),)) for i in range(30))
    app.document = replace(app.document, sections=sections)
    app.selected_id = sections[0].id
    app.refresh_sections()
    app.load_editor()
    app.rebuild()
    capture('pp8l-sections.png', 1280, 900, 'Úseky')
    capture('pp8l-sections-small.png', 1024, 768, 'Úseky')
    app.sections.yview_moveto(1)
    root.update()
    assert app.sections.yview()[0] > 0
    root.destroy()
