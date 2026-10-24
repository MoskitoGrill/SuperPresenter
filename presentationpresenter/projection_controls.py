"""Movable projection panel and transactional profile editor."""
import tkinter as tk
from tkinter import ttk
from dataclasses import replace
from .profiles import ProjectionPreset, OutputPreset, defaults, load_profiles
from .domain import Aspect
from .projection import monitor_labels
from .monitor_editor import ProfileEditor, ProfileLoader
from .ribbon import command_group
from .appearance import appearance


class ProjectionControls:
    def __init__(self, owner, parent, play_parent):
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
        self.frame = parent
        output = command_group(parent, 'Výstup')
        monitor = command_group(parent, 'Monitor')
        layout = command_group(parent, 'Rozložení')
        profiles = command_group(parent, 'Profily')
        row = tk.Frame(output)
        row.pack(anchor='w')
        def button(label, command, container=row):
            b = tk.Button(container, text=label, command=command, takefocus=True)
            b.pack(side='left', padx=1)
            return b
        self.previous = button('<', lambda: self.browse(-1))
        self.counter = tk.StringVar()
        tk.Label(row, textvariable=self.counter, width=5).pack(side='left')
        self.following = button('>', lambda: self.browse(1))
        self.add_button = tk.Button(output, text='+ Výstup', command=self.add_output)
        self.add_button.pack(anchor='w', pady=(4, 0))
        self.load_button = button('Načíst', self.load_profile, profiles)
        self.edit_button = button('Upravit', self.open_editor, profiles)
        for action in (self.load_button, self.edit_button):
            action.pack_configure(side='top', fill='x', pady=1)
        self.display_value = tk.StringVar()
        self.style_value = tk.StringVar()
        self.display_ids = {}
        tk.Label(monitor, text='Display').pack(anchor='w')
        tk.Label(layout, text='Style').grid(row=0, column=0, columnspan=2, sticky='w')
        self.display = ttk.Combobox(monitor, state='readonly', textvariable=self.display_value, width=18)
        self.display.pack(anchor='w', pady=3)
        self.display.bind('<<ComboboxSelected>>', self.change_display)
        self.style = ttk.Combobox(layout, state='readonly', textvariable=self.style_value, values=('Sál', 'Stream'), width=10)
        self.style.grid(row=1, column=0, sticky='ew', pady=3, padx=(0, 4))
        self.style.bind('<<ComboboxSelected>>', self.change_style)
        self.aspect_value = tk.StringVar()
        self.aspect = ttk.Combobox(layout, state='readonly', textvariable=self.aspect_value,
                                   values=tuple(a.value for a in Aspect), width=6)
        self.aspect.grid(row=1, column=1, sticky='ew', pady=3)
        self.aspect.bind('<<ComboboxSelected>>', self.change_aspect)
        self.play = tk.Button(play_parent, text='▶', command=self.toggle_run, bg=appearance(owner.root).run, fg='white', width=3, takefocus=True)
        self.fullscreen_value = tk.BooleanVar(value=True)
        self.fullscreen_check = tk.Checkbutton(monitor, text='Celá obrazovka', variable=self.fullscreen_value,
                                              command=self.change_fullscreen)
        self.fullscreen_check.pack(anchor='w')
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

    def change_aspect(self, event=None):
        # Aspect edits belong to the draft even while a live session is running.
        field = self.outputs()[self.output_index]
        self.owner.change_aspect(field, self.aspect_value.get())
        self.update_summary()

    def toggle_run(self):
        if self.owner.session:
            self.owner.stop_projection()
        else:
            self.start()
        self.update_summary()

    def configure_appearance(self):
        theme = appearance(self.owner.root)
        for widget in (self.display, self.style, self.aspect, self.choice):
            widget.configure(style='PP.TCombobox', font=theme.text)

    def skin(self, widget):
        appearance(self.owner.root).apply(widget)

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
        self.aspect_value.set(getattr(self.owner.document, field).aspect.value)
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
        theme = appearance(self.owner.root)
        self.play.configure(text='■' if self.owner.session else '▶',
                            bg=theme.stop if self.owner.session else theme.run,
                            activebackground=theme.run if self.owner.session else theme.stop)

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

    def start(self, from_current=True):
        return self.owner.start_projection(tuple(f for f in self.enabled if self.enabled[f]), from_current=from_current)

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


