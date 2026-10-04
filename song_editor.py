import logging
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from copy import deepcopy
from pathlib import Path
from superpresenter.domain.song import Song
from superpresenter.services.song_edit_session import SongEditSession, update_song_fields, validate_editor_fields
from superpresenter.services.song_recovery import SongRecovery
from superpresenter.paths import PROJECT_ROOT
from superpresenter.ui.mousewheel import bind_canvas_wheel
from superpresenter.ui.scrollbars import Scrollbar
import os
import re


def add_title_placeholder(entry, variable):
    """Display a hint without inserting it into the song's title variable."""
    hint = tk.Label(entry, text="Název zde", cursor="xterm", takefocus=False)
    active = False

    def refresh(*_):
        if not variable.get() and not active:
            hint.configure(background=entry.cget("background"),
                           foreground="#aaaaaa", font=entry.cget("font"))
            hint.place(relx=0.5, rely=0.5, anchor="center")
        else:
            hint.place_forget()

    def focus_in(event=None):
        nonlocal active
        active = True
        hint.place_forget()

    def focus_out(event=None):
        nonlocal active
        active = False
        refresh()

    def click(event):
        focus_in()
        entry.focus_set()
        return "break"

    hint.bind("<Button-1>", click)
    entry.bind("<Button-1>", focus_in, add="+")
    entry.bind("<FocusIn>", focus_in, add="+")
    entry.bind("<FocusOut>", focus_out, add="+")
    entry.bind("<Configure>", refresh, add="+")
    trace = variable.trace_add("write", refresh)
    entry.bind("<Destroy>", lambda event: variable.trace_remove("write", trace)
               if event.widget == entry else None, add="+")
    refresh()
    return hint


