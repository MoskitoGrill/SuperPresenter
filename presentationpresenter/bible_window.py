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
        self.window.geometry('850x700')
        self.window.minsize(650, 580)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.translation = tk.StringVar(self.window)
        self.query = tk.StringVar(self.window)
        self.book = tk.StringVar(self.window)
        self.numbers = tk.BooleanVar(self.window, value=True)
        self.status = tk.StringVar(self.window)
        frame = ttk.Frame(self.window, padding=12)
        frame.pack(fill='both', expand=True)
        top = ttk.Frame(frame)
        top.pack(fill='x')
        ttk.Label(top, text='Překlad:').pack(side='left')
        self.translation_box = ttk.Combobox(top, textvariable=self.translation, state='readonly',
                                          values=tuple(self.service.translations), width=12)
        self.translation_box.pack(side='left', padx=8)
        self.translation_box.bind('<<ComboboxSelected>>', self.change_translation)
        ttk.Label(top, text='Nabídka vychází ze skutečně dostupných dat.').pack(side='left')
        ttk.Label(frame, text='Rychlý odkaz: Jan 3:16–18 • Jan 3:36–4:2 • Žalm 23').pack(anchor='w', pady=(12, 4))
        quick = ttk.Frame(frame)
        quick.pack(fill='x')
        self.query_entry = ttk.Entry(quick, textvariable=self.query)
        self.query_entry.pack(side='left', fill='x', expand=True)
        self.query_entry.bind('<Return>', lambda e: self.lookup())
        ttk.Button(quick, text='Najít', command=self.lookup).pack(side='left', padx=(8, 0))
        self.suggestions = tk.Listbox(frame, height=3, exportselection=False)
        self.suggestions.pack(fill='x', pady=4)
        self.suggestions.bind('<<ListboxSelect>>', self.choose_suggestion)
        self.query.trace_add('write', self.query_changed)
        pick = ttk.LabelFrame(frame, text='Výběr pasáže bez psaní', padding=8)
        pick.pack(fill='x', pady=8)
        ttk.Label(pick, text='Kniha').grid(row=0, column=0, sticky='w')
        self.book_box = ttk.Combobox(pick, textvariable=self.book, state='readonly', width=28)
        self.book_box.grid(row=0, column=1, columnspan=4, sticky='ew', padx=6)
        self.book_box.bind('<<ComboboxSelected>>', self.change_book)
        self.selectors = {}
        for row, label, prefix in ((1, 'Od', 'start'), (2, 'Do', 'end')):
            ttk.Label(pick, text=label).grid(row=row, column=0, pady=5)
            for column, field, caption in ((1, 'chapter', 'Kapitola'), (3, 'verse', 'Verš')):
                ttk.Label(pick, text=caption).grid(row=row, column=column)
                var = tk.StringVar(self.window)
                box = ttk.Combobox(pick, textvariable=var, state='readonly', width=8)
                box.grid(row=row, column=column+1, padx=6)
                self.selectors[prefix+'_'+field] = (var, box)
                box.bind('<<ComboboxSelected>>', lambda e, p=prefix, f=field: self.selector_changed(p, f))
        ttk.Button(pick, text='Zobrazit výběr', command=self.show_selection).grid(row=3, column=1, columnspan=4, sticky='e')
        options = ttk.Frame(frame)
        options.pack(fill='x')
        ttk.Checkbutton(options, text='Čísla veršů', variable=self.numbers, command=self.render).pack(side='left')
        self.copy_button = ttk.Button(options, text='Kopírovat s odkazem', command=self.copy, state='disabled')
        self.copy_button.pack(side='right')
        self.insert_button = None
        if insert is not None:
            self.insert_button = ttk.Button(options, text='Vložit nový úsek do prezentace', command=self.insert, state='disabled')
            self.insert_button.pack(side='right', padx=8)
        self.status_label = ttk.Label(frame, textvariable=self.status, wraplength=620)
        self.status_label.pack(fill='x', pady=8)
        preview_frame = ttk.Frame(frame)
        preview_frame.pack(fill='both', expand=True)
        self.preview = tk.Text(preview_frame, height=6, wrap='word', state='disabled', font=('Segoe UI', 12), padx=10, pady=10)
        scroll = ttk.Scrollbar(preview_frame, command=self.preview.yview)
        self.preview.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.preview.pack(fill='both', expand=True)
        diagnostics = ' '.join(f'{code}: {problem}' for code, problem in self.service.problems.items())
        if diagnostics:
            notice = ttk.Frame(frame)
            notice.pack(fill='x', pady=(8, 0))
            ttk.Label(notice, text='Omezení podkladů: ' + ', '.join(self.service.problems),
                      foreground='#9b4000').pack(side='left')
            ttk.Button(notice, text='Podrobnosti', command=lambda: messagebox.showinfo(
                'Dostupnost biblických dat', diagnostics, parent=self.window)).pack(side='right')
        # Reserve all controls/diagnostics before allocating the remaining height.
        preview_frame.pack_forget()
        preview_frame.pack(fill='both', expand=True)
        codes = tuple(self.service.translations)
        self.translation.set('B21' if 'B21' in codes else codes[0] if codes else '')
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
        self.set_suggestions(self.service.suggestions(name, self.translation.get()))

    def set_suggestions(self, values):
        self.suggestions.delete(0, 'end')
        for value in values:
            self.suggestions.insert('end', value)

    def choose_suggestion(self, event=None):
        chosen = self.suggestions.curselection()
        if not chosen:
            return
        book = self.suggestions.get(chosen[0])
        if self.ambiguity:
            self.lookup(book)
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

    def lookup(self, selected_book=None):
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
            self.invalidate(str(exc) + ' Klikněte na knihu v nabídce výše.')
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
            self.status.set('Vložen nový rozpracovaný úsek. Projekci potvrďte v editoru.')


def main():
    from .projection import configure_dpi
    configure_dpi()
    bible = BibleWindow()
    bible.window.mainloop()
