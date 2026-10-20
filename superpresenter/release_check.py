"""Opt-in packaged GUI smoke test; all writes use isolated temporary data."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

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
            gui.win.createcommand('record_bgerror', errors.append)
            gui.win.tk.eval('proc bgerror {message} {record_bgerror $message}')
            gui.win.update_idletasks()
            _set_properties(gui.win.winfo_id(), root, root / 'images' / 'launcher-default.ico')
            gui.win.iconbitmap(str(root / 'images' / 'launcher-default.ico'))
            assert Path(gui.song_editor_widget.songs_dir) == root / 'songs'
            repo = SongRepository()
            song = Song.from_texts('Release check', {'cs': {'v1': '\n'.join(
                f'Zkušební řádek {i}' for i in range(10))}}, {'default': 'v1'})
            path = Path(temp) / 'Zkušební píseň.xml'
            repo.save(song, path)
            assert gui.loadSource(str(path))
            gui.song_editor_widget.songs_dir = temp
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
                for _ in range(20):
                    gui.nextStep()
                    gui.prevStep()
                    gui.win.update()
                # Real editor save changes only the temporary fixture. The
                # running source must remain an independent snapshot.
                snapshot = gui.onlineSources[0].song.title
                gui.song_title.set(f'Release check edited {index}')
                with patch.object(messagebox, 'askyesnocancel', return_value=True):
                    assert gui.song_editor_widget.save_file()
                assert gui.onlineSources[0].song.title == snapshot
                gui.runButtFun()
                assert not gui.onlineSources and not hasattr(projector, 'win')
                for _ in range(3):
                    gui.runButtFun()
                    assert gui.runState
                    gui.runButtFun()
                    assert not gui.runState and not hasattr(projector, 'canvas')
                tested_styles.append(style['name'])
            rejected = []
            for index in (0, 2):
                projector.style = index
                with patch.object(gui, '_prepare_song_transition', return_value=True), \
                     patch.object(gui, 'saveRepetitions'), \
                     patch.object(messagebox, 'showerror', side_effect=lambda title, msg: rejected.append(msg)):
                    for guide in ('(v1)*4097', '(v1)*410', 'v1 ???'):
                        gui.sources[0].repetitions = guide
                        gui.runButtFun()
                        assert not gui.runState and not hasattr(projector, 'win')
                        assert str(gui.openProjs.cget('state')) == 'normal'
                        gui.sources[0].repetitions = 'v1'
                        gui.runButtFun()
                        assert gui.runState
                        gui.runButtFun()
            assert len(rejected) == 6, rejected
            gui.runButtFun()
            assert gui.runState
            tcl_version = gui.win.tk.call('info', 'patchlevel')
            gui.on_closing()
            assert not gui.runState and not hasattr(projector, 'win')
            assert not errors, errors
            gui = None
            tk.Tk = original_tk
            # Exercise the current companion used by --presentation-editor.
            from presentationpresenter.ui import MainWindow
            from presentationpresenter.settings import AppSettings
            dnd = TkinterDnD.Tk()
            dnd.withdraw()
            try:
                presenter = MainWindow(dnd, AppSettings(), recovery_dir=Path(temp) / 'presentation-recovery')
                dnd.update_idletasks()
                assert presenter.plan.slides
                assert dnd.tk.call('package', 'require', 'tkdnd')
            finally:
                dnd.destroy()
            return {'ok': True, 'version': VERSION, 'stage': RELEASE_STAGE,
                    'root': str(root), 'tcl': tcl_version,
                    'styles': tested_styles, 'song_roundtrip': True,
                    'presentation_editor': True, 'presentation_editor_version': 2, 'taskbar_properties': True,
                    'start_stop_cycles': 31, 'rapid_navigation_pairs': 120,
                    'edit_during_projection': True, 'invalid_inputs_rejected': len(rejected),
                    'close_during_projection': True, 'callback_errors': errors,
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