class SongEditor:
    def __init__(self, root, embedded=False, title_variable=None, on_saved=None, on_changed=None):
        self.root = root
        self.session = SongEditSession()
        self._loading = True
        self._pending_saved = None
        self._recovery = None
        self._recovery_after = None
        self._recovery_error = False
        self.on_saved = on_saved
        self.on_changed = on_changed
        self.title_variable = title_variable if title_variable is not None else tk.StringVar(master=root)
        self.status_variable = tk.StringVar(master=root)
        self.manual_repetition_edit = False
        self.embedded = embedded 
        if not embedded:
            self.root.title("Editor písní")
            self.root.geometry("900x800")

        self.sections = []
        self.repetition_entry = None
        self.file_path = None
        self.original_title = None
        self.current_variant = "čeština"

        self.songs_dir = os.path.join(PROJECT_ROOT, 'songs')
        os.makedirs(self.songs_dir, exist_ok=True)

        self.bg_color = "#555555"
        self.entry_bg = "#505050"
        self.text_bg = "#666666"
        self.button_bg = "#444444"

        self.repetitions = {}
        self.selected_repetition = tk.StringVar(value="default")
        
        self.apply_base_style()
        self.build_ui()

        self.title_variable.trace_add("write", self._changed)
        self.selected_repetition.trace_add("write", self._changed)
        self._loading = False
        self._render_song()
        self.root.winfo_toplevel().bind('<Control-s>', self._save_shortcut)
        self.root.winfo_toplevel().bind('<Control-S>', self._save_shortcut)
        if not embedded:
            self.root.protocol("WM_DELETE_WINDOW", self.close_window)

    def _save_shortcut(self, event=None):
        self.save_file()
        return 'break'

    def _undo_text(self, text, redo=False):
        try:
            text.edit_redo() if redo else text.edit_undo()
        except tk.TclError:
            text.bell()
        self._changed()
        return 'break'

    def start_recovery(self, directory=None, on_restored=None):
        """Enable disk recovery at application startup (not in embedded test fixtures)."""
        if self._recovery is not None:
            return
        try:
            self._recovery = SongRecovery(directory or Path(PROJECT_ROOT) / '.song-recovery')
        except OSError as exc:
            messagebox.showwarning('Záloha není dostupná', f'Průběžné zálohování se nepodařilo zapnout:\n{exc}', parent=self.root)
            return
        self.root.bind('<Destroy>', self._close_recovery, add='+')
        self.root.after_idle(lambda: self._offer_recovery(on_restored))
        self._queue_recovery()

    def _queue_recovery(self):
        if self._recovery is None:
            return
        if not self.session.dirty:
            self._flush_recovery()
        elif self._recovery_after is None:
            # Throttle rather than debounce: continuous typing is backed up too.
            self._recovery_after = self.root.after(1000, self._flush_recovery)

    def _flush_recovery(self):
        if self._recovery_after is not None:
            self.root.after_cancel(self._recovery_after)
            self._recovery_after = None
        if self._recovery is None:
            return True
        try:
            self.session.song = self.snapshot()
            if self.session.dirty:
                self._recovery.write(self.session)
            else:
                self._recovery.clear()
            self._recovery_error = False
            return True
        except Exception as exc:
            self.status_variable.set('Neuloženo – chyba zálohy' if self.session.dirty else 'Chyba zálohy')
            if not self._recovery_error:
                self._recovery_error = True
                messagebox.showwarning('Chyba zálohy', f'Průběžnou zálohu nelze aktualizovat:\n{exc}\nPíseň můžete uložit tlačítkem Uložit.', parent=self.root)
            return False

    def _offer_recovery(self, on_restored=None):
        try:
            candidates = self._recovery.candidates()
        except OSError as exc:
            messagebox.showerror('Chyba obnovy', str(exc), parent=self.root)
            return
        for candidate in candidates:
            lease = None
            try:
                lease = self._recovery.claim(candidate)
                if lease is None or not candidate.exists():
                    continue
                song, clean_song, path = self._recovery.read(candidate)
                validate_editor_fields(song)
                choice = messagebox.askyesnocancel('Obnovit rozpracovanou píseň?',
                    f'Nalezena neuložená verze: {song.title or "(bez názvu)"}\n'
                    f'{path or "Nová píseň"}\n\nAno = obnovit, Ne = zahodit zálohu, Storno = ponechat na později.', parent=self.root)
                if choice is None:
                    return
                if not choice:
                    candidate.unlink()
                    continue
                if not self.confirm_transition():
                    return
                self.session.reset(clean_song, path)
                self.session.song = song
                self._render_song()
                if on_restored:
                    on_restored(deepcopy(song), deepcopy(clean_song), path)
                # Only remove the old record after the recovered state is durable.
                if self._flush_recovery():
                    candidate.unlink()
                return
            except Exception as exc:
                messagebox.showerror('Chyba obnovy', f'Záloha {candidate} zůstala zachovaná:\n{exc}', parent=self.root)
            finally:
                if lease is not None:
                    lease.close()

    def _close_recovery(self, event):
        if event.widget != self.root:
            return
        if self._recovery_after is not None:
            self.root.after_cancel(self._recovery_after)
            self._recovery_after = None
        if self._recovery is not None:
            self._recovery.close()
            self._recovery = None

    def snapshot(self):
        variants = {name: {} for name, sections in self.session.song.variant_texts.items() if not sections}
        for section in self.sections:
            variants.setdefault(section['lang'], {})[section['sid']] = section['widget'].get("1.0", "end-1c")
        return update_song_fields(self.session.song, self.title_variable.get(), variants,
                                  {name: var.get() for name, var in self.repetition_vars.items()},
                                  self.selected_repetition.get())

    @property
    def dirty(self):
        self.session.song = self.snapshot()
        return self.session.dirty

    def _changed(self, *_):
        if self._loading:
            return
        self.session.song = self.snapshot()
        self.status_variable.set("Neuloženo" if self.session.dirty else "")
        self._queue_recovery()
        if self.on_changed:
            try:
                self.on_changed(deepcopy(self.session.song))
            except Exception as exc:
                messagebox.showerror("Chyba synchronizace", str(exc), parent=self.root)

    def confirm_transition(self):
        if self._pending_saved and not self._notify_saved():
            return False
        if not self.dirty:
            return True
        choice = messagebox.askyesnocancel(
            "Neuložené změny", "Uložit změny písně?\nAno = uložit, Ne = zahodit, Storno = zůstat.", parent=self.root)
        if choice is None:
            return False
        if choice:
            return self.save_file()
        self.session.song = deepcopy(self.session.clean_song)
        self._render_song()
        return True

    def close_window(self):
        if self.confirm_transition():
            self.root.destroy()

    def _render_song(self):
        self._loading = True
        try:
            song = self.session.song
            self.clear_editor()
            self.title_variable.set(song.title)
            self.manual_repetition_edit = True
            for lang, sections in song.variant_texts.items():
                for sid, content in sections.items():
                    match = re.fullmatch(r"([a-zA-Z]+)([0-9]+)", sid)
                    typ, num = (match[1], int(match[2])) if match else (sid, 0)
                    self.add_section(typ, num, content, lang, sid=sid)
            for name, value in song.repetition_texts.items():
                self.add_repetition(name, value)
            self.repetition_entry = self.repetition_vars.get("default", tk.StringVar(master=self.root))
            self.selected_repetition.set(song.main_repetition)
            self.file_path = str(self.session.path) if self.session.path else None
            self.original_title = self.session.clean_song.title
            self.manual_repetition_edit = bool(self.session.path or song.guide)
            self.current_variant = "čeština"
            self.status_variable.set("Neuloženo" if self.session.dirty else "")
        finally:
            self._loading = False
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self._update_canvas_layout()
        self._changed()

    def set_selected_repetition_text(self, text):
        name = self.selected_repetition.get()
        if name not in self.repetition_vars:
            self.add_repetition("default", text)
            self.selected_repetition.set("default")
            self.repetition_entry = self.repetition_vars["default"]
        elif self.repetition_vars[name].get() != text:
            self.repetition_vars[name].set(text)
        self.manual_repetition_edit = True

    def apply_base_style(self):
        self.root.configure(bg=self.bg_color)
        self.root.option_add("*Background", self.bg_color)
        self.root.option_add("*Foreground", "white")
        self.root.option_add("*Entry.Background", self.entry_bg)
        self.root.option_add("*Entry.Foreground", "white")
        self.root.option_add("*Text.Background", self.text_bg)
        self.root.option_add("*Text.Foreground", "white")
        self.root.option_add("*Button.Background", self.button_bg)
        self.root.option_add("*Button.Foreground", "white")
        self.root.option_add("*LabelFrame.Background", self.bg_color)
        self.root.option_add("*LabelFrame.Foreground", "white")
        self.root.option_add("*Label.Background", self.bg_color)
        self.root.option_add("*Label.Foreground", "white")
        self.font = ("Courier New", 13)

    def build_ui(self):
        if not self.embedded:
            top_frame = tk.Frame(self.root)
            top_frame.pack(fill='x') 

            tk.Button(top_frame, text=" + ", command=self.load_file, font=self.font).pack(side='left', padx=5)
            tk.Button(top_frame, text="Nová píseň", command=self.new_song, font=self.font).pack(side='left', padx=5)

        if not self.embedded:
            self.title_entry = tk.Entry(self.root, textvariable=self.title_variable, font=self.font)
            self.title_entry.pack(fill='x', padx=5)
            add_title_placeholder(self.title_entry, self.title_variable)

        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=self.bg_color, highlightthickness=0)
        self.scrollbar = Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        self.horizontal_scrollbar = Scrollbar(canvas_frame, orient='horizontal', command=self.canvas.xview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_color)

        # vytvořit okno a pamatovat si jeho id
        self._window_item = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')

        # držet šířku vnitřního okna = šířka canvasu (tedy šířka "obdélníku")
        self.canvas.bind("<Configure>", self._update_canvas_layout)

        # scrollregion podle obsahu
        self.scrollable_frame.bind("<Configure>", self._update_canvas_layout)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.configure(xscrollcommand=self.horizontal_scrollbar.set)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.scrollbar.grid(row=0, column=1, sticky='ns')
        self.horizontal_scrollbar.grid(row=1, column=0, sticky='ew')
        self._canvas_wheel = bind_canvas_wheel(self.canvas, self._scroll_canvas)

        self.sections_frame = self.scrollable_frame

        self.section_buttons_frame = tk.Frame(self.root)
        self.section_buttons_frame.pack(pady=(20, 5))
        self.section_buttons = []
        for label, typ in [("Sloka", 'v'), ("Refrén", 'r'), ("Bridge", 'b')]:
            button = tk.Button(self.section_buttons_frame, text=label,
                               command=lambda t=typ: self.add_section_to_all_languages(t), font=self.font)
            button.pack(side='left', padx=5)
            self.section_buttons.append(button)
        if not self.embedded:
            tk.Button(self.section_buttons_frame, text="Přidat variantu",
                      command=self.open_language_dialog, font=self.font).pack(side='left', padx=10)

        header_frame = tk.Frame(self.root)
        header_frame.pack(anchor='w', padx=5, pady=(6, 0))
        tk.Label(header_frame, text="Opakování:", font=self.font).pack(side='left')
        tk.Button(header_frame, text=" + ", command=self.add_repetition_prompt, font=self.font).pack(side='left', padx=10)

        self.repetition_frames = {}
        self.repetition_vars = {}

        self.repetition_container = tk.Frame(self.root, bg=self.bg_color)
        self.repetition_container.pack(fill='x', padx=5)

        self.explain_label = tk.Label(self.root,
                text="v = Sloka, r = Refrén, b = Bridge | (v) = 1 Opakování | (v)*x = x Opakování | v.x = Pouze x řádek | v.x:y = od do řádky\n@v = připnutí k předchozí sloce",
                font=('TkDefaultFont' if self.embedded else ('Courier New', 10, 'italic')),
                fg='white', bg=self.bg_color)
        if self.embedded:
            self.explain_label.configure(wraplength=640, justify='left')
        self.explain_label.pack(anchor='w', padx=5)

        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(fill='x', pady=(2, 0))  
        tk.Button(ctrl_frame, text="Uložit",
                command=self.save_file, font=self.font).pack(pady=2)

        tk.Label(ctrl_frame, textvariable=self.status_variable, font=self.font).pack()

        self.add_repetition("default")
        self.repetition_entry = self.repetition_vars["default"]

        if not self.embedded:
            # 🔧 Tlačítko pro opravu XML souborů
            fix_frame = tk.Frame(self.root, bg=self.bg_color)
            fix_frame.pack(anchor="sw", side="bottom", pady=5, padx=5)

            tk.Button(fix_frame, text="Error Fix", font=self.font,
                    bg=self.button_bg, fg="white",
                    command=self.run_error_fix).pack(anchor="sw")


    def _scroll_canvas(self, event):
        if event.delta:
            steps = max(1, int(abs(event.delta) / 120))
            self.canvas.yview_scroll(-steps if event.delta > 0 else steps, 'units')

    def _update_canvas_layout(self, event=None):
        content_width = max((section['frame'].winfo_reqwidth() + 40
                             for section in self.sections), default=0)
        width = max(self.canvas.winfo_width(), content_width)
        self.canvas.itemconfigure(self._window_item, width=width)
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def get_existing_languages(self):
        return list(dict.fromkeys(s['lang'] for s in self.sections)) or ["čeština"]

    def get_next_section_number(self, sec_type):
        existing = [s['num'] for s in self.sections if s['type'] == sec_type]
        return max(existing, default=0) + 1

    def add_section_to_all_languages(self, sec_type):
        num = self.get_next_section_number(sec_type)
        for lang in self.get_existing_languages():
            self.add_section(sec_type, num, "", lang)

    def add_section(self, sec_type, num=None, content="", lang="čeština", sid=None):
        if num is None:
            num = self.get_next_section_number(sec_type)

        sid = sid or f"{sec_type}{num}"
        label = f"{'Sloka' if sec_type == 'v' else 'Refrén' if sec_type == 'r' else 'Bridge'} {num}"
        if lang != "čeština":
            label += f" – {lang}"

        frame = tk.LabelFrame(self.sections_frame, text=label, font=self.font)

        inserted = False
        for s in self.sections:
            if s['type'] == sec_type and s['num'] == num:
                if lang == "čeština":
                    frame.pack(fill='x', padx=5, pady=3, before=s['frame'])
                else:
                    frame.pack(fill='x', padx=20, pady=1, after=s['frame'])
                inserted = True
                break

        if not inserted:
            frame.pack(fill='x', padx=5, pady=3)

        header = tk.Frame(frame)
        header.pack(fill='x')

        remove_btn = tk.Button(
            header,
            text=' - ',
            command=lambda fr=frame: self.remove_section(fr),
            font=self.font
        )
        remove_btn.pack(side='right', padx=5)

        text = tk.Text(frame, height=1, width=1, font=self.font, wrap='none', undo=True, maxundo=200)
        text._scroll_parent_canvas = True
        text.bind('<MouseWheel>', self._canvas_wheel)
        text.insert('end', content)
        text.pack(fill='x')

        def resize_text(event):
            lines = text.get("1.0", "end-1c").split("\n")
            text.configure(height=max(1, len(lines)),
                           width=max(1, max(len(line.expandtabs(8)) for line in lines)))

        def modified(event):
            if text.edit_modified():
                text.edit_modified(False)
                resize_text(event)
                self._changed()
        text.edit_reset()
        text.edit_modified(False)
        text.bind('<Control-z>', lambda e: self._undo_text(text))
        text.bind('<Control-y>', lambda e: self._undo_text(text, redo=True))
        text.bind('<Control-Shift-Z>', lambda e: self._undo_text(text, redo=True))
        text.bind("<<Modified>>", modified)
        text.bind("<KeyRelease>", resize_text)
        resize_text(None)

        if not self.manual_repetition_edit and lang == "čeština":
            if "default" not in self.repetition_vars:
                self.add_repetition("default")
                self.repetition_entry = self.repetition_vars["default"]
                self.selected_repetition.set("default")
            ordered = [s['sid'] for s in self.sections if s['lang'] == "čeština"]
            ordered.append(f"{sec_type}{num}")
            self.repetition_entry.set(" ".join(ordered))

        self.sections.append({'sid': sid, 'type': sec_type, 'num': num, 'widget': text, 'frame': frame, 'lang': lang})
        self._changed()

    def open_language_dialog(self):
        lang_win = tk.Toplevel(self.root)
        lang_win.title("Přidat jazyk")
        lang_win.geometry("300x130")
        lang_win.configure(bg=self.bg_color)

        tk.Label(lang_win, text="Vyber nebo zadej jazyk:", font=self.font, bg=self.bg_color, fg="white").pack(pady=5)
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TCombobox", fieldbackground=self.entry_bg, background=self.entry_bg, foreground="white")

        combo = ttk.Combobox(lang_win, values=["angličtina", "український - auto", "slovenština", "hebrejština", "hebrejština - transkript"], font=self.font)
        combo.pack(pady=5)
        combo.set("angličtina")

        def confirm():
            val = combo.get().strip()
            if not val:
                lang_win.destroy()
                return
            self.create_language_variant(val)
            lang_win.destroy()

        tk.Button(lang_win, text="Přidat", command=confirm, font=self.font).pack(pady=5)

    def create_language_variant(self, lang):
        if lang in self.get_existing_languages():
            messagebox.showinfo("Jazyk", "Tento jazyk již existuje.", parent=self.root)
            return
        original = [s for s in self.sections if s['lang'] == "čeština"]
        self.current_variant = lang
        for s in original:
            content = s['widget'].get("1.0", "end").strip()
            self.add_section(s['type'], s['num'], content, lang, sid=s['sid'])

    def remove_section(self, frame):
        target = next((section for section in self.sections if section['frame'] == frame), None)
        if target is not None:
            self.session.song = self.snapshot()
            self.session.remove_section(target['sid'])
            self._render_song()

    def new_song(self):
        if not self.confirm_transition():
            return False
        self.session.reset(Song.from_texts())
        self._render_song()
        return True

    def mark_repetition_as_manual(self):
        self.manual_repetition_edit = True

    def add_repetition_prompt(self):
        name = simpledialog.askstring("Nové opakování", "Zadej název opakování:", parent=self.root)
        if name and name not in self.repetitions:
            self.add_repetition(name)

    def add_repetition(self, name, value=""):
        if name in self.repetition_vars:
            self.repetition_vars[name].set(value)
            return
        frame = tk.Frame(self.repetition_container, bg=self.bg_color)
        frame.pack(fill='x', pady=2)
        tk.Label(frame, text=name, font=self.font, bg=self.bg_color, fg='white').pack(side='left')

        var = tk.StringVar()
        var.set(value)
        entry = tk.Entry(frame, textvariable=var, font=self.font, width=50)
        entry.pack(side='left', padx=5, expand=True, fill='x')

        if name == "default":
            entry.bind("<Key>", lambda e: self.mark_repetition_as_manual())

        del_btn = tk.Button(
            frame, text=" - ", font=self.font, takefocus=0,
            command=lambda n=name, fr=frame: self.remove_repetition(n, fr)
        )
        del_btn.pack(side='right', padx=5)

        sel = tk.Radiobutton(
            frame,
            variable=self.selected_repetition,
            value=name,
            bg=self.bg_color,
            highlightthickness=0,
            selectcolor=self.bg_color,
            takefocus=0
        )
        sel.pack(side='right', padx=5)

        self.repetition_frames[name] = frame
        self.repetition_vars[name] = var
        self.repetitions[name] = value
        var.trace_add("write", self._changed)
        self._changed()

    def remove_repetition(self, name, frame):
        if name in self.repetition_frames:
            frame.destroy()
            del self.repetition_frames[name]
            del self.repetition_vars[name]
            del self.repetitions[name]
        if self.selected_repetition.get() == name:
            fallback = "default" if "default" in self.repetition_vars else (next(iter(self.repetition_vars), ""))
            self.selected_repetition.set(fallback)
        self._changed()
            
    def validate_line_counts(self):
        section_map = {}
        for s in self.sections:
            key = (s['type'], s['sid'])
            lines = s['widget'].get("1.0", "end").strip().split('\n')
            count = len(lines)
            if key not in section_map:
                section_map[key] = count
            else:
                if section_map[key] != count:
                    return False, key, section_map[key], count
        return True, None, None, None

    def get_selected_repetition_text(self):
        name = self.selected_repetition.get()
        var = self.repetition_vars.get(name)
        return name, (var.get().strip() if var else "")
    
    def save_file(self):
        if self._pending_saved and not self._notify_saved():
            return False
        self.session.song = self.snapshot()
        valid, key, expected, actual = self.validate_line_counts()
        if not valid:
            messagebox.showerror("Chyba", f"Sekce {key[1]} má různý počet řádků mezi jazyky: {expected} a {actual}.", parent=self.root)
            return False
        old_path = self.session.path
        rename = False
        target = old_path
        try:
            title = self.session.song.title
            if not title.strip():
                raise ValueError("Název písně nesmí být prázdný.")
            if old_path and title == self.session.clean_song.title:
                target = old_path
            else:
                target = (old_path.parent if old_path else Path(self.songs_dir)) / self.session.repository.filename(title)
            if old_path and target.resolve() != old_path.resolve():
                decision = messagebox.askyesnocancel("Změna názvu", "Přejmenovat původní soubor?\nAno = přejmenovat, Ne = uložit kopii, Storno = zrušit uložení.", parent=self.root)
                if decision is None:
                    return False
                rename = decision
            same = old_path is not None and target.resolve() == old_path.resolve()
            overwrite = same
            if target.exists() and not same:
                overwrite = messagebox.askyesno("Soubor již existuje", f"Přepsat soubor?\n{target}", parent=self.root)
                if not overwrite:
                    return False
            problems = self.session.repetition_problems()
            if problems:
                details = '\n'.join(f'{name}: {problem}' for name, problem in problems.items())
                if not messagebox.askyesno('Chyba v opakování',
                        'Opakování obsahuje neexistující sekci nebo chybný zápis:\n\n'
                        + details + '\n\nDoporučuji zápis opravit. Přesto uložit rozpracovanou píseň?',
                        icon='warning', parent=self.root):
                    return False
            missing = self.session.omitted_sections()
            if missing:
                def section_label(sid):
                    match = re.fullmatch(r"([vrb])([0-9]+)", sid)
                    return f"{ {'v': 'Sloka', 'r': 'Refrén', 'b': 'Bridge'}[match[1]]} {match[2]} ({sid})" if match else sid
                details = "\n".join(f"{name}: {', '.join(section_label(sid) for sid in sections)}"
                                    for name, sections in missing.items())
                if not messagebox.askyesno(
                        "Vynechané sekce v opakování",
                        "V těchto opakováních nejsou použity některé sekce písně:\n\n"
                        + details + "\n\nVynechání může být záměrné. Přesto uložit?",
                        icon="warning", parent=self.root):
                    return False
            self.session.save(target, overwrite=overwrite, rename=rename)
        except Exception as exc:
            logging.getLogger(__name__).exception("Song save failed: %s", target)
            messagebox.showerror("Chyba ukládání", f"Píseň se nepodařilo uložit:\n{exc}", parent=self.root)
            return False
        self.file_path = str(self.session.path)
        self.original_title = self.session.song.title
        self.status_variable.set("")
        self._flush_recovery()
        self._pending_saved = (deepcopy(self.session.song), self.file_path, str(old_path) if rename and old_path else None)
        return self._notify_saved()

    def _notify_saved(self):
        pending = self._pending_saved
        self._pending_saved = None  # callback may refresh this editor through load_song
        if self.on_saved and pending:
            try:
                self.on_saved(*pending)
            except Exception as exc:
                logging.getLogger(__name__).exception("Saved song synchronization failed")
                self._pending_saved = pending
                self.status_variable.set("Uloženo, chyba synchronizace")
                messagebox.showerror("Chyba synchronizace", f"Soubor je uložen v {pending[1]}, ale hlavní aplikaci se nepodařilo aktualizovat:\n{exc}", parent=self.root)
                return False
        return True

    def load_file(self):
        file_path = filedialog.askopenfilename(initialdir=self.songs_dir, filetypes=[("Písně", "*.xml *.txt")])
        return self.load_file_from_path(file_path) if file_path else False

    def load_file_from_path(self, file_path):
        try:
            song = self.session.repository.load(file_path)
        except Exception as exc:
            logging.getLogger(__name__).exception("Song loading failed: %s", file_path)
            messagebox.showerror("Chyba načítání", f"Nelze načíst {file_path}:\n{exc}", parent=self.root)
            return False
        return self.load_song(song, file_path)

    def load_song(self, song, file_path=None):
        try:
            validate_editor_fields(song)
        except ValueError as exc:
            messagebox.showerror("Chyba načítání", str(exc), parent=self.root)
            return False
        if not self.confirm_transition():
            return False
        self.session.reset(song, file_path)
        self._render_song()
        return True

    def run_error_fix(self):
        import subprocess
        from superpresenter.processes import tool_command
        subprocess.Popen(tool_command('oprava_xml_tagu.py'), cwd=PROJECT_ROOT)

    def clear_editor(self):
        # 1. Smazat grafické prvky sekcí
        for s in self.sections:
            s['frame'].destroy()
        self.sections = []

        # 2. Smazat grafické řádky opakování (kromě vnitřních proměnných)
        for frame in self.repetition_frames.values():
            frame.destroy()
        
        # 3. Resetovat datové struktury
        self.repetition_frames = {}
        self.repetition_vars = {}
        self.repetitions = {}
        
if __name__ == "__main__":
    from superpresenter.logging_setup import configure_logging
    configure_logging()
    root = tk.Tk()
    root.resizable(False, False)
    app = SongEditor(root)
    app.start_recovery()
    root.mainloop()
