from pathlib import Path
p=Path('tests/test_song_editor_data.py'); s=p.read_text(encoding='utf-8-sig'); pos=s.index("if __name__ == '__main__':")
s=s[:pos]+'''class RepetitionCoverageTests(unittest.TestCase):
    def test_missing_chorus_per_repetition_without_duplicate_languages(self):
        session = SongEditSession()
        session.reset(Song('Test', {'cs': {'v1': 'A', 'v2': 'B', 'r1': 'C'},
                                   'en': {'v1': 'a', 'v2': 'b', 'r1': 'c'}},
                           {'band A': 'v1 v2 v1', 'band B': '(v1 v2 r1)*2'}, 'band A'))
        self.assertEqual(session.omitted_sections(), {'band A': ['r1']})
        self.assertFalse(session.dirty)

    def test_whole_ids_nested_groups_and_ranges(self):
        session = SongEditSession()
        session.reset(Song('Test', {'cs': {'v1': 'A', 'v10': 'B', 'r': 'C'}},
                           {'default': '((v10.1:3)*2 r.1)*3'}))
        self.assertEqual(session.omitted_sections(), {'default': ['v1']})
        session.song.repetitions['default'] += ' v1'
        self.assertEqual(session.omitted_sections(), {})

    def test_empty_and_absent_repetition(self):
        session = SongEditSession()
        session.reset(Song('Test', {'cs': {'v1': 'A'}}))
        self.assertEqual(session.omitted_sections(), {'default': ['v1']})
        session.song.repetitions = {}
        self.assertEqual(list(session.omitted_sections().values()), [['v1']])
        session.reset(Song())
        self.assertEqual(session.omitted_sections(), {})


'''+s[pos:]; p.write_text(s,encoding='utf-8')
p=Path('tests/test_song_editor_integration.py'); s=p.read_text(encoding='utf-8-sig')
s=s.replace('from song_editor import SongEditor', 'from song_editor import SongEditor, add_title_placeholder')
s=s.replace("        self.overwrite = self.enterContext(patch('song_editor.messagebox.askyesno', return_value=False))", "        self.overwrite = self.enterContext(patch('song_editor.messagebox.askyesno', return_value=False))\n        self.overwrite.side_effect = lambda title, *args, **kwargs: True if title == 'Vynechané sekce v opakování' else self.overwrite.return_value")
pos=s.index('    def make_gui(self):')
s=s[:pos]+'''    def test_omission_warning_cancel_keeps_disk_and_dirty_then_accept_saves(self):
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

'''+s[pos:]
pos=s.index('    def test_main_window_wiring(self):')
s=s[:pos]+'''    def test_title_placeholder_never_changes_song_data(self):
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

'''+s[pos:]
s=s.replace("                gui.song_title.set('Draft title')", "                self.assertTrue(gui.sourceTitleEntry.winfo_children())\n                gui.song_title.set('Draft title')")
p.write_text(s,encoding='utf-8')
