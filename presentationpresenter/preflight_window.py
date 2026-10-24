"""Non-modal draft report; never navigates the live projection."""
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from .appearance import appearance


class PreflightWindow:
    def __init__(self, owner):
        self.owner = owner
        self.win = tk.Toplevel(owner.root)
        self.win.title('Kontrola před projekcí')
        self.win.geometry('860x480')
        self.summary = tk.StringVar()
        self.summary_label = tk.Label(self.win, textvariable=self.summary, anchor='w', justify='left', wraplength=800)
        self.summary_label.pack(fill='x', padx=12, pady=10)
        # Reserve the footer before allocating the expanding report, including
        # large system fonts. The buttons must remain reachable in a short window.
        footer = tk.Frame(self.win)
        footer.pack(side='bottom', fill='x')
        frame = tk.Frame(self.win)
        frame.pack(fill='both', expand=True, padx=12)
        theme = appearance(owner.root)
        style = ttk.Style(owner.root)
        row_height = tkfont.Font(root=owner.root, font=theme.text).metrics('linespace')+8
        style.configure('PP.Preflight.Treeview', font=theme.text, rowheight=row_height)
        style.configure('PP.Preflight.Treeview.Heading', font=theme.text)
        self.tree = ttk.Treeview(frame, columns=('severity', 'section', 'output', 'message'), show='headings', selectmode='browse', style='PP.Preflight.Treeview')
        for key, title, width in (('severity', 'Stav', 90), ('section', 'Úsek', 150), ('output', 'Výstup', 75), ('message', 'Problém', 480)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, stretch=key == 'message')
        vertical = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        horizontal = ttk.Scrollbar(frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.detail = tk.StringVar()
        self.detail_label = tk.Label(footer, textvariable=self.detail, anchor='w', justify='left', wraplength=800)
        self.detail_label.pack(fill='x', padx=12, pady=6)
        actions = tk.Frame(footer)
        actions.pack(fill='x', padx=12, pady=10)
        self.go = tk.Button(actions, text='Přejít na problém', command=self.navigate)
        self.go.pack(side='left')
        tk.Button(actions, text='Znovu zkontrolovat', command=self.refresh).pack(side='left', padx=8)
        tk.Button(actions, text='Zavřít', command=self.win.destroy).pack(side='right')
        self.tree.bind('<<TreeviewSelect>>', self.selected)
        self.tree.bind('<Double-1>', self.navigate)
        self.tree.bind('<Return>', self.navigate)
        self.win.bind('<Configure>', self.resize)
        appearance(owner.root).apply(self.win)
        self.tree.configure(style='PP.Preflight.Treeview')
        self.refresh()

    def resize(self, event):
        if event.widget is self.win:
            for child in (self.summary_label, self.detail_label):
                child.configure(wraplength=max(200, event.width-24))

    def refresh(self):
        self.issues = self.owner.collect_preflight()
        self.tree.delete(*self.tree.get_children())
        sections = {s.id: f'{n}. '+(' • '.join(p for p in (s.title, s.reference) if p) or 'Bez názvu') for n, s in enumerate(self.owner.document.sections, 1)}
        for index, issue in enumerate(self.issues):
            self.tree.insert('', 'end', iid=str(index), values=('Chyba' if issue.blocking else 'Upozornění', sections.get(issue.section_id, 'Výstupy / dokument'), {'hall': 'Sál', 'stream': 'Stream'}.get(issue.output, '—'), issue.message))
        count = sum(i.blocking for i in self.issues)
        self.summary.set(f'Rozpracovaná verze: {count} chyb, {len(self.issues)-count} upozornění.\n'+
                         ('Před spuštěním opravte chyby.' if count else 'Kontrolované položky jsou v pořádku; upozornění posuďte před projekcí.')+
                         '\nPo úpravě použijte Znovu zkontrolovat. Fyzické monitory a stream tím nejsou ověřeny.')
        if self.issues:
            self.tree.selection_set('0')
        self.selected()

    def selected(self, event=None):
        selection = self.tree.selection()
        self.go.configure(state='normal' if selection else 'disabled')
        self.detail.set(self.issues[int(selection[0])].message if selection else '')

    def navigate(self, event=None):
        selection = self.tree.selection()
        if selection:
            self.owner.navigate_preflight(self.issues[int(selection[0])])
