"""Movable projection panel and transactional profile editor."""
import tkinter as tk
from tkinter import ttk
from dataclasses import replace
from .profiles import ProjectionPreset, OutputPreset, defaults, load_profiles
from .domain import Aspect
from .projection import monitor_labels
from .monitor_editor import ProfileEditor, ProfileLoader


class ProjectionControls:
    def __init__(self, owner, parent):
        self.owner = owner
        self.editor = None
        self.enabled = {'hall': True, 'stream': False}
        self.fullscreen = {'hall': True, 'stream': True}
        self.selected = tk.StringVar(value='Jen sál')
        self.output_index = 0
        self.monitor_names = ()
        self.load_error = ''
        try:
            self.profiles = load_profiles()
        except (OSError, ValueError) as exc:
            self.profiles = defaults()
            self.load_error = str(exc)
        if self.selected.get() not in {p.name for p in self.profiles}:
            self.selected.set(self.profiles[0].name)
        self.applied_name = self.selected.get()
        self.frame = tk.Frame(parent, bg='#555555', bd=1, relief='solid', padx=8, pady=6)
        self.frame.pack(side='right', anchor='n', padx=8, pady=(0, 6))
        row = tk.Frame(self.frame, bg='#555555')
        row.grid(row=0, column=0, columnspan=3, sticky='ew')
        def button(label, command):
            b = tk.Button(row, text=label, command=command, bg='#444444', fg='white',
                          activebackground='#666666', activeforeground='white',
                          relief='flat', font=('Courier New', 11, 'bold'), width=4, takefocus=False)
            b.pack(side='left', padx=2)
            return b
        self.previous = button('<', lambda: self.browse(-1))
        self.counter = tk.StringVar()
        tk.Label(row, textvariable=self.counter, bg='#555555', fg='white', width=7, font=('Courier New', 11)).pack(side='left')
        self.following = button('>', lambda: self.browse(1))
        self.add_button = button('+', self.add_output)
        self.load_button = button('load', self.load_profile)
        self.edit_button = button('edit', self.open_editor)
        self.display_value = tk.StringVar()
        self.style_value = tk.StringVar()
        self.display_ids = {}
        for r, label in ((1, 'Display'), (2, 'Style')):
            tk.Label(self.frame, text=label, bg='#555555', fg='white', font=('Courier New', 11)).grid(row=r, column=0, sticky='e', padx=(0, 10), pady=3)
        self.display = ttk.Combobox(self.frame, state='readonly', textvariable=self.display_value, width=30)
        self.display.grid(row=1, column=1, columnspan=2, sticky='ew', pady=3)
        self.display.bind('<<ComboboxSelected>>', self.change_display)
        self.style = ttk.Combobox(self.frame, state='readonly', textvariable=self.style_value, values=('Sál', 'Stream'), width=30)
        self.style.grid(row=2, column=1, columnspan=2, sticky='ew', pady=3)
        self.style.bind('<<ComboboxSelected>>', self.change_style)
        self.play = tk.Button(self.frame, text='▶', command=self.toggle_run, bg='#006400', fg='white', relief='flat', width=18, takefocus=False)
        self.play.grid(row=3, column=0, columnspan=2, sticky='w', pady=(5, 0))
        self.fullscreen_value = tk.BooleanVar(value=True)
        self.fullscreen_check = tk.Checkbutton(self.frame, text='Celá obrazovka', variable=self.fullscreen_value,
                                              command=self.change_fullscreen, bg='#555555', fg='white', selectcolor='#444444', activebackground='#555555', activeforeground='white')
        self.fullscreen_check.grid(row=3, column=2, sticky='e')
        # Catalog selection is exposed through load/edit; the compact panel
        # retains its Display/Style controls for the current output.
        self.choice = ttk.Combobox(row, state='readonly', textvariable=self.selected,
                                   values=[p.name for p in self.profiles], width=16)
        self.choice.bind('<<ComboboxSelected>>', self.choose)
        self.summary = tk.StringVar()
        self.configure_appearance()

    def outputs(self):
        return [f for f in ('hall', 'stream') if self.enabled[f]]

    def browse(self, delta):
        fields = self.outputs()
        self.output_index = (self.output_index+delta) % len(fields)
        self.update_summary()

    def add_output(self):
        if self.owner.session:
            self.owner.status.set('Před přidáním výstupu zastavte projekci.')
            return
        fields = self.outputs()
        if len(fields) == 2:
            return
        other = 'stream' if fields[0] == 'hall' else 'hall'
        self.enabled[other] = True
        self.output_index = self.outputs().index(other)
        self.update_summary()

    def change_display(self, event=None):
        if self.owner.session:
            self.update_summary()
            return
        field = self.outputs()[self.output_index]
        mid = self.display_ids.get(self.display_value.get())
        if mid is not None:
            self.owner.monitor_choices[field].set(mid)
        self.update_summary()

    def change_style(self, event=None):
        if self.owner.session:
            self.update_summary()
            return
        field = self.outputs()[self.output_index]
        target = 'hall' if self.style_value.get() == 'Sál' else 'stream'
        if target != field:
            if self.enabled[target]:
                self.owner.status.set('Sál i stream již mají vlastní výstup; stejný Style nelze přidat dvakrát.')
            else:
                self.owner.monitor_choices[target].set(self.owner.monitor_choices[field].get())
                self.enabled[field], self.enabled[target] = False, True
        self.update_summary()

    def change_fullscreen(self):
        if not self.owner.session:
            self.fullscreen[self.outputs()[self.output_index]] = self.fullscreen_value.get()
        self.update_summary()

    def toggle_run(self):
        if self.owner.session:
            self.owner.stop_projection()
        else:
            self.start()
        self.update_summary()

    def configure_appearance(self):
        style = ttk.Style(self.owner.root)
        style.theme_use('clam')
        for kind in ('TFrame', 'TLabelframe', 'TLabelframe.Label', 'TLabel', 'TCheckbutton', 'TButton', 'TMenubutton', 'TEntry', 'TCombobox'):
            name = 'PPProjection.'+kind
            style.configure(name, background='#444444', foreground='#ffffff',
                            fieldbackground='#282828', insertcolor='white', padding=4)
            style.map(name, background=[('active', '#626262')], foreground=[('disabled', '#aaaaaa')])
        style.map('PPProjection.TCombobox', fieldbackground=[('readonly', '#282828')],
                  selectbackground=[('readonly', '#282828')], selectforeground=[('readonly', '#ffffff')])
        self.skin(self.frame)

    def skin(self, widget):
        kinds = {'TFrame', 'TLabelframe', 'TLabel', 'TCheckbutton', 'TButton', 'TMenubutton', 'TEntry', 'TCombobox'}
        if widget.winfo_class() in kinds:
            widget.configure(style='PPProjection.'+widget.winfo_class())
        for child in widget.winfo_children():
            self.skin(child)

    def update_summary(self):
        active = [name for field, name in (('hall', 'Sál'), ('stream', 'Stream')) if self.enabled[field]]
        self.summary.set(' + '.join(active))
        fields = self.outputs()
        self.output_index = min(self.output_index, len(fields)-1)
        field = fields[self.output_index]
        self.fullscreen_value.set(self.fullscreen[field])
        self.fullscreen_check.configure(state='disabled' if self.owner.session else 'normal')
        self.counter.set(f'{self.output_index+1} / {len(fields)}')
        self.style_value.set('Sál' if field == 'hall' else 'Stream')
        self.display_ids = {label: m.id for label, m in zip(self.labels(), self.owner.monitor_inventory)}
        mid = self.owner.monitor_choices[field].get()
        label = next((s for s, value in self.display_ids.items() if value == mid), 'Nedostupný: '+mid)
        self.display_ids[label] = mid
        self.display.configure(values=list(self.display_ids), state='disabled' if self.owner.session else 'readonly')
        self.display_value.set(label)
        self.style.configure(state='disabled' if self.owner.session else 'readonly')
        self.add_button.configure(state='disabled' if len(fields) == 2 or self.owner.session else 'normal')
        for button in (self.load_button, self.edit_button):
            button.configure(state='disabled' if self.owner.session else 'normal')
        self.previous.configure(state='normal' if len(fields) > 1 else 'disabled')
        self.following.configure(state='normal' if len(fields) > 1 else 'disabled')
        self.play.configure(text='■' if self.owner.session else '▶', bg='#8b2020' if self.owner.session else '#006400')

    def snapshot(self, name=None):
        w = self.owner
        outputs = {f: OutputPreset(self.enabled[f], w.monitor_choices[f].get(), getattr(w.document, f).aspect.value, self.fullscreen[f]) for f in self.enabled}
        return ProjectionPreset(name or self.selected.get(), **outputs, monitor_names=self.monitor_names)

    def labels(self):
        aliases = {n.monitor: n.label for n in self.monitor_names if n.label.strip()}
        return [f'{aliases[m.id]} ({m.x}, {m.y})' if m.id in aliases else label
                for m, label in zip(self.owner.monitor_inventory, monitor_labels(self.owner.monitor_inventory))]

    def apply(self, preset):
        w = self.owner
        if w.session:
            w.status.set('Před změnou projekčního profilu zastavte všechny výstupy.')
            return False
        self.selected.set(preset.name)
        self.monitor_names = preset.monitor_names
        for field in self.enabled:
            config = getattr(preset, field)
            self.enabled[field] = config.enabled
            self.fullscreen[field] = config.fullscreen
            if config.monitor:
                w.monitor_choices[field].set(config.monitor)
        w.commit(replace(w.document, **{f: replace(getattr(w.document, f), aspect=Aspect(getattr(preset, f).aspect)) for f in self.enabled}))
        w.rebuild()
        self.update_summary()
        missing = [f for f in self.enabled if self.enabled[f] and w.monitor_choices[f].get() not in {m.id for m in w.monitor_inventory}]
        if missing:
            w.status.set('Profil má nedostupný monitor. Otevřete Monitory a projekční výstupy a vyberte náhradu.')
        return True

    def choose(self, event=None):
        old = getattr(self, 'applied_name', 'Sál + stream')
        preset = next((p for p in self.profiles if p.name == self.selected.get()), None)
        if preset and self.apply(preset):
            self.applied_name = preset.name
        else:
            self.selected.set(old)

    def start(self):
        return self.owner.start_projection(tuple(f for f in self.enabled if self.enabled[f]))

    def load_profile(self):
        if self.owner.session:
            self.owner.status.set('Před načtením profilu zastavte všechny výstupy.')
            return
        if self.editor and self.editor.win.winfo_exists():
            self.editor.win.lift()
            return
        self.editor = ProfileLoader(self)

    def open_editor(self):
        if self.owner.session:
            self.owner.status.set('Před úpravou projekčního profilu zastavte všechny výstupy.')
            return
        if self.editor and self.editor.win.winfo_exists():
            self.editor.win.lift()
            return
        self.editor = ProfileEditor(self)


