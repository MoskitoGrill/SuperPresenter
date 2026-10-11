"""PP1 source inspector; deliberately not a projection/layout preview."""
import tkinter as tk
from tkinter import messagebox
from dataclasses import replace
from .domain import TextSection, BlockKind, Aspect
from .settings import load_settings, save_settings
from .sample import sample_document

class MainWindow:
    def __init__(self, root, settings=None):
        self.root = root
        self.settings = settings or load_settings()
        self.document = sample_document()
        root.title('PresentationPresenter — PP1')
        root.geometry(self.settings.geometry)
        root.configure(bg=self.settings.background)
        font = (self.settings.font_family, 12)
        def label(parent, text):
            widget = tk.Label(parent, text=text, bg=self.settings.background, fg=self.settings.foreground, font=font, anchor='w')
            widget.pack(fill='x', padx=12, pady=6)
            return widget
        label(root, 'PresentationPresenter • samostatný základ')
        label(root, 'Zdrojový dokument — ukázka. Dělení snímků a projekce budou doplněny v dalších etapách.')
        outputs = tk.Frame(root, bg=self.settings.background)
        outputs.pack(fill='x')
        for name, field in (('Sál', 'hall'), ('Stream', 'stream')):
            frame = tk.Frame(outputs, bg=self.settings.background)
            frame.pack(side='left', padx=12)
            label(frame, name)
            variable = tk.StringVar(value=getattr(self.document, field).aspect.value)
            menu = tk.OptionMenu(frame, variable, *(a.value for a in Aspect), command=lambda value, key=field: self.change_aspect(key, value))
            menu.configure(bg=self.settings.panel, fg=self.settings.foreground, font=font, highlightthickness=0)
            menu.pack()
        label(root, 'Stream: rezervovaná pravá dolní čtvrtina + odstup. Černý začátek a předěl po úseku jsou zapnuté.')
        body = tk.Frame(root, bg=self.settings.background)
        body.pack(fill='both', expand=True, padx=12, pady=12)
        self.sections = tk.Listbox(body, bg=self.settings.panel, fg=self.settings.foreground, font=font, exportselection=False, width=25)
        self.sections.pack(side='left', fill='y')
        self.text = tk.Text(body, bg='#222222', fg=self.settings.foreground, font=font, wrap='word', padx=16, pady=16)
        self.text.pack(side='left', fill='both', expand=True, padx=(12, 0))
        for section in self.document.sections:
            self.sections.insert('end', section.title)
        self.sections.bind('<<ListboxSelect>>', self.inspect)
        self.sections.selection_set(0)
        self.inspect()
        root.protocol('WM_DELETE_WINDOW', self.close)

    def change_aspect(self, field, value):
        self.document = replace(self.document, **{field: replace(getattr(self.document, field), aspect=Aspect(value))})

    def inspect(self, event=None):
        selected = self.sections.curselection()
        if not selected:
            return
        section = self.document.sections[selected[0]]
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.insert('end', section.title + '\n' + section.reference + '\n\n')
        if isinstance(section, TextSection):
            for block in section.blocks:
                if block.kind == BlockKind.BULLET:
                    self.text.insert('end', '• ')
                for run in block.runs:
                    tag = run.id
                    weight = 'bold' if run.style.bold else 'normal'
                    slant = 'italic' if run.style.italic else 'roman'
                    self.text.tag_configure(tag, foreground=run.style.color, underline=run.style.underline,
                                            font=(self.settings.font_family, 16, weight, slant))
                    self.text.insert('end', run.text, tag)
                self.text.insert('end', '\n\n')
        self.text.configure(state='disabled')

    def close(self):
        try:
            save_settings(replace(self.settings, geometry=self.root.geometry()))
        except OSError as exc:
            messagebox.showwarning('Nastavení', f'Nastavení se nepodařilo uložit: {exc}', parent=self.root)
        self.root.destroy()
