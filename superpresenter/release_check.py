"""Opt-in packaged GUI smoke test; all writes use isolated temporary data."""
import os
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace

from superpresenter.paths import PROJECT_ROOT
from superpresenter.version import VERSION, RELEASE_STAGE


def run_check():
    import tkinter as tk
    from tkinter import messagebox
    from tkinterdnd2 import TkinterDnD
    from superpresenter.domain.song import Song
    from superpresenter.services.song_repository import SongRepository
    from superpresenter.ui.main_window import GUI
    from superpresenter.ui.projector_window import ProjWindow
    from superpresenter.windows_shell import _set_properties

    root = Path(PROJECT_ROOT)
    errors = []
    original_tk = tk.Tk
    original_error = messagebox.showerror
    original_appdata = os.environ.get('APPDATA')

    def hidden_tk(*args, **kwargs):
        win = original_tk(*args, **kwargs)
        win.withdraw()
        return win

    def fail_dialog(title, message, **kwargs):
        raise RuntimeError(str(title) + ': ' + str(message))

    with tempfile.TemporaryDirectory(prefix='SuperPresenter-check-') as temp:
        os.environ['APPDATA'] = temp
        tk.Tk = hidden_tk
        messagebox.showerror = fail_dialog
        gui = None
        try:
            gui = GUI()
            gui.stop_monitor_watch()
            gui.win.report_callback_exception = lambda *exc: errors.append(str(exc[1]))
            gui.win.update_idletasks()
            _set_properties(gui.win.winfo_id(), root, root / 'images' / 'launcher-default.ico')
            gui.win.iconbitmap(str(root / 'images' / 'launcher-default.ico'))
            assert Path(gui.song_editor_widget.songs_dir) == root / 'songs'
            repo = SongRepository()
            song = Song.from_texts('Release check', {'cs': {'v1': 'První řádek\nDruhý řádek'}}, {'default': 'v1'})
            path = Path(temp) / 'Zkušební píseň.xml'
            repo.save(song, path)
            assert gui.loadSource(str(path))
            gui._profiles_ready = False
            gui.monitors = [SimpleNamespace(name='check', x=30000, y=30000,
                                           width=800, height=600, is_primary=True)]
            tested_styles = []
            for index, style in enumerate(gui.projStyles):
                projector = ProjWindow(gui)
                projector.style = index
                projector.fullscreen = False
                gui.projectors = [projector]
                gui.projectorID = 0
                gui.runButtFun()
                assert gui.runState and projector.canvas.winfo_exists()
                gui.win.update_idletasks()
                gui.nextStep()
                gui.prevStep()
                gui.runButtFun()
                tested_styles.append(style['name'])
            assert not errors, errors
            tcl_version = gui.win.tk.call('info', 'patchlevel')
            gui.win.destroy()
            gui = None
            tk.Tk = original_tk
            # Execute the legacy file with its real data-root __file__, as the
            # packaged --presentation-editor command does, without mainloop.
            legacy = runpy.run_path(str(root / 'presentation_presenter.py'))
            dnd = TkinterDnD.Tk()
            dnd.withdraw()
            try:
                legacy['PresentationEditor'](dnd)
                dnd.update_idletasks()
                assert dnd.tk.call('package', 'require', 'tkdnd')
            finally:
                dnd.destroy()
            return {'ok': True, 'version': VERSION, 'stage': RELEASE_STAGE,
                    'root': str(root), 'tcl': tcl_version,
                    'styles': tested_styles, 'song_roundtrip': True,
                    'presentation_editor': True, 'taskbar_properties': True,
                    'song_files': len(list((root / 'songs').rglob('*.xml')))}
        finally:
            if gui is not None:
                gui.win.destroy()
            tk.Tk = original_tk
            messagebox.showerror = original_error
            if original_appdata is None:
                os.environ.pop('APPDATA', None)
            else:
                os.environ['APPDATA'] = original_appdata
