import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch, Mock

from song_editor import SongEditor, add_title_placeholder
from superpresenter.services.song_recovery import SongRecovery
from super_presenter import GUI, WidgetSource
from superpresenter.domain.song import Song, SongSection, SongVariant
from superpresenter.services.song_repository import SongRepository, SongLoadError, SongSaveError


class EditorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update_idletasks)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.error = self.enterContext(patch('song_editor.messagebox.showerror'))
        self.enterContext(patch('super_presenter.tkmsg.showwarning'))
        self.choice = self.enterContext(patch('song_editor.messagebox.askyesnocancel', return_value=None))
        self.overwrite = self.enterContext(patch('song_editor.messagebox.askyesno', return_value=False))
        self.overwrite.side_effect = lambda title, *args, **kwargs: True if title == 'Vynechané sekce v opakování' else self.overwrite.return_value
        self.song = Song.from_texts('Original', {'cs': {'v1': 'One', 'v2': 'Two'}}, {'default': 'v1 v2', 'short': 'v2'}, 'short')
        self.path = Path(self.tmp.name) / 'original.xml'
        SongRepository().save(self.song, self.path)
        self.editor = SongEditor(self.root, embedded=True)
        self.editor.songs_dir = self.tmp.name
        self.editor.load_file_from_path(self.path)

    def test_load_clean_and_programmatic_text_changes_dirty(self):
        self.root.update()
        self.assertFalse(self.editor.dirty)
        self.editor.sections[0]['widget'].insert('end', ' changed')
        self.root.update()
        self.assertTrue(self.editor.dirty)
        self.assertTrue(self.editor.status_variable.get())

    def test_fixed_window_and_horizontal_overflow_when_switching_songs(self):
        self.root.geometry('700x700')
        self.root.deiconify()
        self.root.update()
        size = (self.root.winfo_width(), self.root.winfo_height())
        long_song = Song.from_texts('Long', {'cs': {'v1': 'x' * 250}}, {'default': 'v1'})
        self.assertTrue(self.editor.load_song(long_song))
        self.root.update()
        self.assertEqual((self.root.winfo_width(), self.root.winfo_height()), size)
        self.assertLess(self.editor.canvas.xview()[1], 1.0)
        self.editor.canvas.xview_moveto(1.0)
        self.root.update()
        self.assertGreater(self.editor.canvas.xview()[0], 0.0)
        self.assertTrue(self.editor.load_song(Song.from_texts()))
        self.root.update()
        self.assertEqual((self.root.winfo_width(), self.root.winfo_height()), size)
        self.assertEqual(self.editor.canvas.xview(), (0.0, 1.0))

    def test_wheel_over_expanding_verse_scrolls_editor(self):
        self.root.geometry('700x500')
        self.root.deiconify()
        # Synthetic wheel coordinates must hit this window even when another
        # desktop window overlaps it; exercise the real hit-test and bindings.
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.editor.load_song(Song.from_texts('Long', {'cs': {
            f'v{i}': 'One\nTwo\nThree' for i in range(1, 16)
        }}, {'default': 'v1'}))
        self.root.update()
        text = self.editor.sections[0]['widget']
        x, y = text.winfo_rootx() + 5, text.winfo_rooty() + 5
        self.assertIs(self.root.winfo_containing(x, y), text)
        self.editor.canvas.yview_moveto(0)
        text.event_generate('<MouseWheel>', delta=-30, rootx=x, rooty=y)
        self.root.update()
        self.assertGreater(self.editor.canvas.yview()[0], 0)
        self.assertEqual(text.yview(), (0.0, 1.0))

    def test_cancel_discard_and_failed_save_transitions(self):
        self.editor.title_variable.set('Changed')
        self.assertFalse(self.editor.new_song())
        self.assertEqual(self.editor.snapshot().title, 'Changed')
        self.choice.return_value = True
        with patch.object(self.editor.session.repository, 'save', side_effect=PermissionError('locked')):
            self.assertFalse(self.editor.new_song())
        self.assertTrue(self.editor.dirty)
        self.choice.return_value = False
        self.assertTrue(self.editor.new_song())
        self.assertFalse(self.editor.dirty)
        self.assertEqual(self.editor.snapshot(), Song.from_texts())

    def test_invalid_load_keeps_dirty_song_without_prompt(self):
        self.editor.title_variable.set('Changed')
        self.assertFalse(self.editor.load_file_from_path(self.path.with_name('absent.xml')))
        self.choice.assert_not_called()
        self.assertEqual(self.editor.snapshot().title, 'Changed')

    def test_repetitions_sync_and_save(self):
        self.editor.set_selected_repetition_text('v1 v2')
        self.assertTrue(self.editor.dirty)
        self.assertTrue(self.editor.save_file())
        self.assertFalse(self.editor.dirty)
        saved = SongRepository().load(self.path)
        self.assertEqual(saved.guide, 'v1 v2')
        self.assertEqual(saved.main_repetition, 'short')

    def test_remove_default_then_add_section_does_not_leave_stale_variable(self):
        self.editor.new_song()  # clean existing song
        self.editor.remove_repetition('default', self.editor.repetition_frames['default'])
        self.editor.add_section_to_all_languages('v')
        self.assertEqual(self.editor.snapshot().guide, 'v1')
        self.assertTrue(self.editor.dirty)

    def test_callback_failure_visible_and_transition_stops(self):
        self.editor.on_saved = Mock(side_effect=RuntimeError('callback failure'))
        self.editor.set_selected_repetition_text('v1')
        self.choice.return_value = True
        self.assertFalse(self.editor.new_song())
        self.assertIn('callback failure', self.error.call_args.args[1])
        self.assertEqual(SongRepository().load(self.path).guide, 'v1')
        self.assertFalse(self.editor.confirm_transition())
        self.editor.on_saved = Mock()
        self.assertTrue(self.editor.confirm_transition())
        self.editor.on_saved.assert_called_once()

    def test_rename_cancel_collision_and_copy(self):
        self.editor.title_variable.set('New')
        self.assertFalse(self.editor.save_file())
        self.assertTrue(self.editor.dirty)
        self.choice.return_value = False
        target = self.path.with_name('new.xml')
        SongRepository().save(self.song, target)
        self.assertFalse(self.editor.save_file())
        self.assertEqual(SongRepository().load(target).title, 'Original')
        self.overwrite.return_value = True
        self.assertTrue(self.editor.save_file())
        self.assertTrue(self.path.exists())
        self.assertEqual(SongRepository().load(target).title, 'New')

    def test_omission_warning_cancel_keeps_disk_and_dirty_then_accept_saves(self):
        original = self.path.read_bytes()
        self.editor.set_selected_repetition_text('v1')
        self.overwrite.side_effect = None
        self.overwrite.return_value = False
        self.assertFalse(self.editor.save_file())
        self.assertTrue(self.editor.dirty)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertIn('short', self.overwrite.call_args.args[1])
        self.assertIn('Sloka 2 (v2)', self.overwrite.call_args.args[1])
        self.overwrite.return_value = True
        self.assertTrue(self.editor.save_file())
        self.assertFalse(self.editor.dirty)
        self.assertEqual(SongRepository().load(self.path).guide, 'v1')

    def test_complete_repetitions_do_not_warn(self):
        self.editor.set_selected_repetition_text('v1 v2')
        self.assertTrue(self.editor.save_file())
        self.overwrite.assert_not_called()

    def test_text_undo_redo_restores_dirty_state(self):
        text = self.editor.sections[0]['widget']
        text.insert('end', ' extra')
        text.edit_separator()
        self.root.update()
        self.assertTrue(self.editor.dirty)
        self.editor._undo_text(text)
        self.assertEqual(text.get('1.0', 'end-1c'), 'One')
        self.assertFalse(self.editor.dirty)
        self.editor._undo_text(text, redo=True)
        self.assertEqual(text.get('1.0', 'end-1c'), 'One extra')
        self.assertTrue(self.editor.dirty)

    def test_ctrl_s_uses_save_validation_and_persists_text(self):
        self.root.geometry('+30000+30000')
        self.root.deiconify()
        self.root.update()
        text = self.editor.sections[0]['widget']
        text.focus_force()
        text.insert('end', ' changed')
        self.root.update()
        text.event_generate('<Control-s>')
        self.root.update()
        self.assertEqual(SongRepository().load(self.path).variant_texts['cs']['v1'], 'One changed')
        self.assertFalse(self.editor.dirty)

    def test_unknown_section_warning_can_cancel_or_save_draft(self):
        before = self.path.read_bytes()
        self.editor.set_selected_repetition_text('v3')
        self.overwrite.side_effect = None
        self.overwrite.return_value = False
        self.assertFalse(self.editor.save_file())
        self.assertEqual(self.overwrite.call_args.args[0], 'Chyba v opakování')
        self.assertIn('v3', self.overwrite.call_args.args[1])
        self.assertTrue(self.editor.dirty)
        self.assertEqual(self.path.read_bytes(), before)
        self.overwrite.return_value = True
        self.assertTrue(self.editor.save_file())
        self.assertEqual(SongRepository().load(self.path).guide, 'v3')

    def enable_recovery(self, directory=None, callback=None):
        self.editor.start_recovery(directory or Path(self.tmp.name) / 'recovery', on_restored=callback)
        self.addCleanup(self.editor._recovery.close)
        self.root.update_idletasks()
        return self.editor._recovery

    def test_backup_is_removed_on_save_and_explicit_discard(self):
        store = self.enable_recovery()
        self.editor.set_selected_repetition_text('v1')
        self.assertIsNotNone(self.editor._recovery_after)
        self.assertTrue(self.editor._flush_recovery())
        self.assertTrue(store.path.exists())
        self.assertTrue(self.editor.save_file())
        self.assertFalse(store.path.exists())
        self.editor.set_selected_repetition_text('v2')
        self.editor._flush_recovery()
        self.choice.return_value = False
        self.assertTrue(self.editor.new_song())
        self.assertFalse(store.path.exists())

    def test_restore_keeps_dirty_data_out_of_presentation_until_saved(self):
        gui = self.make_gui()
        writer = SongRecovery(Path(self.tmp.name) / 'recovery')
        self.addCleanup(writer.close)
        session = deepcopy(self.editor.session)
        session.song.variants[0].sections[0].lines = ['Recovered text']
        writer.write(session)
        writer.close()
        self.choice.return_value = True
        store = self.enable_recovery(writer.directory, gui.on_editor_restored)
        self.assertTrue(self.editor.dirty)
        self.assertEqual(self.editor.snapshot().variant_texts['cs']['v1'], 'Recovered text')
        self.assertEqual(gui.sources[gui.sourceList[gui.sourceID]].song.variant_texts['cs']['v1'], 'One')
        self.assertEqual(SongRepository().load(self.path).variant_texts['cs']['v1'], 'One')
        self.assertFalse(writer.path.exists())
        self.assertTrue(store.path.exists())
        self.assertTrue(self.editor.save_file())
        self.assertEqual(gui.sources[gui.sourceList[gui.sourceID]].song.variant_texts['cs']['v1'], 'Recovered text')
        self.assertFalse(store.path.exists())

    def test_recovery_can_be_postponed_or_discarded(self):
        writer = SongRecovery(Path(self.tmp.name) / 'recovery')
        self.addCleanup(writer.close)
        session = deepcopy(self.editor.session)
        session.song.title = 'Recovery'
        writer.write(session)
        writer.close()
        self.choice.return_value = None
        self.enable_recovery(writer.directory)
        self.assertTrue(writer.path.exists())
        self.assertEqual(self.editor.snapshot().title, 'Original')
        self.choice.return_value = False
        self.editor._offer_recovery()
        self.assertFalse(writer.path.exists())
        self.assertEqual(self.editor.snapshot().title, 'Original')

    def test_recovery_timer_records_latest_text_without_saving_song(self):
        before = self.path.read_bytes()
        store = self.enable_recovery()
        self.editor.title_variable.set('First change')
        self.root.after(300, lambda: self.editor.title_variable.set('Latest change'))
        self.root.after(1200, self.root.quit)
        self.root.mainloop()
        self.assertEqual(store.read(store.path)[0].title, 'Latest change')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertTrue(self.editor.dirty)

    def test_recovered_new_draft_can_be_saved_normally(self):
        gui = self.make_gui()
        writer = SongRecovery(Path(self.tmp.name) / 'recovery')
        self.addCleanup(writer.close)
        session = deepcopy(self.editor.session)
        session.reset(Song.from_texts())
        session.song = Song.from_texts('Recovered draft', {'cs': {'v1': 'Draft text'}}, {'default': 'v1'})
        writer.write(session)
        writer.close()
        self.choice.return_value = True
        store = self.enable_recovery(writer.directory, gui.on_editor_restored)
        self.assertTrue(gui.draft_open)
        self.assertTrue(self.editor.dirty)
        self.assertIsNone(self.editor.file_path)
        self.assertEqual(len(gui.sourceList), 1)
        self.assertTrue(self.editor.save_file())
        self.assertFalse(gui.draft_open)
        self.assertFalse(self.editor.dirty)
        self.assertEqual(len(gui.sourceList), 2)
        self.assertEqual(gui.sources[gui.sourceList[gui.sourceID]].song.title, 'Recovered draft')
        self.assertFalse(store.path.exists())

    def test_corrupt_recovery_shows_error_and_preserves_backup(self):
        directory = Path(self.tmp.name) / 'recovery'
        directory.mkdir()
        candidate = directory / 'corrupt.json'
        candidate.write_text('{broken', encoding='utf-8')
        self.enable_recovery(directory)
        self.assertEqual(candidate.read_text(encoding='utf-8'), '{broken')
        self.assertEqual(self.error.call_args.args[0], 'Chyba obnovy')
        self.assertFalse(self.editor.dirty)

    def make_gui(self):
        gui = GUI.__new__(GUI)
        gui.runState = False
        gui.win = self.root
        gui.sources = [WidgetSource(str(self.path))]
        gui.sources[0].variants = ['cs', '-----', '-----']
        gui.sourceList = [0]
        gui.sourceID = 0
        gui.draft_open = False
        gui.song_editor_widget = self.editor
        gui.newSource = tk.Button(self.root)
        gui.sourceNum = tk.Label(self.root)
        gui.sourceLab = tk.Label(self.root)
        gui.dirtyLabel = tk.Label(self.root)
        gui.var1Combo = ttk.Combobox(self.root)
        gui.var2Combo = ttk.Combobox(self.root)
        gui.var3Combo = ttk.Combobox(self.root)
        gui.construct_variable = tk.StringVar(master=self.root)
        gui.repIn = tk.Entry(self.root, textvariable=gui.construct_variable)
        gui._syncing_song = False
        gui.construct_variable.trace_add('write', gui._construct_changed)
        self.editor.on_changed = gui._editor_changed
        self.editor.on_saved = gui.on_editor_saved
        gui.viewSource()
        return gui

    def test_main_construct_is_dirty_and_only_save_publishes(self):
        gui = self.make_gui()
        running = deepcopy(gui.sources[0])
        gui.construct_variable.set('v1')
        self.assertTrue(self.editor.dirty)
        self.assertEqual(gui.sources[0].song.guide, 'v2')
        self.assertTrue(self.editor.save_file())
        self.assertEqual(gui.sources[0].song.guide, 'v1')
        self.assertEqual(running.song.guide, 'v2')
        self.assertEqual(gui.construct_variable.get(), 'v1')
        self.assertFalse(self.editor.dirty)

    def test_save_preserves_new_language_selection(self):
        gui = self.make_gui()
        self.editor.add_section('v', 1, 'First', 'en')
        self.editor.add_section('v', 2, 'Second', 'en')
        gui.var1Combo.set('en')
        gui.setVariant1()
        self.assertTrue(self.editor.save_file())
        self.assertEqual(gui.sources[0].variants[0], 'en')
        self.assertEqual(gui.var1Combo.get(), 'en')

    def test_retry_saved_callback_preserves_newer_edits(self):
        gui = self.make_gui()
        self.editor.on_saved = Mock(side_effect=RuntimeError('failed'))
        self.editor.set_selected_repetition_text('v1')
        self.assertFalse(self.editor.save_file())
        self.editor.title_variable.set('Newer unsaved title')
        self.editor.on_saved = gui.on_editor_saved
        self.assertFalse(self.editor.confirm_transition())
        self.assertEqual(self.editor.snapshot().title, 'Newer unsaved title')
        self.assertTrue(self.editor.dirty)
        self.assertEqual(gui.sources[0].song.guide, 'v1')

    def test_main_cancel_navigation_new_close_and_quit(self):
        gui = self.make_gui()
        second = self.path.with_name('second.xml')
        SongRepository().save(Song.from_texts('Second', {'cs': {'v1': 'Other'}}), second)
        gui.loadSource(str(second))
        self.editor.title_variable.set('Unsaved')
        for action in (gui.prevSourceFun, gui.newSongFun, gui.closeSourceFun, gui.on_closing):
            action()
            self.assertEqual(gui.sourceID, 1)
            self.assertEqual(self.editor.snapshot().title, 'Unsaved')
        self.assertTrue(self.root.winfo_exists())
        self.choice.return_value = False
        gui.prevSourceFun()
        self.assertEqual(gui.sourceID, 0)
        self.assertEqual(self.editor.snapshot().title, 'Original')

    def test_draft_save_during_navigation(self):
        gui = self.make_gui()
        gui.newSongFun()
        self.editor.title_variable.set('Draft')
        self.editor.add_section_to_all_languages('v')
        self.choice.return_value = True
        gui.prevSourceFun()
        self.assertEqual(len(gui.sourceList), 2)
        self.assertFalse(gui.draft_open)
        self.assertEqual(gui.sourceID, 0)
        self.assertEqual(gui.sources[1].song.title, 'Draft')

    def test_languages_and_non_numbered_ids_survive_load(self):
        song = Song.from_texts('Legacy', {'cs': {'r': 'Text'}, 'empty': {}}, {'only': 'r'}, 'only')
        self.assertTrue(self.editor.load_song(song))
        self.assertFalse(self.editor.dirty)
        self.assertEqual(self.editor.snapshot(), song)


