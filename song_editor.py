import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from copy import deepcopy
from pathlib import Path
from superpresenter.domain.editable_song import EditableSong as Song
from superpresenter.services.song_edit_session import SongEditSession
import os
import re


class SongEditor:
    def __init__(self, root, embedded=False, title_variable=None, on_saved=None, on_changed=None):
        self.root = root
        self.session = SongEditSession()
        self._loading = True
        self._pending_saved = None
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

        self.songs_dir = os.path.join(os.path.dirname(__file__), 'songs')
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
        if not embedded:
            self.root.protocol("WM_DELETE_WINDOW", self.close_window)

    def snapshot(self):
        song = deepcopy(self.session.song)
        song.title = self.title_variable.get()
        song.variants = {name: {} for name, sections in song.variants.items() if not sections}
        for section in self.sections:
            song.variants.setdefault(section['lang'], {})[section['sid']] = section['widget'].get("1.0", "end-1c")
        song.repetitions = {name: var.get() for name, var in self.repetition_vars.items()}
        song.main_repetition = self.selected_repetition.get()
        return song

    @property
    def dirty(self):
        self.session.song = self.snapshot()
        return self.session.dirty

    def _changed(self, *_):
        if self._loading:
            return
        self.session.song = self.snapshot()
        self.status_variable.set("Neuloženo" if self.session.dirty else "")
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
            for lang, sections in song.variants.items():
                for sid, content in sections.items():
                    match = re.fullmatch(r"([a-zA-Z]+)([0-9]+)", sid)
                    typ, num = (match[1], int(match[2])) if match else (sid, 0)
                    self.add_section(typ, num, content, lang, sid=sid)
            for name, value in song.repetitions.items():
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

        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=self.bg_color, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_color)

        # vytvořit okno a pamatovat si jeho id
        self._window_item = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')

        # držet šířku vnitřního okna = šířka canvasu (tedy šířka "obdélníku")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._window_item, width=e.width))

        # scrollregion podle obsahu
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * int(e.delta / 120), "units"))

        self.sections_frame = self.scrollable_frame

        if not self.embedded:
            btn_frame = tk.Frame(self.root)
            btn_frame.pack(pady=5)

            for label, typ in [("Sloka", 'v'), ("Refrén", 'r'), ("Bridge", 'b')]:
                tk.Button(btn_frame, text=label, command=lambda t=typ: self.add_section_to_all_languages(t), font=self.font).pack(side='left', padx=5)

            tk.Button(btn_frame, text="Přidat jazyk", command=self.open_language_dialog, font=self.font).pack(side='left', padx=10)

        header_frame = tk.Frame(self.root)
        header_frame.pack(anchor='w', padx=5, pady=(6, 0))
        tk.Label(header_frame, text="Opakování:", font=self.font).pack(side='left')
        tk.Button(header_frame, text=" + ", command=self.add_repetition_prompt, font=self.font).pack(side='left', padx=10)

        self.repetition_frames = {}
        self.repetition_vars = {}

        self.repetition_container = tk.Frame(self.root, bg=self.bg_color)
        self.repetition_container.pack(fill='x', padx=5)

        if not self.embedded:
            tk.Label(self.root,
                    text="v = Sloka, r = Refrén, b = Bridge | (v) = 1 Opakování | (v)*x = x Opakování | v.x = Pouze x řádek",
                    font=('Courier New', 10, 'italic'), fg='white', bg=self.bg_color).pack(anchor='w', padx=5)

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

        text = tk.Text(frame, height=1, font=self.font, wrap='word')  # přidané wrap='word'
        text.insert('end', content)
        text.pack(fill='x')

        def resize_text(event):
            lines = text.get("1.0", "end-1c").split("\n")
            text.configure(height=max(1, len(lines)))

        def modified(event):
            if text.edit_modified():
                text.edit_modified(False)
                resize_text(event)
                self._changed()
        text.edit_modified(False)
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
        self.session.reset(Song())
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
            self.session.save(target, overwrite=overwrite, rename=rename)
        except Exception as exc:
            messagebox.showerror("Chyba ukládání", f"Píseň se nepodařilo uložit:\n{exc}", parent=self.root)
            return False
        self.file_path = str(self.session.path)
        self.original_title = self.session.song.title
        self.status_variable.set("")
        self._pending_saved = (deepcopy(self.session.song), self.file_path, str(old_path) if rename and old_path else None)
        return self._notify_saved()

    def _notify_saved(self):
        pending = self._pending_saved
        self._pending_saved = None  # callback may refresh this editor through load_song
        if self.on_saved and pending:
            try:
                self.on_saved(*pending)
            except Exception as exc:
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
            messagebox.showerror("Chyba načítání", f"Nelze načíst {file_path}:\n{exc}", parent=self.root)
            return False
        return self.load_song(song, file_path)

    def load_song(self, song, file_path=None):
        if not self.confirm_transition():
            return False
        self.session.reset(song, file_path)
        self._render_song()
        return True

    def run_error_fix(self):
        import subprocess
        import sys
        path = os.path.join(os.path.dirname(__file__), 'oprava_xml_tagu.py')
        subprocess.Popen([sys.executable, path])

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
    root = tk.Tk()
    root.resizable(False, False)
    app = SongEditor(root)
    root.mainloop()
