"""Monitor cards and saved-profile loading; changes are drafts until applied."""
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import replace
from .profiles import ProjectionPreset, OutputPreset, MonitorName, save_profiles, validate_catalog
from .projection import monitor_labels


class ProfileLoader:
    def __init__(self, controls):
        self.controls, self.owner = controls, controls.owner
        self.win = tk.Toplevel(self.owner.root)
        self.win.title('Načíst projekční profil')
        self.win.transient(self.owner.root)
        self.win.configure(bg='#444444')
        self.win.protocol('WM_DELETE_WINDOW', self.cancel)
        self.win.bind('<Escape>', lambda e: self.cancel())
        frame = ttk.Frame(self.win, padding=16)
        frame.pack(fill='both', expand=True)
        initial = controls.selected.get() if controls.selected.get() in {p.name for p in controls.profiles} else controls.profiles[0].name
        self.selection = tk.StringVar(value=initial)
        self.choice = ttk.Combobox(frame, textvariable=self.selection, state='readonly', values=[p.name for p in controls.profiles], width=32)
        self.choice.pack(fill='x', pady=8)
        self.status = tk.StringVar(value='Vyberte uložený profil. Načtení projekci nespustí.')
        ttk.Label(frame, textvariable=self.status, wraplength=420).pack(fill='x', pady=8)
        actions = ttk.Frame(frame)
        actions.pack(anchor='e')
        ttk.Button(actions, text='Načíst', command=self.apply).pack(side='left', padx=4)
        ttk.Button(actions, text='Zrušit', command=self.cancel).pack(side='left', padx=4)
        controls.skin(self.win)
        self.win.grab_set()

    def refresh_monitors(self):
        pass

    def apply(self):
        preset = next((p for p in self.controls.profiles if p.name == self.selection.get()), None)
        if not preset:
            self.status.set('Vyberte existující uložený profil.')
            return False
        if self.controls.apply(preset):
            self.controls.applied_name = preset.name
            self.cancel()
            return True
        self.status.set('Před načtením profilu zastavte všechny výstupy.')
        return False

    def cancel(self):
        self.controls.editor = None
        self.win.destroy()