class StartupTests(unittest.TestCase):
    def test_standalone_editor_has_title_and_close_protocol(self):
        root = tk.Tk()
        root.withdraw()
        try:
            editor = SongEditor(root)
            self.assertTrue(editor.title_entry.winfo_exists())
            self.assertTrue(root.protocol('WM_DELETE_WINDOW'))
            self.assertFalse(editor.dirty)
            order = editor.root.pack_slaves()
            self.assertLess(order.index(editor.canvas.master), order.index(editor.section_buttons_frame))
            self.assertLess(order.index(editor.section_buttons_frame), order.index(editor.repetition_container))
            self.assertLess(order.index(editor.repetition_container), order.index(editor.explain_label))
            editor.section_buttons[0].invoke()
            self.assertEqual(len(editor.sections), 1)
            self.assertTrue(any(w.cget('text') == 'Přidat variantu'
                                for w in editor.section_buttons_frame.winfo_children()))
            root.update_idletasks()
        finally:
            root.destroy()

    def test_title_placeholder_never_changes_song_data(self):
        root = tk.Tk()
        root.withdraw()
        try:
            editor = SongEditor(root)
            entry = editor.title_entry
            hint = next(child for child in entry.winfo_children() if isinstance(child, tk.Label))
            self.assertEqual(hint.cget('text'), 'Název zde')
            self.assertEqual(hint.winfo_manager(), 'place')
            self.assertEqual(editor.snapshot().title, '')
            self.assertFalse(editor.dirty)
            # Mouse events require mapped widgets; keep the test window offscreen.
            root.geometry('+30000+30000')
            root.deiconify()
            root.update()
            hint.event_generate('<Button-1>')
            self.assertEqual(hint.winfo_manager(), '')
            self.assertFalse(editor.dirty)
            entry.event_generate('<FocusOut>')
            self.assertEqual(hint.winfo_manager(), 'place')
            editor.title_variable.set('Actual title')
            self.assertEqual(hint.winfo_manager(), '')
            self.assertEqual(editor.snapshot().title, 'Actual title')
            root.update_idletasks()
        finally:
            root.destroy()

    def test_main_window_wiring(self):
        original_tk = tk.Tk
        def hidden_root():
            root = original_tk()
            root.withdraw()
            return root
        with patch('super_presenter.tk.Tk', side_effect=hidden_root), patch.object(GUI, 'getMonitors'), patch.object(GUI, 'newProjector'), patch.object(GUI, 'init_profiles'), patch.object(GUI, 'start_monitor_watch'), patch('super_presenter.tkmsg.showerror') as error:
            gui = GUI()
            try:
                self.assertTrue(gui.sourceTitleEntry.winfo_children())
                gui.song_title.set('Draft title')
                self.assertEqual(gui.song_editor_widget.snapshot().title, 'Draft title')
                self.assertTrue(gui.song_editor_widget.dirty)
                error.assert_not_called()
                gui.win.update_idletasks()
            finally:
                gui.win.destroy()


if __name__ == '__main__':
    unittest.main()
