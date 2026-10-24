"""Embedded editor callbacks; the widgets themselves remain in SongEditor.

Mixed into GUI to preserve existing callback names and shared UI state.
"""
import os
from superpresenter.services.presentation_session import WidgetSource


class SongEditorPanel:
    def _is_on_draft(self):
        return self.draft_open and self.sourceID == len(self.sourceList)


    def _prepare_song_transition(self):
        return self.song_editor_widget.confirm_transition()


    def _update_new_button_state(self):
        self.newSource.configure(state='normal')


    def _construct_changed(self, *_):
        if not self._syncing_song:
            self.song_editor_widget.set_selected_repetition_text(self.construct_variable.get())


    def _update_song_caption(self, dirty=None):
        editor = self.song_editor_widget
        suffix = ' *' if (editor.dirty if dirty is None else dirty) else ''
        self.sourceLab.config(text=(editor.title_variable.get() or '(neuložená píseň)') + suffix)
        self.dirtyLabel.config(text=suffix)

    def _editor_changed(self, song):
        self._update_song_caption(self.song_editor_widget.session.dirty)
        self._syncing_song = True
        try:
            if self.construct_variable.get() != song.guide:
                self.construct_variable.set(song.guide)
            languages = list(song.variant_texts)
            for index, combo in enumerate((self.var1Combo, self.var2Combo, self.var3Combo)):
                choices = languages if index == 0 else ['-----'] + languages
                current = combo.get()
                if tuple(combo['values']) != tuple(choices):
                    combo['values'] = choices
                if current not in choices:
                    combo.set(choices[0] if choices else '')
        finally:
            self._syncing_song = False


    def total_sources(self):
        return len(self.sourceList) + (1 if self.draft_open else 0)


    def viewDraft(self, *e):
        self.sourceNum.configure(text=f'{self.sourceID+1} / {self.total_sources()}')
        self.sourceLab.config(text='(neuložená píseň)')
        self._editor_changed(self.song_editor_widget.snapshot())


    def on_editor_restored(self, song, clean_song, path):
        """Show recovered work while keeping presentation data at its clean baseline."""
        if path:
            source = WidgetSource(path, clean_song)
            languages = source.importVariants()
            source.variants = [languages[0] if languages else '-----', '-----', '-----']
            self.sources.append(source)
            self.sourceList.append(len(self.sources) - 1)
            self.sourceID = len(self.sourceList) - 1
            self.draft_open = False
            self.viewSource(reload_editor=False)
            self._editor_changed(song)
        else:
            self.draft_open = True
            self.sourceID = len(self.sourceList)
            self.viewDraft()
        self._update_new_button_state()


    def on_editor_saved(self, song, path, renamed_from=None):
        """Publish a fresh saved snapshot; running presentations retain their snapshot."""
        same_path = lambda a, b: os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
        selected_languages = [combo.get() for combo in (self.var1Combo, self.var2Combo, self.var3Combo)]
        current = self.sourceList[self.sourceID] if 0 <= self.sourceID < len(self.sourceList) else None
        idx = None
        for i, source in enumerate(self.sources):
            if same_path(source.path, path) or (renamed_from and same_path(source.path, renamed_from)):
                updated = WidgetSource(path, song)
                languages = updated.importVariants()
                choices = selected_languages if i == current else source.variants
                updated.variants = [value if value in languages else (languages[0] if j == 0 and languages else '-----') for j, value in enumerate(choices)]
                self.sources[i] = updated
                if idx is None:
                    idx = i
        if idx is None:
            updated = WidgetSource(path, song)
            languages = updated.importVariants()
            updated.variants = [value if value in languages else (languages[0] if j == 0 and languages else '-----') for j, value in enumerate(selected_languages)]
            self.sources.append(updated)
            idx = len(self.sources) - 1
        if idx not in self.sourceList:
            self.sourceList.append(idx)
        self.draft_open = False
        self.sourceID = self.sourceList.index(idx)
        self._update_new_button_state()
        self.viewSource(reload_editor=False)


    def openSongEditor(self):
        import subprocess
        import sys
        if hasattr(self, "song_editor_win") and self.song_editor_win.poll() is None:
            return  # Editor už běží
        path = os.path.join(self.dir, 'song_editor.py')
        self.song_editor_win = subprocess.Popen([sys.executable, path])


    def saveRepetitions(self, *e):
        self.song_editor_widget.set_selected_repetition_text(self.repIn.get())


    def _set_variant(self, index, combo):
        if 0 <= self.sourceID < len(self.sourceList):
            source = self.sources[self.sourceList[self.sourceID]]
            if combo.get() in source.song.variant_texts or (index > 0 and combo.get() == '-----'):
                source.variants[index] = combo.get()


    def setVariant1(self, *e):
        self._set_variant(0, self.var1Combo)


    def setVariant2(self, *e):
        self._set_variant(1, self.var2Combo)


    def setVariant3(self, *e):
        self._set_variant(2, self.var3Combo)


    def newSongFun(self, *e):
        if not self.song_editor_widget.new_song():
            return
        self.draft_open = True
        self.sourceID = len(self.sourceList)
        self._update_new_button_state()
        self.viewDraft()
