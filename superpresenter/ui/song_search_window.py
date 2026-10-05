"""Search dialog; repository work runs outside the Tk event loop."""
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tkinter as tk
from tkinter import ttk, font as tkfont
from superpresenter.ui.scrollbars import Scrollbar
from superpresenter.ui.mousewheel import bind_widget_wheel

from superpresenter.services.song_search import SongSearch
from superpresenter.windows_shell import style_title_bar

logger = logging.getLogger(__name__)


def in_playlist(gui, path):
    key = os.path.normcase(str(Path(path).resolve()))
    return any(os.path.normcase(str(Path(gui.sources[i].path).resolve())) == key
               for i in gui.sourceList)


def add_result(gui, path):
    """Use the existing validated, dirty-protected transition (13A permits edits)."""
    if in_playlist(gui, path):
        return 'Píseň už je v playlistu.'
    if gui.loadSource(str(path)):
        return 'Přidáno do playlistu.'
    return 'Píseň nebyla přidána.'


class SongSearchWindow:
    def __init__(self, gui):
        self.gui = gui
        self.win = tk.Toplevel(gui.win)
        self.win.title('Hledat píseň')
        self.win.geometry('900x480')
        self.win.rowconfigure(1, weight=1)
        self.win.columnconfigure(0, weight=1)
        self.query = tk.StringVar(self.win)
        self.entry = tk.Entry(self.win, textvariable=self.query)
        self.entry.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        self.browse_button = tk.Button(self.win, text='+', width=3, command=self.browse_files)
        self.browse_button.grid(row=0, column=1, sticky='e', padx=(0, 10), pady=10)
        self.tree = ttk.Treeview(self.win, columns=('title', 'snippet'), show='headings')
        for key, label, width in [('title', 'Název písně', 240), ('snippet', 'Úryvek', 610)]:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width)
        self.tree.grid(row=1, column=0, sticky='nsew', padx=(10, 0))
        scroll = Scrollbar(self.win, orient='vertical', command=self.tree.yview)
        scroll.grid(row=1, column=1, sticky='ns', padx=(0, 10))
        self.tree.configure(yscrollcommand=scroll.set)
        bind_widget_wheel(self.tree)
        self.status = tk.Label(self.win, text='Načítám knihovnu…')
        self.status.grid(row=2, column=0, sticky='w', padx=10, pady=10)
        self.add_button = tk.Button(self.win, text='Přidat', command=self.add, state='disabled')
        self.add_button.grid(row=3, column=0, sticky='e', padx=10, pady=(0, 10))
        self.apply_style()
        self.results = []
        self.pending = None
        self.poll = None
        self.ready = False
        self.search_index = SongSearch(Path(gui.dir) / 'songs')
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='song-search')
        self.future = self.executor.submit(self.search_index.rebuild)
        self.query.trace_add('write', self.schedule)
        self.entry.bind('<Return>', self.search)
        self.tree.bind('<Double-1>', self.add)
        self.tree.bind('<<TreeviewSelect>>', self.selection_changed)
        self.win.protocol('WM_DELETE_WINDOW', self.close)
        self.win.bind('<Destroy>', self.destroyed, add='+')
        self.check_index()
        self.entry.focus_set()
        style_title_bar(self.win)

    def browse_files(self):
        try:
            self.gui.addSource()
            self.search()  # Refresh playlist marks after the existing file picker.
        except Exception:
            logger.exception('Opening song files failed')
            self.status.configure(text='Otevření souborů selhalo. Podrobnosti jsou v logu.')

    def apply_style(self):
        """Reuse the active application's colors and fonts, without changing its theme."""
        gui = self.gui
        background = gui.win.cget('background')
        foreground = gui.sourceLab.cget('foreground')
        surface = gui.stepsList.cget('background')
        text = gui.stepsList.cget('foreground')
        selection = gui.stepsList.cget('selectbackground')
        font = gui.stepsList.cget('font')
        self.win.configure(background=background)
        self.status.configure(background=background, foreground=foreground,
                              font=gui.sourceTitleEntry.cget('font'))
        self.entry.configure(**{key: gui.sourceTitleEntry.cget(key) for key in
                               ('background', 'foreground', 'font', 'selectbackground',
                                'selectforeground', 'insertbackground', 'relief')})
        self.add_button.configure(**{key: gui.openSource.cget(key) for key in
                                    ('background', 'foreground', 'font', 'activebackground',
                                     'activeforeground', 'relief', 'borderwidth')})
        self.browse_button.configure(**{key: gui.openSource.cget(key) for key in
                                       ('background', 'foreground', 'font', 'activebackground',
                                        'activeforeground', 'relief', 'borderwidth')})
        style = ttk.Style(self.win)
        name = 'SongSearch.Treeview'
        style.configure(name, background=surface, fieldbackground=surface,
                        foreground=text, font=font, borderwidth=0,
                        rowheight=2 * tkfont.Font(root=self.win, font=font).metrics('linespace') + 14)
        style.map(name, background=[('selected', selection)],
                  foreground=[('selected', gui.stepsList.cget('selectforeground'))])
        style.configure(name + '.Heading', background=background, foreground=foreground,
                        font=gui.openSource.cget('font'), relief='flat')
        # These headings are labels, with no sorting or click action.
        style.map(name + '.Heading',
                  background=[('pressed', background), ('active', background)],
                  foreground=[('pressed', foreground), ('active', foreground)],
                  relief=[('pressed', 'flat'), ('active', 'flat')])
        self.tree.configure(style=name)
        self.tree.column('title', anchor='w')
        self.tree.column('snippet', anchor='w')
        horizontal = Scrollbar(self.win, orient='horizontal', command=self.tree.xview)
        horizontal.grid(row=2, column=0, sticky='ew', padx=10)
        self.tree.configure(xscrollcommand=horizontal.set)
        self.status.grid(row=3)
        self.add_button.grid(row=4)

    def check_index(self):
        self.poll = None
        if not self.future.done():
            self.poll = self.win.after(50, self.check_index)
            return
        try:
            self.future.result()
            self.ready = True
            self.search()
        except Exception:
            logger.exception('Song search indexing failed')
            self.status.configure(text='Knihovnu nelze načíst. Podrobnosti jsou v logu.')
        finally:
            self.executor.shutdown(wait=False)

    def schedule(self, *_):
        if self.pending is not None:
            self.win.after_cancel(self.pending)
        self.pending = self.win.after(200, self.search)

    def search(self, *_):
        if self.pending is not None:
            self.win.after_cancel(self.pending)
            self.pending = None
        if not self.ready:
            return
        try:
            self.results = self.search_index.search(self.query.get())
            self.tree.delete(*self.tree.get_children())
            for i, result in enumerate(self.results):
                title = result.display_title + (' (v playlistu)' if in_playlist(self.gui, result.path) else '')
                self.tree.insert('', 'end', iid=str(i), values=(title, result.snippet))
            summary = f'Výsledků: {len(self.results)}' if self.query.get().strip() else 'Zadejte název nebo část textu písně.'
            if self.search_index.failures:
                summary += f' Přeskočeno souborů: {len(self.search_index.failures)}.'
            self.status.configure(text=summary)
            self.selection_changed()
        except Exception:
            logger.exception('Song search failed')
            self.status.configure(text='Vyhledávání selhalo. Podrobnosti jsou v logu.')

    def selection_changed(self, *_):
        selected = self.tree.selection()
        duplicate = bool(selected) and in_playlist(self.gui, self.results[int(selected[0])].path)
        self.add_button.configure(state='normal' if selected and not duplicate else 'disabled')

    def add(self, event=None):
        if event is not None:
            row = self.tree.identify_row(event.y)
            if not row:
                return
            self.tree.selection_set(row)
        selected = self.tree.selection()
        if not selected:
            return
        try:
            message = add_result(self.gui, self.results[int(selected[0])].path)
            self.search()
            self.status.configure(text=message)
        except Exception:
            logger.exception('Adding song search result failed')
            self.status.configure(text='Přidání selhalo. Podrobnosti jsou v logu.')

    def destroyed(self, event):
        if event.widget is self.win:
            for timer in (self.pending, self.poll):
                if timer is not None:
                    self.win.after_cancel(timer)
            self.pending = self.poll = None
            self.executor.shutdown(wait=False, cancel_futures=True)

    def close(self):
        self.win.destroy()
