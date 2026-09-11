"""13B uses real Tk and the existing validated song transition."""
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import test_release_stability as release
from superpresenter.domain.song import Song
from superpresenter.services.song_repository import SongRepository
from superpresenter.ui.song_search_window import add_result, in_playlist


class SearchWindowTests(unittest.TestCase):
    setUp = release.ReleaseTests.setUp
    destroy = release.ReleaseTests.destroy
    configure_outputs = release.ReleaseTests.configure_outputs

    def new_path(self):
        path = Path(self.tmp.name) / 'third.xml'
        SongRepository().save(Song.from_texts('Third', {'cs': {'v1': 'třetí píseň'}}, {'default': 'v1'}), path)
        return path

    def test_add_duplicate_and_cancel_dirty(self):
        gui = self.gui
        path = self.new_path()
        gui.song_title.set('Dirty')
        before = list(gui.sourceList)
        with patch('song_editor.messagebox.askyesnocancel', return_value=None):
            self.assertEqual(add_result(gui, path), 'Píseň nebyla přidána.')
        self.assertEqual(gui.sourceList, before)
        self.assertTrue(gui.song_editor_widget.dirty)
        with patch('song_editor.messagebox.askyesnocancel', return_value=False):
            self.assertEqual(add_result(gui, path), 'Přidáno do playlistu.')
        self.assertTrue(in_playlist(gui, path))
        with patch.object(gui, 'loadSource') as load:
            self.assertEqual(add_result(gui, path), 'Píseň už je v playlistu.')
            load.assert_not_called()
        self.assertEqual(len(gui.sourceList), len(before) + 1)

    def test_running_policy_keeps_projection_snapshot(self):
        gui = self.gui
        self.configure_outputs([0])
        gui.runButtFun()
        snapshot = deepcopy([source.song for source in gui.onlineSources])
        plans = gui.stationary_navigation.plans
        self.assertEqual(str(gui.chooseStyle['state']), 'disabled')
        self.assertNotEqual(str(gui.openSource['state']), 'disabled')
        self.assertEqual(add_result(gui, self.new_path()), 'Přidáno do playlistu.')
        self.assertEqual([source.song for source in gui.onlineSources], snapshot)
        self.assertIs(gui.stationary_navigation.plans, plans)

    def test_window_add_and_reopen_refresh(self):
        gui = self.gui
        production = Path(self.tmp.name) / 'songs'
        production.mkdir()
        gui.dir = Path(self.tmp.name)
        path = production / 'third.xml'
        song = Song.from_texts('Third', {'cs': {'v1': 'třetí píseň'}}, {'default': 'v1'})
        SongRepository().save(song, path)
        gui.openSource.invoke()
        window = gui._song_search_window
        window.future.result(timeout=10)
        window.check_index()
        self.assertEqual(tuple(window.tree['columns']), ('title', 'snippet'))
        self.assertEqual(window.win['background'], gui.win['background'])
        self.assertEqual(window.entry['background'], gui.sourceTitleEntry['background'])
        self.assertEqual(window.add_button['background'], gui.openSource['background'])
        from tkinter import ttk, font
        style = ttk.Style(window.win)
        self.assertGreaterEqual(int(style.lookup(window.tree['style'], 'rowheight')),
                                2 * font.Font(root=window.win, font=gui.stepsList['font']).metrics('linespace'))
        window.query.set('treti')
        window.search()
        self.assertEqual(len(window.results), 1)
        window.tree.selection_set('0')
        window.add_button.configure(state='normal')
        window.add_button.invoke()
        self.assertTrue(in_playlist(gui, path))
        self.assertIn('(v playlistu)', window.tree.item('0', 'values')[0])
        gui.song_editor_widget.sections[0]['widget'].insert('end', ' změněno')
        gui.win.update()
        self.assertTrue(gui.song_editor_widget.save_file())
        window.close()
        gui.openSource.invoke()
        window = gui._song_search_window
        window.future.result(timeout=10)
        window.check_index()
        window.query.set('zmeneno')
        window.search()
        self.assertEqual(len(window.results), 1)
        self.assertEqual(gui.openPresentation['text'], 'prez')
        self.assertEqual(gui.openSource['text'], '+')
        self.assertFalse(hasattr(gui, 'searchSource'))
        self.assertEqual(window.browse_button['text'], '+')
        self.assertGreater(window.browse_button.grid_info()['column'], window.entry.grid_info()['column'])
        with patch('superpresenter.ui.main_window.filedialog.askopenfilenames', return_value=(str(path),)) as picker, patch.object(gui, 'loadSource', return_value=True) as load:
            window.browse_button.invoke()
            picker.assert_called_once()
            load.assert_called_once_with(str(path))
        window.close()

    def test_validation_failure(self):
        path = Path(self.tmp.name) / 'invalid.xml'
        path.write_text('<slide name="Invalid"/>')
        before = list(self.gui.sourceList)
        self.assertEqual(add_result(self.gui, path), 'Píseň nebyla přidána.')
        self.assertEqual(self.gui.sourceList, before)
        self.error.assert_called()
