"""Independent Bible window, optionally connected to a draft insertion callback."""
import re
import tkinter as tk
from tkinter import ttk, messagebox
from .bible import BibleService, BibleError, AmbiguousBook


class BibleWindow:
    def __init__(self, parent=None, service=None, insert=None):
        self.window = tk.Toplevel(parent) if parent is not None else tk.Tk()
        self.service = service or BibleService()
        self.insert_callback = insert
        self.passage = None
        self.ambiguity = ()
        self.window.title('Bible — PresentationPresenter')
        self.window.geometry('900x650')
        self.window.minsize(650, 580)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.translation = tk.StringVar(self.window)
        self.query = tk.StringVar(self.window)
        self.book = tk.StringVar(self.window)
        self.numbers = tk.BooleanVar(self.window, value=False)
        self.status = tk.StringVar(self.window)
        bg, fg = '#555555', '#ffffff'
        font = ('Courier New', 12)
        self.window.configure(bg=bg)
        # Named styles affect only these selectors, never the editor's ttk theme.
        style = ttk.Style(self.window)
        style.configure('Bible.TCombobox', font=('Courier New', 11))
        frame = tk.Frame(self.window, bg=bg)
        frame.pack(fill='both', expand=True, padx=12, pady=12)
        frame.columnconfigure(0, minsize=310)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        self.controls = tk.Frame(frame, bg=bg, width=310)
        self.controls.grid(row=0, column=0, sticky='nsew', padx=(0, 12))
        self.controls.pack_propagate(False)
        self.preview_frame = tk.Frame(frame, bg='#666666')
        self.preview_frame.grid(row=0, column=1, sticky='nsew')

        def label(parent, text, **kwargs):
            return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kwargs)

        def button(parent, text, command, **kwargs):
            return tk.Button(parent, text=text, command=command, bg='#444444', fg=fg,
                             activebackground='#666666', activeforeground=fg,
                             disabledforeground='#999999', relief='flat',
                             font=('Courier New', 11, 'bold'), padx=6, pady=2, **kwargs)

        tk.Label(self.controls, text='Odkaz (např. Jan 3:16–18)', bg=bg, fg=fg,
                 font=('Courier New', 10)).pack(anchor='w')
        quick = tk.Frame(self.controls, bg=bg)
        quick.pack(fill='x', pady=(4, 0))
        self.query_entry = tk.Entry(quick, textvariable=self.query, font=('Courier New', 11), width=20)
        self.query_entry.bind('<Return>', self.query_enter)
        self.query_entry.bind('<Down>', lambda e: self.move_suggestion(1))
        self.query_entry.bind('<Up>', lambda e: self.move_suggestion(-1))
        self.query_entry.bind('<Escape>', lambda e: (self.hide_suggestions(), 'break')[1])
        self.query_entry.bind('<FocusOut>', self.query_focus_out)
        button(quick, 'Najít', self.lookup).pack(side='right', padx=(6, 0))
        self.query_entry.pack(side='left', fill='x', expand=True)
        self.suggestion_popup = tk.Toplevel(self.window)
        self.suggestion_popup.withdraw()
        self.suggestion_popup.overrideredirect(True)
        self.suggestion_popup.transient(self.window)
        self.suggestions = tk.Listbox(self.suggestion_popup, height=6, exportselection=False,
                                      font=('Courier New', 10), bg='white', fg='black',
                                      selectbackground='#0078d7', selectforeground='white',
                                      relief='solid', borderwidth=1, highlightthickness=0,
                                      takefocus=False)
        suggestion_scroll = ttk.Scrollbar(self.suggestion_popup, command=self.suggestions.yview)
        self.suggestions.configure(yscrollcommand=suggestion_scroll.set)
        suggestion_scroll.pack(side='right', fill='y')
        self.suggestions.pack(fill='both', expand=True)
        self.suggestions.bind('<ButtonRelease-1>', self.choose_suggestion)
        self.suggestions.bind('<Return>', self.query_enter)
        self.suggestions.bind('<Escape>', lambda e: (self.hide_suggestions(), self.query_entry.focus_set(), 'break')[-1])
        self.window.bind('<ButtonPress-1>', self.dismiss_suggestions, add='+')
        self.window.bind('<Configure>', self.position_suggestions, add='+')
        self.window.bind('<Unmap>', lambda e: self.hide_suggestions() if e.widget is self.window else None, add='+')
        self.query.trace_add('write', self.query_changed)
        self.translation_box = ttk.Combobox(self.controls, textvariable=self.translation, state='readonly',
                                          values=tuple(self.service.translations), width=26,
                                          style='Bible.TCombobox', font=('Courier New', 11))
        self.translation_box.pack(fill='x', pady=(6, 8))
        self.translation_box.bind('<<ComboboxSelected>>', self.change_translation)
        self.book_box = ttk.Combobox(self.controls, textvariable=self.book, state='readonly', width=26,
                                     style='Bible.TCombobox', font=('Courier New', 11))
        self.book_box.pack(fill='x', pady=(0, 8))
        self.book_box.bind('<<ComboboxSelected>>', self.change_book)
        pick = tk.Frame(self.controls, bg=bg)
        pick.pack(fill='x')
        pick.columnconfigure(1, weight=1)
        pick.columnconfigure(3, weight=1)
        self.selectors = {}
        for row, field, caption in ((0, 'chapter', 'Kapitoly:'), (2, 'verse', 'Verše:')):
            label(pick, caption).grid(row=row, column=0, columnspan=4, sticky='w', pady=(4, 2))
            for column, prefix, caption in ((0, 'start', 'Od:'), (2, 'end', 'Do:')):
                label(pick, caption).grid(row=row+1, column=column, sticky='w')
                var = tk.StringVar(self.window)
                box = ttk.Combobox(pick, textvariable=var, state='readonly', width=5,
                                   style='Bible.TCombobox', font=('Courier New', 11))
                box.grid(row=row+1, column=column+1, sticky='ew', padx=(4, 10))
                self.selectors[prefix+'_'+field] = (var, box)
                box.bind('<<ComboboxSelected>>', lambda e, p=prefix, f=field: self.selector_changed(p, f))
        self.copy_button = button(self.controls, 'Zkopírovat do schránky', self.copy, state='disabled')
        self.copy_button.pack(fill='x', pady=2)
        tk.Checkbutton(self.controls, text='Zobrazit čísla veršů', variable=self.numbers,
                       command=self.render, bg=bg, fg=fg, selectcolor='#444444',
                       activebackground=bg, activeforeground=fg, font=('Courier New', 11)).pack(anchor='w', pady=2)
        self.insert_button = None
        if insert is not None:
            self.insert_button = button(self.controls, 'Vložit do prezentace', self.insert, state='disabled')
            self.insert_button.pack(fill='x', pady=2)
        self.status_label = tk.Label(self.controls, textvariable=self.status, wraplength=290,
                                     bg=bg, fg=fg, font=('Courier New', 10), anchor='w', justify='left')
        self.status_label.pack(fill='x', pady=4)
        self.preview = tk.Text(self.preview_frame, width=1, height=6, wrap='word', state='disabled',
                               font=font, bg='#666666', fg=fg, relief='sunken', borderwidth=1,
                               highlightthickness=0, padx=12, pady=12)
        scroll = tk.Scrollbar(self.preview_frame, command=self.preview.yview)
        self.preview.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.preview.pack(fill='both', expand=True)
        diagnostics = ' '.join(f'{code}: {problem}' for code, problem in self.service.problems.items())
        if diagnostics:
            notice = tk.Frame(self.controls, bg=bg)
            notice.pack(fill='x', pady=(8, 0))
            tk.Label(notice, text='Podklady: ' + ', '.join(self.service.problems),
                     bg=bg, fg='#ffe2ad', font=('Courier New', 8)).pack(anchor='w')
            button(notice, 'Podrobnosti', lambda: messagebox.showinfo(
                'Dostupnost biblických dat', diagnostics, parent=self.window)).pack(anchor='w')
        codes = tuple(self.service.translations)
        self.translation.set('CSP' if 'CSP' in codes else codes[0] if codes else '')
        self.change_translation()
        self.query_entry.focus_set()

    def alive(self):
        try:
            return bool(self.window.winfo_exists())
        except tk.TclError:
            return False

    def close(self):
        if self.alive():
            self.window.destroy()
        self.insert_callback = None

    def invalidate(self, message='Vyberte pasáž nebo zadejte odkaz.'):
        self.passage = None
        self.status.set(message)
        self.render()

    def set_choices(self, key, values, preferred=None):
        var, box = self.selectors[key]
        values = tuple(str(v) for v in values)
        box.configure(values=values)
        choice = str(preferred) if preferred is not None else var.get()
        var.set(choice if choice in values else values[0] if values else '')

    def change_translation(self, event=None):
        books = self.service.books(self.translation.get())
        self.book_box.configure(values=books)
        if self.book.get() not in books:
            self.book.set('Jan' if 'Jan' in books else books[0] if books else '')
        self.change_book()
        if self.query.get().strip():
            self.lookup()

    def change_book(self, event=None):
        self.ambiguity = ()
        chapters = self.service.chapters(self.translation.get(), self.book.get())
        for prefix in ('start', 'end'):
            self.set_choices(prefix+'_chapter', chapters)
            self.update_verses(prefix)
        self.show_selection()

    def update_verses(self, prefix):
        chapter = self.selectors[prefix+'_chapter'][0].get()
        values = self.service.verses(self.translation.get(), self.book.get(), int(chapter)) if chapter else ()
        self.set_choices(prefix+'_verse', values)

    def selector_changed(self, prefix, field):
        if field == 'chapter':
            self.update_verses(prefix)
        self.show_selection()

    def show_selection(self):
        if not self.service.translations:
            self.invalidate('Nejsou dostupná čitelná biblická data ve složce bible vedle aplikace.')
            return
        try:
            values = [int(self.selectors[k][0].get()) for k in ('start_chapter', 'start_verse', 'end_chapter', 'end_verse')]
            self.passage = self.service.passage(self.translation.get(), self.book.get(), *values)
            self.status.set(self.passage.reference)
            self.render()
        except (BibleError, ValueError) as exc:
            self.invalidate(str(exc))

    def query_changed(self, *args):
        self.ambiguity = ()
        self.invalidate('Potvrďte rychlý odkaz tlačítkem Najít nebo Enter.')
        # Chapter starts after a space; retain a leading number of an epistle.
        name = re.split(r'\s+\d', self.query.get().strip(), maxsplit=1)[0]
        values = self.service.suggestions(name, self.translation.get()) if name else ()
        # A complete chapter/verse suffix no longer needs book completion.
        self.set_suggestions(values if name == self.query.get().strip() else ())

    def hide_suggestions(self):
        self.suggestion_popup.withdraw()

    def position_suggestions(self, event=None):
        if event is not None and event.widget is not self.window:
            return
        if not self.suggestions.size():
            return
        height = min(6, self.suggestions.size()) * int(self.suggestions.tk.call(
            'font', 'metrics', self.suggestions.cget('font'), '-linespace')) + 4
        x = self.query_entry.winfo_rootx()
        y = self.query_entry.winfo_rooty() + self.query_entry.winfo_height()
        width = max(240, self.query_entry.winfo_width())
        if y + height > self.window.winfo_screenheight():
            y = self.query_entry.winfo_rooty() - height
        self.suggestion_popup.geometry(f'{width}x{height}{x:+d}{y:+d}')

    def dismiss_suggestions(self, event):
        if event.widget is not self.query_entry:
            self.hide_suggestions()

    def query_focus_out(self, event):
        if self.window.focus_displayof() is not self.suggestions:
            self.hide_suggestions()

    def move_suggestion(self, direction):
        if self.suggestions.size():
            self.position_suggestions()
            self.suggestion_popup.deiconify()
            selected = self.suggestions.curselection()
            index = max(0, min(self.suggestions.size()-1,
                              selected[0]+direction if selected else 0 if direction > 0 else self.suggestions.size()-1))
            self.suggestions.selection_clear(0, 'end')
            self.suggestions.selection_set(index)
            self.suggestions.activate(index)
            self.suggestions.see(index)
        return 'break'

    def query_enter(self, event=None):
        if self.suggestion_popup.winfo_ismapped() and self.suggestions.curselection():
            self.choose_suggestion()
        else:
            self.lookup()
        return 'break'

    def set_suggestions(self, values):
        self.suggestions.delete(0, 'end')
        for value in values:
            self.suggestions.insert('end', value)
        if values:
            self.position_suggestions()
            self.suggestion_popup.deiconify()
            self.suggestion_popup.lift()
        else:
            self.hide_suggestions()

    def choose_suggestion(self, event=None):
        chosen = self.suggestions.curselection()
        if not chosen:
            return
        book = self.suggestions.get(chosen[0])
        if self.ambiguity:
            self.lookup(book)
            self.query_entry.focus_set()
            return
        match = re.search(r'\s+(\d+\s*(?::.*)?(?:[-–—].*)?)$', self.query.get().strip())
        self.query.set(book + (' ' + match.group(1) if match else ' '))
        if match:
            self.lookup()
        else:
            self.book.set(book)
            self.change_book()
        self.query_entry.focus_set()
        self.query_entry.icursor('end')
        self.hide_suggestions()

    def lookup(self, selected_book=None):
        self.hide_suggestions()
        try:
            self.passage = self.service.parse(self.translation.get(), self.query.get(), selected_book)
            self.ambiguity = ()
            self.book.set(self.passage.book)
            chapters = self.service.chapters(self.translation.get(), self.book.get())
            for prefix, verse in (('start', self.passage.verses[0]), ('end', self.passage.verses[-1])):
                self.set_choices(prefix+'_chapter', chapters, verse[0])
                self.update_verses(prefix)
                self.set_choices(prefix+'_verse', self.service.verses(self.translation.get(), self.book.get(), verse[0]), verse[1])
            self.status.set(self.passage.reference)
            self.render()
        except AmbiguousBook as exc:
            self.ambiguity = exc.candidates
            self.set_suggestions(exc.candidates)
            self.invalidate(str(exc) + ' Vyberte knihu z rozbalovací nabídky.')
        except BibleError as exc:
            self.ambiguity = ()
            self.invalidate(str(exc))

    def render(self):
        self.preview.configure(state='normal')
        self.preview.delete('1.0', 'end')
        if self.passage:
            self.preview.insert('1.0', self.passage.clipboard_text(self.numbers.get()))
        self.preview.configure(state='disabled')
        state = 'normal' if self.passage else 'disabled'
        self.copy_button.configure(state=state)
        if self.insert_button:
            self.insert_button.configure(state=state)

    def copy(self):
        if self.passage:
            self.window.clipboard_clear()
            self.window.clipboard_append(self.passage.clipboard_text(self.numbers.get()))
            self.status.set('Pasáž a odkaz byly zkopírovány.')

    def insert(self):
        if self.passage and self.insert_callback:
            self.insert_callback(self.passage.section(self.numbers.get()))
            self.status.set('Pasáž vložena do návrhu. Projekci potvrďte v editoru.')


def main():
    from .projection import configure_dpi
    configure_dpi()
    bible = BibleWindow()
    bible.window.mainloop()
