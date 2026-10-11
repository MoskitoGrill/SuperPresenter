"""Stage 13A controls tested with real Tk widgets and temporary songs."""
import unittest
import tkinter as tk
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import test_release_stability as release
from superpresenter.services.song_repository import SongRepository
from superpresenter.services.stationary_navigation import CueNavigation


class ControlsTests(unittest.TestCase):
    setUp = release.ReleaseTests.setUp
    destroy = release.ReleaseTests.destroy
    configure_outputs = release.ReleaseTests.configure_outputs

    def test_dirty_caption_save_and_xml_title(self):
        gui = self.gui
        editor = gui.song_editor_widget
        self.assertEqual(gui.sourceLab['text'], 'Second')
        editor.sections[0]['widget'].insert('end', ' edited')
        gui.win.update()
        self.assertEqual(gui.sourceLab['text'], 'Second *')
        self.assertEqual(gui.dirtyLabel['text'], ' *')
        self.assertTrue(editor.save_file())
        self.assertEqual(gui.sourceLab['text'], 'Second')
        self.assertEqual(gui.dirtyLabel['text'], '')
        self.assertEqual(SongRepository().load(editor.file_path).title, 'Second')

    def test_discard_draft_and_recovery_caption(self):
        gui = self.gui
        editor = gui.song_editor_widget
        gui.song_title.set('Changed')
        with patch('song_editor.messagebox.askyesnocancel', return_value=False):
            gui.prevSourceFun()
        self.assertEqual(gui.sourceLab['text'], 'First')
        gui.newSongFun()
        gui.song_title.set('Draft')
        self.assertEqual(gui.sourceLab['text'], 'Draft *')
        clean = deepcopy(editor.session.clean_song)
        restored = editor.snapshot()
        editor.session.song = restored
        editor._render_song()
        gui.on_editor_restored(restored, clean, None)
        self.assertEqual(gui.sourceLab['text'], 'Draft *')
        with patch('song_editor.messagebox.askyesnocancel', return_value=False):
            editor.confirm_transition()
        self.assertEqual(gui.dirtyLabel['text'], '')

    def test_scrollbar_both_directions_and_manual_scroll(self):
        gui = self.gui
        # Tk delivers scrollbar fractions when the Listbox is mapped.
        gui.win.geometry('+30000+30000')
        gui.win.deiconify()
        gui.win.update()
        gui.stepsList.insert('end', 'long ' * 200)
        gui.win.update_idletasks()
        self.assertEqual(str(gui.stepsXScroll['orient']), 'horizontal')
        self.assertEqual(str(gui.stepsScroll['orient']), 'vertical')
        gui.win.tk.call(gui.stepsXScroll['command'], 'moveto', 1)
        self.assertGreater(gui.stepsList.xview()[0], 0)
        gui.win.update_idletasks()
        self.assertAlmostEqual(gui.stepsXScroll.get()[0], gui.stepsList.xview()[0])
        self.assertAlmostEqual(gui.stepsList.xview()[1], 1)

    def test_counter_and_reset_all_modes(self):
        gui = self.gui
        for styles in ([0], [1], [0, 1], [2], [3], [4], [5]):
            with self.subTest(styles=styles):
                self.configure_outputs(styles)
                gui.runButtFun()
                total = (gui.stationary_navigation.last_step - 1 if gui.stationary_active else
                         len(gui.pair2_map) if gui.pair2_active else
                         len(gui.paged_starts) if gui.paged_active else gui.noOfSteps - 1)
                self.assertEqual(gui.stepsLabel['text'], f'0 / {total}')
                with patch.object(gui.stepsList, 'xview_moveto', wraps=gui.stepsList.xview_moveto) as reset:
                    for index in range(1, total + 1):
                        gui.animation = 0
                        gui.nextStep()
                        gui.stepGoTo(0)
                        self.assertEqual(gui.stepsLabel['text'], f'{index} / {total}')
                        reset.assert_called_with(0)
                    gui.animation = 0
                    gui.prevStep()
                    reset.assert_called_with(0)
                    reset.reset_mock()
                    gui.stepsLangUpdate()
                    reset.assert_called_with(0)
                    reset.reset_mock()
                    if gui.stationary_active:
                        gui._stationary_select_row(len(gui.cue_rows) - 1)
                    else:
                        gui.stepsList.selection_clear(0, 'end')
                        gui.stepsList.selection_set(gui.noOfSteps)
                        gui.stepSelect(None)
                    self.assertEqual(gui.stepsLabel['text'], 'Konec')
                    reset.assert_called_with(0)
                    reset.reset_mock()
                    gui.nextSlide()
                    reset.assert_called_with(0)
                gui.runButtFun()

    def test_empty_song_boundaries(self):
        gui = self.gui
        gui.stationary_active = True
        gui.stationary_navigation = CueNavigation([SimpleNamespace(cues=())])
        gui.stepUpdate()
        self.assertEqual(gui.stepsLabel['text'], '0 / 0')
        gui.stationary_navigation.move(1)
        gui.stepUpdate()
        self.assertEqual(gui.stepsLabel['text'], 'Konec')
        gui.stationary_active = False
        for pair, paged in ((False, False), (True, False), (False, True)):
            gui.pair2_active, gui.paged_active = pair, paged
            gui.pair2_map = []
            gui.paged_starts = []
            gui.noOfSteps = 1
            gui.currentStep = 0
            gui.stepUpdate()
            self.assertEqual(gui.stepsLabel['text'], '0 / 0')
            gui.currentStep = 1
            gui.stepUpdate()
            self.assertEqual(gui.stepsLabel['text'], 'Konec')

    def test_layout_and_dynamic_repetitions(self):
        gui = self.gui
        editor = gui.song_editor_widget
        order = editor.root.pack_slaves()
        self.assertLess(order.index(editor.canvas.master), order.index(editor.section_buttons_frame))
        self.assertLess(order.index(editor.section_buttons_frame), order.index(editor.repetition_container))
        self.assertLess(order.index(editor.repetition_container), order.index(editor.explain_label))
        save_frame = order[order.index(editor.explain_label) + 1]
        self.assertTrue(any(w.cget('text') == 'Uložit' for w in save_frame.winfo_children()))
        editor.add_repetition('extra', 'v1')
        self.assertEqual(order, editor.root.pack_slaves())
        editor.remove_repetition('extra', editor.repetition_frames['extra'])
        self.assertEqual(order, editor.root.pack_slaves())
        self.assertIs(gui.addSlokaBtn.master, editor.section_buttons_frame)
        self.assertEqual(gui.addLangBtn['text'], 'Přidat variantu')
        self.assertIs(gui.addLangBtn.master, gui.variants)
        self.assertEqual(gui.addLangBtn.grid_info()['row'], gui.var2Combo.grid_info()['row'])
        self.assertEqual(str(gui.dirtyLabel.winfo_manager()), 'grid')

    def test_lock_restore_and_error_cleanup(self):
        gui = self.gui
        self.configure_outputs([0])
        gui.addProj.configure(state='disabled')
        widgets = [gui.loadProjs, gui.saveProjs, gui.chooseProj,
                   gui.chooseStyle, gui.addProj]
        states = [str(w['state']) for w in widgets]
        gui.runButtFun()
        self.assertTrue(all(str(w['state']) == 'disabled' for w in widgets))
        for widget in (gui.sourceTitleEntry, gui.addSlokaBtn, gui.addLangBtn,
                       gui.var1Combo, gui.openSource, gui.closeSource, gui.changeOrder,
                       gui.nextBtn, gui.stepsList, gui.openProjs, gui.collectionCheck, gui.fullscreenCheck):
            self.assertNotEqual(str(widget['state']), 'disabled')
        with patch.object(gui.song_editor_widget, 'save_file') as save:
            gui.song_editor_widget._save_shortcut()
            save.assert_called_once()
        gui.runButtFun()
        self.assertEqual([str(w['state']) for w in widgets], states)
        with patch.object(gui, 'previewSlide', side_effect=RuntimeError('failure')):
            with self.assertLogs('superpresenter.ui.main_window', level='ERROR'):
                with self.assertRaises(RuntimeError):
                    gui.runButtFun()
        self.assertFalse(gui.runState)
        self.assertEqual([str(w['state']) for w in widgets], states)

    def test_edits_save_variants_and_order_only_affect_next_run(self):
        gui = self.gui
        self.configure_outputs([0])
        gui.runButtFun()
        running = deepcopy([source.song for source in gui.onlineSources])
        plans = gui.stationary_navigation.plans
        editor = gui.song_editor_widget
        editor.sections[0]['widget'].insert('end', ' corrected')
        gui.win.update()
        self.assertTrue(editor.save_file())
        self.assertIn('corrected', SongRepository().load(editor.file_path).variant_texts['cs']['v1'])
        gui.var1Combo.set('en')
        gui.setVariant1()
        self.assertEqual(gui.sources[gui.sourceList[gui.sourceID]].variants[0], 'en')
        gui.sortSources()
        gui.sorter.positions.reverse()
        with patch('superpresenter.ui.main_window.tkmsg.askyesnocancel', return_value=True):
            gui.closeSorter()
        self.assertEqual([source.song for source in gui.onlineSources], running)
        self.assertIs(gui.stationary_navigation.plans, plans)
        gui.nextStep()
        gui.runButtFun()
        gui.runButtFun()
        self.assertIn('corrected', gui.onlineSources[0].song.variant_texts['cs']['v1'])

    def test_callback_error_restores_controls(self):
        gui = self.gui
        self.configure_outputs([0])
        gui.chooseStyle.configure(state='readonly')
        gui.runButtFun()
        error = RuntimeError('callback failure')
        with patch('tkinter.Tk.report_callback_exception'), self.assertLogs(
                'superpresenter.ui.main_window', level='ERROR'):
            gui._report_callback_exception(type(error), error, None)
        self.assertFalse(gui.runState)
        self.assertEqual(str(gui.sourceTitleEntry['state']), 'normal')
        self.assertEqual(str(gui.chooseStyle['state']), 'readonly')

    def test_compact_width_and_button_spacing(self):
        gui = self.gui
        gui.win.geometry('+30000+30000')
        gui.win.deiconify()
        gui.win.update()
        editor = gui.song_editor_widget
        self.assertLessEqual(gui.rightFrame.winfo_reqwidth(), 850)
        self.assertGreaterEqual(editor.section_buttons_frame.winfo_y() -
                                (editor.canvas.master.winfo_y() + editor.canvas.master.winfo_height()), 20)
        self.assertGreaterEqual(gui.addLangBtn.winfo_x() -
                                (gui.var2Combo.winfo_x() + gui.var2Combo.winfo_width()), 20)

    def test_fullscreen_toggle_keeps_running_plan_and_canvas(self):
        gui = self.gui
        self.configure_outputs([0])
        gui.projectors[0].fullscreen = True
        gui.fullscreenState.set(True)
        gui.runButtFun()
        proj = gui.projectors[0]
        canvas = proj.canvas
        plans = gui.stationary_navigation.plans
        self.assertNotEqual(str(gui.fullscreenCheck['state']), 'disabled')
        gui.fullscreenCheck.invoke()
        gui.win.update_idletasks()
        self.assertFalse(proj.win.overrideredirect())
        self.assertLess(proj.win.winfo_width(), gui.monitors[proj.monitor].width)
        windowed = proj.win.geometry()
        gui.fullscreenCheck.invoke()
        gui.win.update_idletasks()
        self.assertTrue(proj.win.overrideredirect())
        gui.fullscreenCheck.invoke()
        gui.win.update_idletasks()
        self.assertEqual(proj.win.geometry(), windowed)
        self.assertIs(proj.canvas, canvas)
        self.assertIs(gui.stationary_navigation.plans, plans)
        self.assertTrue(gui.runState)
        from tkinter import font
        label_font = font.Font(root=gui.win, font=gui.addLangBtn['font'])
        self.assertGreaterEqual(gui.addLangBtn.winfo_reqwidth(),
                                label_font.measure(gui.addLangBtn['text']) + 10)
