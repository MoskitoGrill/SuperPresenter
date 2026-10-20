"""Background stabilization with real Tk widgets and isolated user data."""
import logging
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from superpresenter.ui.main_window import GUI
from superpresenter.ui.projector_window import ProjWindow
from superpresenter.domain.song import Song
from superpresenter.services.song_repository import SongRepository
from superpresenter.logging_setup import configure_logging


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.enterContext(patch.object(GUI, 'init_profiles'))
        self.enterContext(patch.object(GUI, 'persist_layout'))
        self.enterContext(patch.object(GUI, 'start_monitor_watch'))
        monitor = SimpleNamespace(name='test', x=30000, y=30000, width=800, height=600, is_primary=True)
        self.enterContext(patch('superpresenter.ui.projection_profiles.get_monitors', return_value=[monitor]))
        self.error = self.enterContext(patch('superpresenter.ui.main_window.tkmsg.showerror'))
        original = tk.Tk
        def hidden_root():
            root = original()
            root.withdraw()
            return root
        self.enterContext(patch('superpresenter.ui.main_window.tk.Tk', side_effect=hidden_root))
        self.gui = GUI()
        self.addCleanup(self.destroy)
        self.gui.song_editor_widget.songs_dir = self.tmp.name
        for name, count in [('First', 10), ('Second', 6)]:
            song = Song.from_texts(name, {'cs': {'v1': '\n'.join(f'cs {i}' for i in range(count))},
                                         'en': {'v1': '\n'.join(f'en {i}' for i in range(count))}}, {'default': 'v1'})
            path = Path(self.tmp.name) / (name + '.xml')
            SongRepository().save(song, path)
            self.assertTrue(self.gui.loadSource(str(path)))

    def destroy(self):
        if self.gui.win.winfo_exists():
            if self.gui.runState:
                self.gui.runButtFun()
            self.gui.win.update_idletasks()
            self.gui.win.destroy()

    def configure_outputs(self, styles):
        self.gui.projectors = []
        for style in styles:
            projector = ProjWindow(self.gui)
            projector.style = style
            projector.fullscreen = False
            self.gui.projectors.append(projector)
        self.gui.projectorID = 0

    def test_all_shipped_styles_and_combined_stationary(self):
        for styles in ([0], [1], [0, 1], [2], [3], [4], [5]):
            with self.subTest(styles=styles):
                self.configure_outputs(styles)
                self.gui.runButtFun()
                self.assertTrue(self.gui.runState)
                for projector in self.gui.projectors:
                    self.assertTrue(projector.canvas.winfo_exists())
                for action in (self.gui.nextStep, self.gui.nextStep, self.gui.prevStep):
                    action()
                    self.gui.stepGoTo(0)
                self.gui.nextSlide()
                self.assertEqual(self.gui.runningSlide, 1)
                self.gui.prevSlide()
                self.assertEqual(self.gui.runningSlide, 0)
                self.gui.runButtFun()
                self.assertFalse(self.gui.onlineSources)
                self.error.assert_not_called()

    def test_sorter_cancel_and_commit_preserve_selected_song(self):
        gui = self.gui
        before = list(gui.sourceList)
        gui.sortSources()
        gui.sorter.positions.reverse()
        self.assertEqual(gui.sourceList, before)
        with patch('superpresenter.ui.main_window.tkmsg.askyesnocancel', return_value=False):
            gui.closeSorter()
        self.assertEqual(gui.sourceList, before)
        gui.sortSources()
        gui.sorter.positions.reverse()
        with patch('superpresenter.ui.main_window.tkmsg.askyesnocancel', return_value=True):
            gui.closeSorter()
        self.assertEqual(gui.sourceList, before[::-1])
        self.assertEqual(gui.sources[gui.sourceList[gui.sourceID]].song.title, 'Second')

    def test_start_failure_cleans_up_before_existing_error_handling(self):
        self.configure_outputs([0, 1])
        with patch.object(self.gui, 'previewSlide', side_effect=RuntimeError('preview failed')):
            with self.assertLogs('superpresenter.ui.main_window', level='ERROR'):
                with self.assertRaisesRegex(RuntimeError, 'preview failed'):
                    self.gui.runButtFun()
        self.assertFalse(self.gui.runState)
        self.assertFalse(self.gui.onlineSources)
        self.assertEqual(str(self.gui.openProjs['state']), 'normal')
        self.assertTrue(all(not hasattr(p, 'win') for p in self.gui.projectors))
        self.error.assert_not_called()
        self.gui.runButtFun()
        self.assertTrue(self.gui.runState)

    def test_close_during_projection_and_cancel_dirty_close(self):
        self.configure_outputs([0, 1])
        self.gui.runButtFun()
        self.gui.song_title.set('Dirty')
        with patch('song_editor.messagebox.askyesnocancel', return_value=None):
            self.gui.on_closing()
        self.assertTrue(self.gui.runState)
        with patch('song_editor.messagebox.askyesnocancel', return_value=False):
            self.gui.on_closing()
        self.assertFalse(self.gui.runState)
        self.assertTrue(all(not hasattr(p, 'win') for p in self.gui.projectors))
        self.gui.win = Mock(winfo_exists=Mock(return_value=False))

    def test_original_stream_last_pair_and_existing_song_transition(self):
        gui = self.gui
        self.configure_outputs([3])
        gui.runButtFun()
        self.assertTrue(gui.pair2_active)
        for expected in (1, 3, 5, 7, 9):
            gui.animation = 0
            gui.nextStep()
            gui.stepGoTo(0)
            self.assertEqual(gui.currentStep, expected)
            self.assertEqual(gui.runningSlide, 0)
        gui.animation = 0
        gui.nextStep()
        self.assertEqual(gui.runningSlide, 1)
        self.assertEqual(gui.currentStep, 0)  # No extra end/blank step added.
        gui.prevStep()
        self.assertEqual(gui.runningSlide, 0)
        self.assertEqual(gui.currentStep, 9)
        self.error.assert_not_called()

    def test_legacy_immediate_and_animation_send_identical_indices(self):
        gui = self.gui
        gui.pair2_active = True
        gui.pair2_map = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)]
        gui.onlineSources = [SimpleNamespace(lines={'short2steps': list(range(5)), 'longsteps': list(range(10))})]
        gui.runningSlide = 0
        gui.noOfSteps = 11
        gui.projectors = [Mock(switch=Mock(return_value=False))]
        for step, expected in [(0, (0, 0)), (3, (2, 3)), (9, (5, 9)), (11, (6, 11))]:
            gui.currentStep = step
            gui._update_projectors(0)
            gui.projectors[0].switch.assert_called_with(expected, 0)
            gui.animation = 1
            gui.animated = [0]
            gui.animmator()
            gui.projectors[0].switch.assert_called_with(expected, 1)

    def test_stop_cancels_pending_animation(self):
        self.configure_outputs([2])
        self.gui.runButtFun()
        self.gui.t = 0
        self.gui.nextStep()
        timer = self.gui._animation_timer
        self.assertIn(timer, self.gui.win.tk.call('after', 'info'))
        self.gui.runButtFun()
        self.assertNotIn(timer, self.gui.win.tk.call('after', 'info'))
        self.assertIsNone(self.gui._animation_timer)

    def test_language_selection_and_single_song(self):
        gui = self.gui
        gui.sourceList = [1]
        gui.sourceID = 0
        gui.viewSource()
        gui.var1Combo.set('en')
        gui.setVariant1()
        self.configure_outputs([0, 1])
        gui.runButtFun()
        self.assertEqual(len(gui.onlineSources), 1)
        gui.nextStep()
        self.assertTrue(all(line.text.startswith('en') for line in gui.stationary_navigation.cue.hall_page.lines))
        self.error.assert_not_called()

    def test_callback_failure_logs_without_new_dialog(self):
        self.configure_outputs([0])
        self.gui.runButtFun()
        error = RuntimeError('canvas failed')
        # tk.Tk is mocked only for construction; use the actual root's class here.
        with patch.object(type(self.gui.win), 'report_callback_exception') as fallback:
            with patch('superpresenter.ui.main_window.tk.Tk', type(self.gui.win)):
                with self.assertLogs('superpresenter.ui.main_window', level='ERROR'):
                    self.gui._report_callback_exception(type(error), error, None)
        self.assertFalse(self.gui.runState)
        fallback.assert_called_once()
        self.error.assert_not_called()

    def test_empty_title_save_reports_existing_validation(self):
        self.gui.song_title.set('')
        with patch('song_editor.messagebox.showerror') as error:
            with self.assertLogs('song_editor', level='ERROR'):
                self.assertFalse(self.gui.song_editor_widget.save_file())
        error.assert_called_once()
        self.assertTrue(self.gui.song_editor_widget.dirty)

    def test_original_stream_with_two_languages(self):
        gui = self.gui
        gui.var2Combo.set('en')
        gui.setVariant2()
        self.configure_outputs([3])
        gui.runButtFun()
        self.assertTrue(gui.runState)
        gui.nextSlide()
        self.assertEqual(tuple(gui.stepsLang['values']), ('cs', 'en'))
        gui.stepsLang.current(1)
        gui.stepsLangUpdate()
        gui.nextStep()
        gui.stepGoTo(0)
        self.error.assert_not_called()

    def test_legacy_repeated_rows_expand_before_pairing(self):
        source = self.gui.sources[0]
        source.repetitions = 'v1 (v1.10)*3'
        source.readInstructions()
        self.assertEqual(source.constructLines([{'type': 'long'}, {'type': 'short2'}]), ['cs'])
        actual = []
        for pair, first, second in zip(source.lines['short2pairmap'], *source.lines['short2']):
            actual.append(first)
            if pair[1] is not None:
                actual.append(second)
        self.assertEqual(actual[:10], source.lines['long'][0][:10])
        self.assertEqual(actual[10:], ['cs 9×3'] * 3)
        self.assertEqual(len(actual), len(source.lines['long'][0]))

    def test_late_preview_language_event_after_stop_is_safe(self):
        self.gui.stepsLangUpdate()
        self.error.assert_not_called()

    def test_presentation_editor_button_launches_v2(self):
        self.assertEqual(self.gui.openPresentation.cget('text'), 'prez')
        self.assertEqual(self.gui.openPresentation.winfo_manager(), 'grid')
        with patch('subprocess.Popen') as launch:
            launch.return_value.poll.return_value = None
            self.gui.openPresentation.invoke()
            self.gui.openPresentation.invoke()
        launch.assert_called_once()
        self.assertEqual(Path(launch.call_args.args[0][1]).name, 'presentation_presenter_v2.py')


class LoggingTests(unittest.TestCase):
    def test_utf8_file_idempotence_and_rotation(self):
        root = logging.getLogger()
        old_level = root.level
        with tempfile.TemporaryDirectory() as tmp:
            try:
                configure_logging(Path(tmp))
                configure_logging(Path(tmp))
                handlers = [h for h in root.handlers if getattr(h, '_superpresenter', False) is True]
                self.assertEqual(len(handlers), 1)
                handler = handlers[0]
                logging.getLogger(__name__).error('Píseň se nepodařilo uložit')
                handler.flush()
                self.assertIn('Píseň', (Path(tmp) / 'superpresenter.log').read_text(encoding='utf-8'))
                handler.doRollover()
                self.assertTrue((Path(tmp) / 'superpresenter.log.1').exists())
            finally:
                for handler in list(root.handlers):
                    if getattr(handler, '_superpresenter', False) is True:
                        root.removeHandler(handler)
                        handler.close()
                root.setLevel(old_level)
