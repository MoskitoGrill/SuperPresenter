"""Review a detached import before a single draft mutation."""
import tkinter as tk
from tkinter import ttk
from .pptx_import import read_pptx
from .layout import paginate, LayoutError
from .rendering import draw

class ImportWindow:
    def __init__(self, owner, path):
        self.owner, self.path = owner, path
        self.result = self.plan = None
        self.index = 0
        self.accepted = None
        self.window = tk.Toplevel(owner.root)
        self.window.title('Import PPTX — kontrola před vložením')
        self.window.geometry('1050x760')
        self.window.minsize(760, 600)
        self.window.transient(owner.root)
        self.window.protocol('WM_DELETE_WINDOW', self.window.destroy)
        self.join = tk.BooleanVar(value=True)
        self.join_control = tk.Checkbutton(self.window, text='Spojit sousední snímky se stejným neprázdným odkazem\nČerný předěl spojení vždy zastaví.',
                        variable=self.join, command=self.refresh, justify='left', wraplength=960)
        self.join_control.pack(anchor='w', padx=12)
        self.summary = tk.StringVar()
        self.summary_label = tk.Label(self.window, textvariable=self.summary, anchor='w', justify='left', wraplength=960)
        self.summary_label.pack(fill='x', padx=12)
        footer = tk.Frame(self.window)
        footer.pack(side='bottom', fill='x', padx=12, pady=10)
        self.insert = ttk.Button(footer, text='Vložit za vybraný úsek', command=self.accept)
        self.insert.pack(side='right')
        ttk.Button(footer, text='Zrušit', command=self.window.destroy).pack(side='right', padx=8)
        navigation = tk.Frame(self.window)
        navigation.pack(side='bottom', fill='x', padx=12)
        ttk.Button(navigation, text='←', command=lambda: self.move(-1)).pack(side='left')
        self.position = tk.StringVar()
        tk.Label(navigation, textvariable=self.position).pack(side='left', padx=12)
        ttk.Button(navigation, text='→', command=lambda: self.move(1)).pack(side='left')
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill='both', expand=True, padx=12, pady=8)
        preview = tk.Frame(notebook)
        notebook.add(preview, text='Výsledek — sál a stream')
        self.canvases = {}
        for field, title in (('hall', 'Sál'), ('stream', 'Stream — rezerva kamery')):
            frame = tk.Frame(preview)
            frame.pack(side='left', fill='both', expand=True)
            tk.Label(frame, text=title).pack()
            canvas = tk.Canvas(frame, bg='black', highlightthickness=0)
            canvas.pack(fill='both', expand=True, padx=3)
            canvas.bind('<Configure>', lambda e: self.render())
            self.canvases[field] = canvas
        details = tk.Frame(notebook)
        notebook.add(details, text='Obsah, mapování a upozornění')
        self.details = tk.Text(details, wrap='word', width=60)
        scroll = ttk.Scrollbar(details, command=self.details.yview)
        self.details.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.details.pack(fill='both', expand=True)
        owner.appearance.apply(self.window)
        self.details.configure(font=owner.appearance.text)
        self.window.bind('<Configure>', self.resize_labels, add='+')
        self.refresh()
        self.window.grab_set()

    def resize_labels(self, event):
        if event.widget is self.window:
            for widget in (self.join_control, self.summary_label):
                widget.configure(wraplength=max(300, event.width-50))

    def refresh(self):
        self.plan = self.result = None
        try:
            self.result = read_pptx(self.path, style=self.owner.default_content_style(), join_same=self.join.get(),
                                    hall=self.owner.document.hall, stream=self.owner.document.stream)
            from .storage import validate, encode
            encode(validate(self.result.document))
            self.plan = paginate(self.result.document, self.owner.metrics, self.owner.typography)
            self.index = 0
            self.summary.set(f'{len(self.result.document.sections)} úseků → {len(self.plan.slides)} snímků včetně předělů; '
                             f'{len(self.result.warnings)} upozornění.')
            lines = ['MAPOVÁNÍ PŮVODNÍCH SNÍMKŮ', *self.result.mapping, '', 'UPOZORNĚNÍ',
                     *(self.result.warnings or ('Žádná další upozornění.',)), '', 'PŘEVEDENÝ OBSAH']
            for i, section in enumerate(self.result.document.sections, 1):
                lines.extend([f'\nÚsek {i}: {section.title or "Bez názvu"} — obrázky: {len(section.images)}'])
                for block in section.blocks:
                    marker = '• ' if block.kind.value == 'bullet' else '1. ' if block.kind.value == 'numbered' else ''
                    lines.append('  '*block.level + marker + ''.join(r.text for r in block.runs))
            content = '\n'.join(lines)
        except (OSError, ValueError, LayoutError) as exc:
            self.summary.set('Import nelze vložit. Původní prezentace se nemění.')
            content = str(exc)
        self.details.configure(state='normal')
        self.details.delete('1.0', 'end')
        self.details.insert('1.0', content)
        self.details.configure(state='disabled')
        self.update_button()
        self.render()

    def update_button(self):
        self.insert.configure(state='normal' if self.plan else 'disabled')

    def move(self, delta):
        if self.plan:
            self.index = max(0, min(len(self.plan.slides)-1, self.index+delta))
            self.render()

    def render(self):
        if not self.plan:
            for canvas in self.canvases.values():
                canvas.delete('all')
            self.position.set('Bez platného náhledu')
            return
        slide = self.plan.slides[self.index]
        self.position.set(f'{self.index+1} / {len(self.plan.slides)}' + (' — černý předěl' if slide.black else ''))
        for field, canvas in self.canvases.items():
            from .layout import geometry
            w, h, _, _ = geometry(getattr(self.result.document, field))
            scale = min(max(1, canvas.winfo_width())/w, max(1, canvas.winfo_height())/h)
            draw(canvas, slide, field, self.owner.metrics, self.owner.typography, scale=scale, resize_canvas=False)
            canvas.move('all', (canvas.winfo_width()-w*scale)/2, (canvas.winfo_height()-h*scale)/2)

    def accept(self):
        if self.plan:
            self.accepted = self.result.document
            self.window.destroy()
