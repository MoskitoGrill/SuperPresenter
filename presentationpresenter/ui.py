"""PP2 static slide preview. Editing and thumbnail strip belong to PP3."""
import tkinter as tk
from tkinter import messagebox, ttk
from dataclasses import replace
from .domain import Aspect
from .settings import load_settings, save_settings
from .sample import sample_document
from .layout import paginate, Typography, LayoutError
from .rendering import TkMetrics, draw

class MainWindow:
    def __init__(self, root, settings=None):
        self.root = root
        self.settings = settings or load_settings()
        self.document = sample_document()
        self.metrics = TkMetrics(root, self.settings.font_family)
        self.typography = Typography()
        root.title('PresentationPresenter — PP2')
        root.geometry(self.settings.geometry)
        root.configure(bg=self.settings.background)
        controls = tk.Frame(root, bg=self.settings.background)
        controls.pack(fill='x', padx=12, pady=8)
        for name, field in (('Sál', 'hall'), ('Stream', 'stream')):
            tk.Label(controls, text=name, bg=self.settings.background, fg='white').pack(side='left', padx=8)
            variable = tk.StringVar(value=getattr(self.document, field).aspect.value)
            tk.OptionMenu(controls, variable, *(a.value for a in Aspect), command=lambda value, key=field: self.change_aspect(key, value)).pack(side='left')
        tk.Label(root, text='Statické náhledy v původní velikosti • záložky Sál / Stream • šedá plocha je rezerva kamery', bg=self.settings.background, fg='white').pack(fill='x')
        body = tk.Frame(root)
        body.pack(fill='both', expand=True, padx=12, pady=12)
        self.sections = tk.Listbox(body, exportselection=False, width=28)
        self.sections.pack(side='left', fill='y')
        self.sections.bind('<<ListboxSelect>>', self.inspect)
        tabs = ttk.Notebook(body)
        tabs.pack(side='left', fill='both', expand=True)
        self.canvases = {}
        for field, name in (('hall', 'Sál'), ('stream', 'Stream')):
            frame = tk.Frame(tabs)
            tabs.add(frame, text=name)
            canvas = tk.Canvas(frame, bg='black', highlightthickness=0)
            horizontal = tk.Scrollbar(frame, orient='horizontal', command=canvas.xview)
            vertical = tk.Scrollbar(frame, command=canvas.yview)
            canvas.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
            horizontal.pack(side='bottom', fill='x')
            vertical.pack(side='right', fill='y')
            canvas.pack(fill='both', expand=True)
            self.canvases[field] = canvas
        self.rebuild()
        root.protocol('WM_DELETE_WINDOW', self.close)

    def rebuild(self):
        try:
            self.plan = paginate(self.document, self.metrics, self.typography)
        except LayoutError as exc:
            messagebox.showerror('Rozložení', str(exc), parent=self.root)
            return
        self.sections.delete(0, 'end')
        counts = {}
        by_id = {s.id: s for s in self.document.sections}
        for slide in self.plan.slides:
            if slide.black:
                label = 'Černý začátek' if slide.section_id is None else 'Černý předěl'
            else:
                counts[slide.section_id] = counts.get(slide.section_id, 0)+1
                label = f'{by_id[slide.section_id].title} / {counts[slide.section_id]}'
            self.sections.insert('end', label)
        self.sections.selection_set(0)
        self.inspect()

    def change_aspect(self, field, value):
        self.document = replace(self.document, **{field: replace(getattr(self.document, field), aspect=Aspect(value))})
        self.rebuild()

    def inspect(self, event=None):
        selected = self.sections.curselection()
        if selected:
            for field, canvas in self.canvases.items():
                draw(canvas, self.plan.slides[selected[0]], field, self.metrics, self.typography)

    def close(self):
        try:
            save_settings(replace(self.settings, geometry=self.root.geometry()))
        except OSError as exc:
            messagebox.showwarning('Nastavení', f'Nastavení se nepodařilo uložit: {exc}', parent=self.root)
        self.root.destroy()