class ProfileEditor:
    def __init__(self, controls):
        self.controls, self.owner = controls, controls.owner
        self.profiles = list(controls.profiles)
        self.win = tk.Toplevel(self.owner.root)
        self.win.title('Monitory a projekční výstupy')
        self.win.transient(self.owner.root)
        self.win.configure(bg='#444444')
        width = min(1100, max(580, 440*len(self.owner.monitor_inventory)))
        height = min(800, max(500, self.owner.root.winfo_screenheight()-100))
        self.win.geometry(f'{width}x{height}')
        self.win.minsize(540, 500)
        self.win.protocol('WM_DELETE_WINDOW', self.cancel)
        self.win.bind('<Escape>', lambda e: self.cancel())
        self.cards = {}
        self.inventory = ()
        self.base = controls.snapshot()
        header = ttk.Frame(self.win, padding=12)
        header.pack(fill='x')
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text='Profil:').grid(row=0, column=0, sticky='w')
        self.selection = tk.StringVar(value=self.base.name)
        self.choice = ttk.Combobox(header, state='readonly', textvariable=self.selection, values=[p.name for p in self.profiles], width=24)
        self.choice.grid(row=0, column=1, sticky='ew', padx=8)
        self.choice.bind('<<ComboboxSelected>>', self.switch)
        ttk.Button(header, text='+ Nový profil', command=self.new).grid(row=0, column=2, padx=4)
        ttk.Label(header, text='Název:').grid(row=1, column=0, sticky='w')
        self.name = tk.StringVar(value=self.base.name)
        ttk.Entry(header, textvariable=self.name).grid(row=1, column=1, sticky='ew', padx=8, pady=6)
        ttk.Button(header, text='Smazat profil', command=self.delete).grid(row=1, column=2, padx=4)
        self.status = tk.StringVar(value=controls.load_error or 'Uložit uloží profil. Použít bez uložení změní pouze přípravu projekce.')
        footer = ttk.Frame(self.win, padding=12)
        footer.pack(side='bottom', fill='x')
        ttk.Label(footer, textvariable=self.status, wraplength=750).pack(fill='x', pady=6)
        actions = ttk.Frame(footer)
        actions.pack(anchor='center')
        for label, command in (('Uložit', self.save), ('Použít bez uložení', self.apply), ('Zrušit', self.cancel)):
            ttk.Button(actions, text=label, command=command).pack(side='left', padx=4)
        area = ttk.Frame(self.win, padding=12)
        area.pack(fill='both', expand=True)
        area.rowconfigure(0, weight=1)
        area.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(area, bg='#444444', highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        ttk.Scrollbar(area, orient='horizontal', command=self.canvas.xview).grid(row=1, column=0, sticky='ew')
        ttk.Scrollbar(area, orient='vertical', command=self.canvas.yview).grid(row=0, column=1, sticky='ns')
        self.canvas.configure(xscrollcommand=lambda *v: area.grid_slaves(row=1, column=0)[0].set(*v),
                              yscrollcommand=lambda *v: area.grid_slaves(row=0, column=1)[0].set(*v))
        self.body = ttk.Frame(self.canvas)
        self.body_id = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.body.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.current_name = self.base.name
        self.load(self.base)
        controls.skin(self.win)
        self.win.grab_set()

    def render(self, preset, retained=None):
        retained = retained or {}
        for child in self.body.winfo_children():
            child.destroy()
        self.cards = {}
        self.inventory = tuple(sorted(self.owner.monitor_inventory, key=lambda m: (m.x, m.y, m.id)))
        ids = [m.id for m in self.inventory]
        outputs, secondary = {}, {}
        for field in ('hall', 'stream'):
            config = getattr(preset, field)
            if config.enabled:
                mid = config.monitor or self.owner.monitor_choices[field].get()
                if mid in outputs:
                    previous_field = 'hall' if outputs[mid][0] == 'Sál' else 'stream'
                    if not config.fullscreen and not getattr(preset, previous_field).fullscreen:
                        secondary[mid] = ('Sál' if field == 'hall' else 'Stream', config.aspect, config.fullscreen)
                        continue
                    # Legacy single-monitor dual-output preset: preserve warning,
                    # let the user reassign the second style on another card.
                    self.status.set('Profil má dva výstupy na stejném monitoru. Vyberte Sál/Stream na různých kartách.')
                    mid = 'unassigned:'+field
                    outputs[mid] = ('Sál' if field == 'hall' else 'Stream', config.aspect, config.fullscreen)
                else:
                    outputs[mid] = ('Sál' if field == 'hall' else 'Stream', config.aspect, config.fullscreen)
                if mid not in ids:
                    ids.append(mid)
        for mid in retained:
            if mid not in ids:
                ids.append(mid)
        aliases = {n.monitor: n.label for n in preset.monitor_names}
        labels = dict(zip([m.id for m in self.inventory], monitor_labels(self.inventory)))
        # Horizontal cards make every connected monitor inspectable in one strip.
        for index, mid in enumerate(ids):
            default_style, default_aspect, default_fullscreen = outputs.get(mid, ('Nepoužívat', '4:3', True))
            second_style, second_aspect, second_fullscreen = secondary.get(mid, ('Nepoužívat', '16:9', True))
            custom, style, aspect, fullscreen, second_style, second_aspect, second_fullscreen = retained.get(mid, (aliases.get(mid, ''), default_style, default_aspect, default_fullscreen, second_style, second_aspect, second_fullscreen))
            tile = ttk.Frame(self.body, padding=6)
            tile.grid(row=0, column=index, sticky='n', padx=6)
            preview = tk.Canvas(tile, width=360, height=90, bg='#444444', highlightthickness=0)
            preview.pack(fill='x', pady=(0, 10))
            label = labels.get(mid, 'Odpojený monitor')
            frame = ttk.LabelFrame(tile, text=label, padding=12)
            frame.pack(fill='x')
            name_var, style_var, aspect_var = tk.StringVar(value=custom), tk.StringVar(value=style), tk.StringVar(value=aspect)
            card = dict(name=name_var, style=style_var, aspect=aspect_var, preview=preview, label=label, frame=frame)
            card['fullscreen'] = tk.BooleanVar(value=fullscreen)
            self.cards[mid] = card
            ttk.Label(frame, text='Vlastní název').pack(anchor='w')
            ttk.Entry(frame, textvariable=name_var, width=28).pack(fill='x', pady=(4, 10))
            ttk.Label(frame, text='Promítaný styl').pack(anchor='w')
            ttk.Combobox(frame, textvariable=style_var, state='readonly', values=('Nepoužívat', 'Sál', 'Stream'), width=28).pack(fill='x', pady=(4, 10))
            ttk.Label(frame, text='Poměr stran').pack(anchor='w')
            ttk.Combobox(frame, textvariable=aspect_var, state='readonly', values=('4:3', '16:9'), width=10).pack(anchor='w', pady=4)
            ttk.Checkbutton(frame, text='Celá obrazovka', variable=card['fullscreen']).pack(anchor='w', pady=4)
            card['second_style'] = tk.StringVar(value=second_style)
            card['second_aspect'] = tk.StringVar(value=second_aspect)
            card['second_fullscreen'] = tk.BooleanVar(value=second_fullscreen)
            second = ttk.Frame(frame)
            card['second_frame'] = second
            ttk.Label(second, text='Druhý výstup na stejném monitoru').pack(anchor='w')
            ttk.Combobox(second, textvariable=card['second_style'], state='readonly', values=('Nepoužívat', 'Sál', 'Stream'), width=28).pack(fill='x', pady=4)
            ttk.Combobox(second, textvariable=card['second_aspect'], state='readonly', values=('4:3', '16:9'), width=10).pack(anchor='w', pady=4)
            ttk.Checkbutton(second, text='Celá obrazovka', variable=card['second_fullscreen']).pack(anchor='w', pady=4)
            ttk.Button(frame, text='+ Druhý výstup pro testování', command=lambda mid=mid: self.add_second(mid)).pack(anchor='w', pady=4)
            if second_style != 'Nepoužívat':
                second.pack(fill='x', pady=8)
            card['last_style'] = style
            style_var.trace_add('write', lambda *args, mid=mid: self.style_changed(mid))
            name_var.trace_add('write', lambda *args, mid=mid: self.draw_card(mid))
            preview.bind('<Configure>', lambda e, mid=mid: self.draw_card(mid))
            self.draw_card(mid)
        self.controls.skin(self.body)

    def add_second(self, mid):
        card = self.cards[mid]
        if card['second_style'].get() == 'Nepoužívat':
            card['second_style'].set('Stream' if card['style'].get() != 'Stream' else 'Sál')
            card['second_aspect'].set(self.base.stream.aspect if card['second_style'].get() == 'Stream' else self.base.hall.aspect)
        card['fullscreen'].set(False)
        card['second_fullscreen'].set(False)
        card['second_frame'].pack(fill='x', pady=8)

    def style_changed(self, mid):
        card = self.cards[mid]
        value = card['style'].get()
        if value != card['last_style'] and value in ('Sál', 'Stream'):
            field = 'hall' if value == 'Sál' else 'stream'
            card['aspect'].set(getattr(self.base, field).aspect)
        card['last_style'] = value

    def draw_card(self, mid):
        card = self.cards[mid]
        canvas = card['preview']
        canvas.delete('all')
        width = max(360, canvas.winfo_width())
        canvas.create_rectangle(1, 1, width-1, 88, fill='#444444', outline='#aaaaaa', width=2)
        custom = card['name'].get().strip()
        canvas.create_text(width/2, 45, text=(custom+'\n' if custom else '')+card['label'], fill='white', font=('Courier New', 11), width=width-20)

    def refresh_monitors(self):
        if tuple(sorted(self.owner.monitor_inventory, key=lambda m: (m.x, m.y, m.id))) != self.inventory:
            retained = {mid: (c['name'].get(), c['style'].get(), c['aspect'].get(), c['fullscreen'].get(), c['second_style'].get(), c['second_aspect'].get(), c['second_fullscreen'].get()) for mid, c in self.cards.items()}
            self.render(self.base, retained)
            self.status.set('Zapojení monitorů se změnilo. Návrh je zachován; zkontrolujte aktivní karty.')

    def load(self, preset):
        self.base = preset
        self.name.set(preset.name)
        self.current_name = preset.name
        self.render(preset)

    def draft(self):
        outputs = {f: replace(getattr(self.base, f), enabled=False) for f in ('hall', 'stream')}
        aliases = {n.monitor: n for n in self.base.monitor_names}
        for mid, card in self.cards.items():
            custom = card['name'].get().strip()
            if custom:
                aliases[mid] = MonitorName(mid, custom)
            else:
                aliases.pop(mid, None)
            for prefix in ('', 'second_'):
                style = card[prefix+'style'].get()
                if style == 'Nepoužívat':
                    continue
                if style not in ('Sál', 'Stream'):
                    raise ValueError('Vyberte platný promítaný styl.')
                field = 'hall' if style == 'Sál' else 'stream'
                if outputs[field].enabled:
                    raise ValueError('Sál i Stream mohou být použity nejvýše jednou.')
                outputs[field] = OutputPreset(True, mid, card[prefix+'aspect'].get(), card[prefix+'fullscreen'].get())
        active = [o for o in outputs.values() if o.enabled]
        if len(active) == 2 and active[0].monitor == active[1].monitor and any(o.fullscreen for o in active):
            raise ValueError('Pro dva výstupy na jednom monitoru vypněte Celá obrazovka u obou.')
        return ProjectionPreset(self.name.get().strip(), **outputs, monitor_names=tuple(aliases.values()))

    def stage(self):
        preset = self.draft()
        profiles = [p for p in self.profiles if p.name != self.current_name]
        profiles.append(preset)
        validate_catalog(profiles)
        self.profiles = profiles
        self.current_name = preset.name
        self.selection.set(preset.name)
        self.choice.configure(values=[p.name for p in profiles])
        return preset

    def switch(self, event=None):
        target = self.selection.get()
        try:
            self.stage()
            self.load(next(p for p in self.profiles if p.name == target))
            self.selection.set(target)
        except (ValueError, StopIteration) as exc:
            self.selection.set(self.current_name)
            self.status.set(str(exc))

    def new(self):
        try:
            self.stage()
            index = 1
            while any(p.name.casefold() == f'profil {index}' for p in self.profiles):
                index += 1
            preset = replace(self.draft(), name=f'Profil {index}')
            self.profiles.append(preset)
            self.load(preset)
            self.selection.set(preset.name)
            self.choice.configure(values=[p.name for p in self.profiles])
        except ValueError as exc:
            self.status.set(str(exc))

    def delete(self):
        if len(self.profiles) <= 1:
            self.status.set('Ponechte alespoň jeden profil.')
            return
        if messagebox.askyesno('Smazat profil', 'Odstranit vybraný profil? Změna se uloží tlačítkem Uložit.', parent=self.win):
            self.profiles = [p for p in self.profiles if p.name != self.current_name]
            self.load(self.profiles[0])
            self.selection.set(self.current_name)
            self.choice.configure(values=[p.name for p in self.profiles])

    def save(self):
        try:
            self.stage()
            save_profiles(tuple(self.profiles))
            self.controls.profiles = tuple(self.profiles)
            self.controls.choice.configure(values=[p.name for p in self.profiles])
            self.status.set('Profily uloženy. Nastavení se změní až tlačítkem Použít bez uložení.')
            return True
        except (OSError, ValueError) as exc:
            self.status.set('Nelze uložit: '+str(exc))
            return False

    def apply(self):
        try:
            if self.owner.session:
                raise ValueError('Před změnou profilu zastavte všechny výstupy.')
            preset = self.draft()
            self.owner.refresh_monitors_now()
            available = {m.id for m in self.owner.monitor_inventory}
            if any(getattr(preset, f).enabled and getattr(preset, f).monitor not in available for f in ('hall', 'stream')):
                raise ValueError('Aktivní monitor je odpojený. Přesuňte styl na připojenou kartu.')
            if self.controls.apply(preset):
                self.controls.applied_name = preset.name
                self.cancel()
                return True
        except ValueError as exc:
            self.status.set(str(exc))
        return False

    def cancel(self):
        self.controls.editor = None
        self.win.destroy()
