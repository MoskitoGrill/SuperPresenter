"""Transactional monitor/profile editor using the application's Tk widgets."""
from copy import deepcopy
from superpresenter.services.projection_limits import STREAM_STANDARD_ROWS, row_limits
from superpresenter.services.stationary_navigation import style_mode
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

from superpresenter.services.projection_config import (
    ConfigError, layout_row_limit, monitor_labels, load_layout, match_monitor, monitor_identity,
)
from superpresenter.services.projection_profile_catalog import profile_catalog, next_profile_name, save_named_profile, delete_named_profile
from superpresenter.services.projection_editor_model import editor_cards, layout_from_cards


class ProjectionEditor:
    def __init__(self, owner):
        self.owner = owner
        self.monitors = list(owner.monitors)
        self.original = owner.layout_snapshot()
        self.cards = []
        self.entries = profile_catalog(owner.profile_dir / 'profiles')
        self.selected_profile = len(self.entries)
        candidates = sorted(range(len(self.entries)), key=lambda i: self.entries[i]['name'] != self.original.get('profile_name'))
        for i in candidates:
            entry = self.entries[i]
            try:
                stored = load_layout(entry['path'], owner.projStyles)
                if (stored.get('outputs') == self.original.get('outputs')
                        and stored.get('monitor_names', []) == self.original.get('monitor_names', [])
                        and layout_row_limit(stored, owner.projStyles) == layout_row_limit(self.original, owner.projStyles)):
                    self.selected_profile = i
                    break
            except ConfigError:
                pass
        if self.selected_profile == len(self.entries):
            self.entries.append(dict(path=None, name=next_profile_name(self.entries)))
        self.win = tk.Toplevel(owner.win)
        self.win.title('Monitory a projekční výstupy')
        self.win.transient(owner.win)
        self.configure_appearance()
        self.win.protocol('WM_DELETE_WINDOW', self.cancel)
        self.win.bind('<Escape>', lambda event: self.cancel())
        self.win.rowconfigure(2, weight=1)
        self.win.columnconfigure(0, weight=1)
        header = ttk.Frame(self.win, padding=12, style='Projection.TFrame')
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text='Profil:', style='Projection.TLabel').grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.profile_choice = ttk.Combobox(header, state='readonly', width=20, font=self.font, style='Projection.TCombobox')
        self.profile_choice.grid(row=0, column=1, sticky='ew', pady=5)
        self.profile_choice.bind('<<ComboboxSelected>>', self.switch_profile)
        ttk.Button(header, text='+ Nový profil', command=self.new_profile, style='Projection.TButton').grid(row=0, column=2, padx=(10, 0))
        ttk.Label(header, text='Název:', style='Projection.TLabel').grid(row=1, column=0, sticky='w')
        self.profile_name = tk.StringVar(self.win, value=self.entries[self.selected_profile]['name'])
        ttk.Entry(header, textvariable=self.profile_name, width=20, font=self.font, style='Projection.TEntry').grid(row=1, column=1, sticky='ew', pady=5)
        ttk.Button(header, text='Smazat profil', command=self.delete_profile, style='Projection.TButton').grid(row=1, column=2, padx=(10, 0))
        self.refresh_profile_choices()

        area = ttk.Frame(self.win, padding=12, style='Projection.TFrame')
        area.grid(row=2, column=0, sticky='nsew')
        area.rowconfigure(0, weight=1)
        area.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(area, highlightthickness=0, background=self.background)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        sx = ttk.Scrollbar(area, orient='horizontal', command=self.canvas.xview)
        sy = ttk.Scrollbar(area, orient='vertical', command=self.canvas.yview)
        sx.grid(row=1, column=0, sticky='ew')
        sy.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)
        self.body = ttk.Frame(self.canvas, style='Projection.TFrame')
        self.body_id = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.body.bind('<Configure>', self.center_body)
        self.canvas.bind('<Configure>', self.center_body)
        footer = ttk.Frame(self.win, padding=12, style='Projection.TFrame')
        footer.grid(row=3, column=0, sticky='ew')
        self.status = tk.StringVar(self.win)
        ttk.Label(footer, textvariable=self.status, wraplength=560, style='Projection.Status.TLabel').pack(fill='x', pady=(0, 12))
        actions = ttk.Frame(footer, style='Projection.TFrame')
        actions.pack(anchor='center')
        ttk.Button(actions, style='Projection.TButton', text='Zrušit', command=self.cancel).pack(side='right', padx=4)
        ttk.Button(actions, style='Projection.TButton', text='Použít', command=self.apply).pack(side='right', padx=4)
        ttk.Button(actions, style='Projection.TButton', text='Uložit', command=self.save_profile).pack(side='right', padx=4)
        self.render_cards()
        self.baseline = self.state()
        self.win.update_idletasks()
        width = min(max(header.winfo_reqwidth(), self.body.winfo_reqwidth()) + 48, self.win.winfo_screenwidth() - 80)
        height = min(header.winfo_reqheight() + self.body.winfo_reqheight() + footer.winfo_reqheight() + 60, self.win.winfo_screenheight() - 100)
        self.win.geometry(f'{width}x{height}')
        self.win.minsize(min(560, width), min(480, height))
        self.win.grab_set()
        self.draw_map()
        from superpresenter.windows_shell import style_title_bar
        style_title_bar(self.win)

    def configure_appearance(self):
        self.background = self.owner.win.cget('background')
        if self.background in ('SystemButtonFace', '#d9d9d9'):
            self.background = '#555555'
        self.font = 'listfont' if 'listfont' in tkfont.names(self.win) else ('Courier New', 14)
        button_font = 'buttfont' if 'buttfont' in tkfont.names(self.win) else ('Courier New', 14, 'bold')
        self.win.configure(background=self.background)
        style = ttk.Style(self.win)
        style.configure('Projection.TFrame', background=self.background)
        style.configure('Projection.TLabel', background=self.background, foreground='white', font=self.font)
        style.configure('Projection.Status.TLabel', background=self.background, foreground='white', font=('Courier New', 11))
        style.configure('Projection.TLabelframe', background=self.background, bordercolor='#aaaaaa', relief='solid', borderwidth=1)
        style.configure('Projection.TLabelframe.Label', background=self.background, foreground='white', font=self.font)
        style.configure('Projection.TButton', background='#444444', foreground='white', font=button_font, padding=(10, 8), relief='flat', borderwidth=0,
                        bordercolor='#444444', lightcolor='#444444', darkcolor='#444444')
        style.map('Projection.TButton', background=[('active', '#666666')], foreground=[('active', 'white')],
                  relief=[('pressed', 'flat'), ('active', 'flat')],
                  bordercolor=[('active', '#666666')], lightcolor=[('active', '#666666')], darkcolor=[('active', '#666666')])
        style.configure('Projection.TCheckbutton', background=self.background, foreground='white', font=self.font, padding=(0, 6))
        style.map('Projection.TCheckbutton', background=[('active', self.background)], foreground=[('disabled', '#aaaaaa'), ('active', 'white')])
        style.configure('Projection.TEntry', fieldbackground='#eeeeee', foreground='black', padding=5)
        style.configure('Projection.TCombobox', fieldbackground='#eeeeee', foreground='black', padding=5)
        style.map('Projection.TCombobox', fieldbackground=[('readonly', '#eeeeee')], foreground=[('readonly', 'black')])

    def center_body(self, *args):
        width = max(self.canvas.winfo_width(), self.body.winfo_reqwidth())
        self.canvas.coords(self.body_id, max(0, (width - self.body.winfo_reqwidth()) / 2), 0)
        self.canvas.configure(scrollregion=(0, 0, width, self.body.winfo_reqheight()))

    def refresh_topology(self, monitors):
        old = [(monitor_identity(m), getattr(m, 'is_primary', None)) for m in self.monitors]
        new = [(monitor_identity(m), getattr(m, 'is_primary', None)) for m in monitors]
        if old == new:
            return
        dirty = self.state() != self.baseline
        try:
            draft = self.draft()
        except ConfigError:
            self.status.set('Zapojení monitorů se změnilo. Opravte neplatné údaje; seznam se poté automaticky obnoví.')
            return
        self.original = draft
        self.monitors = list(monitors)
        self.render_cards()
        self.baseline = None if dirty else self.state()
        self.win.update_idletasks()
        width = min(max(560, self.body.winfo_reqwidth() + 48), self.win.winfo_screenwidth() - 80)
        height = min(max(self.win.winfo_height(), self.body.winfo_reqheight() + 240), self.win.winfo_screenheight() - 100)
        self.win.geometry(f'{width}x{height}')
        self.status.set('Seznam obrazovek aktualizován. Rozpracované změny zůstaly zachované.')

    def render_cards(self):
        self.hall_rows = tk.StringVar(self.win, value=str(layout_row_limit(self.original, self.owner.projStyles)))
        self.cards = []
        for widget in self.body.winfo_children():
            widget.destroy()
        x_positions = sorted({m.x for m in self.monitors})
        y_positions = sorted({m.y for m in self.monitors})
        labels = monitor_labels(self.monitors)
        for index, (monitor, draft) in enumerate(zip(self.monitors, editor_cards(self.original, self.monitors))):
            tile = ttk.Frame(self.body, style='Projection.TFrame')
            tile.grid(row=y_positions.index(monitor.y), column=x_positions.index(monitor.x),
                       sticky='new', padx=6, pady=6)
            preview = tk.Canvas(tile, height=180, width=380, background=self.background, highlightthickness=0)
            preview.pack(fill='x', padx=12, pady=(0, 10))
            frame = ttk.LabelFrame(tile, text=labels[index], padding=12, style='Projection.TLabelframe')
            frame.pack(fill='x')
            ttk.Label(frame, text='Vlastní název', style='Projection.TLabel').pack(anchor='w')
            name = tk.StringVar(self.win, value=draft['label'])
            ttk.Entry(frame, textvariable=name, width=28, font=self.font, style='Projection.TEntry').pack(fill='x', pady=(4, 8))
            name.trace_add('write', lambda *args: self.draw_map())
            rows = ttk.Frame(frame, style='Projection.TFrame')
            rows.pack(fill='x')
            card = dict(label=name, rows=rows, outputs=[], preview=preview)
            preview.bind('<Configure>', lambda event: self.draw_map())
            self.cards.append(card)
            self.add_output(card, draft['outputs'][0])

        matches = [match_monitor(output['monitor'], self.monitors) for output in self.original['outputs']]
        if any(index is not None and matches.count(index) > 1 for index in matches):
            self.status.set('Starý profil má více výstupů na obrazovce. Uložit zachová jen první; můžete vybrat jiný styl.')
        elif None in matches:
            self.status.set('Odpojené obrazovky zůstanou v uloženém profilu zachovány.')
        else:
            self.status.set('Uložit uloží profil. Použít jej uloží a také použije.')
        self.draw_map()

    def refresh_profile_choices(self):
        self.profile_choice['values'] = [entry['name'] for entry in self.entries]
        self.profile_choice.current(self.selected_profile)

    def state(self):
        return (self.profile_name.get(), self.hall_rows.get(), [
            (card['label'].get(), [(row['combo'].current(), row['fullscreen'].get(), row['collection'], deepcopy(row.get('collection_settings')))
                                  for row in card['outputs']]) for card in self.cards])

    def confirm_transition(self):
        if self.state() == self.baseline:
            return True
        answer = messagebox.askyesnocancel('Neuložené změny',
            'Uložit změny profilu před pokračováním?', parent=self.win)
        if answer is None:
            return False
        return self.save_profile() if answer else True

    def switch_profile(self, *args):
        target = self.profile_choice.current()
        if target == self.selected_profile:
            return
        if not self.confirm_transition():
            self.refresh_profile_choices()
            return
        entry = self.entries[target]
        try:
            data = load_layout(entry['path'], self.owner.projStyles) if entry['path'] else deepcopy(entry['draft'])
        except (ConfigError, OSError) as exc:
            messagebox.showerror('Načtení profilu', str(exc), parent=self.win)
            self.refresh_profile_choices()
            return
        # Keep a new unsaved profile available when switching away from it.
        old = self.entries[self.selected_profile]
        if old['path'] is None:
            old['draft'] = deepcopy(self.original)
        self.selected_profile = target
        self.original = data
        self.profile_name.set(entry['name'])
        self.refresh_profile_choices()
        self.render_cards()
        self.baseline = self.state()

    def new_profile(self):
        if not self.confirm_transition():
            return
        # Start from the saved version, so discarded changes are not copied.
        source = self.entries[self.selected_profile]
        try:
            data = load_layout(source['path'], self.owner.projStyles) if source['path'] else deepcopy(self.original)
        except ConfigError as exc:
            messagebox.showerror('Nový profil', str(exc), parent=self.win)
            return
        if source['path'] is None:
            source['draft'] = deepcopy(self.original)
        entry = dict(path=None, name=next_profile_name(self.entries), draft=data)
        self.entries.append(entry)
        self.selected_profile = len(self.entries) - 1
        self.original = data
        self.profile_name.set(entry['name'])
        self.refresh_profile_choices()
        self.render_cards()
        self.baseline = None

    def delete_profile(self):
        entry = self.entries[self.selected_profile]
        if not messagebox.askyesno('Smazat profil',
                f'Smazat profil „{entry["name"]}“ včetně případných neuložených úprav? '
                'Aktuálně používané rozložení zůstane zachované.', parent=self.win):
            return
        try:
            delete_named_profile(self.owner.profile_dir / 'profiles', entry)
        except ConfigError as exc:
            messagebox.showerror('Smazání profilu', str(exc), parent=self.win)
            return
        self.entries.pop(self.selected_profile)
        data = None
        for index, candidate in enumerate(self.entries):
            try:
                data = load_layout(candidate['path'], self.owner.projStyles) if candidate['path'] else deepcopy(candidate['draft'])
                self.selected_profile = index
                break
            except (ConfigError, OSError):
                continue
        if data is None:
            data = self.owner.layout_snapshot()
            self.entries.append(dict(path=None, name=next_profile_name(self.entries), draft=deepcopy(data)))
            self.selected_profile = len(self.entries) - 1
        self.original = data
        self.profile_name.set(self.entries[self.selected_profile]['name'])
        self.refresh_profile_choices()
        self.render_cards()
        self.baseline = self.state()
        self.status.set(f'Profil „{entry["name"]}“ smazán. Používané rozložení se nezměnilo.')

    def add_output(self, card, output=None):
        if output is None:
            output = dict(style=None, fullscreen=True, collection=False, window_position=None)
        frame = ttk.Frame(card['rows'], style='Projection.TFrame')
        frame.pack(fill='x', pady=6)
        choices = ['Nepromítat'] + [s['name'] for s in self.owner.projStyles]
        ttk.Label(frame, text='Promítaný styl', style='Projection.TLabel').pack(anchor='w')
        combo = ttk.Combobox(frame, values=choices, state='readonly', width=28, font=self.font, style='Projection.TCombobox')
        combo.current(0 if output['style'] is None else choices.index(output['style']))
        combo.pack(fill='x', pady=4)
        row_frame = ttk.Frame(frame, style='Projection.TFrame')
        ttk.Label(row_frame, text='Počet řádků', style='Projection.TLabel').pack(anchor='w')
        ttk.Entry(row_frame, textvariable=self.hall_rows, font=self.font,
                  style='Projection.TEntry').pack(fill='x', pady=4)
        ttk.Label(row_frame, text=f'Maximum sálu (společné pro všechny výstupy).\nStream použije nejvýše {STREAM_STANDARD_ROWS} řádky.',
                  style='Projection.Status.TLabel').pack(anchor='w')
        fullscreen = tk.BooleanVar(self.win, value=output['fullscreen'])
        row = dict(collection_settings=deepcopy(output.get('collection_settings')))
        def edit_qr():
            from superpresenter.ui.collection_qr_editor import CollectionQREditor
            try:
                rows = row_limits(int(self.hall_rows.get()))[0]
            except ValueError:
                rows = 8
            CollectionQREditor(self.win, self.owner.projStyles[combo.current() - 1],
                               row['collection_settings'],
                               lambda settings: row.update(collection_settings=settings), rows)
        ttk.Button(row_frame, text='Nastavení QR sbírky…', command=edit_qr,
                   style='Projection.TButton').pack(anchor='w', pady=8)
        collection = bool(output['collection'])  # Preserve stored QR preference without editing it here.
        full_check = ttk.Checkbutton(frame, text='Celá obrazovka', variable=fullscreen, style='Projection.TCheckbutton')
        full_check.pack(anchor='w')
        def update_options(*args):
            selected = combo.current()
            full_check.configure(state='normal' if selected > 0 else 'disabled')
            if selected > 0 and style_mode(self.owner.projStyles[selected - 1]) == 'stationary_hall':
                row_frame.pack(fill='x', before=full_check)
            else:
                row_frame.pack_forget()
        combo.bind('<<ComboboxSelected>>', update_options)
        update_options()
        row.update(combo=combo, fullscreen=fullscreen, collection=collection,
                   window_position=deepcopy(output.get('window_position')))
        card['outputs'].append(row)

    def draft(self):
        cards = []
        for card in self.cards:
            outputs = []
            for row in card['outputs']:
                selected = row['combo'].current()
                outputs.append(dict(style=None if selected == 0 else self.owner.projStyles[selected - 1]['name'],
                    fullscreen=bool(row['fullscreen'].get()), collection=bool(row['collection']),
                    window_position=row['window_position']))
                if row.get('collection_settings') is not None:
                    outputs[-1]['collection_settings'] = deepcopy(row['collection_settings'])
            cards.append(dict(label=card['label'].get(), outputs=outputs))
        try:
            hall_rows, _ = row_limits(int(self.hall_rows.get()))
        except ValueError as exc:
            raise ConfigError('Počet řádků musí být kladné celé číslo.') from exc
        data = layout_from_cards(cards, self.monitors, self.owner.projStyles,
                                 self.original.get('monitor_names', []), self.original['outputs'])
        data['hall_max_rows'] = hall_rows
        return data

    def draw_map(self):
        labels = monitor_labels(self.monitors)
        for i, card in enumerate(self.cards):
            preview = card['preview']
            preview.delete('all')
            width = max(1, preview.winfo_width())
            height = int(preview.cget('height'))
            preview.create_rectangle(1, 1, width - 1, height - 1,
                                     outline='#aaaaaa', fill='#444444', width=2)
            custom = card['label'].get().strip()
            preview.create_text(width / 2, height / 2,
                                text=(custom + '\n' + labels[i]) if custom else labels[i],
                                fill='white', font=self.font, width=max(1, width - 24))

    def apply(self):
        if not self.save_profile():
            return
        try:
            data = dict(self.draft(), profile_name=self.entries[self.selected_profile]['name'])
            if self.owner.apply_editor_layout(data, self.monitors):
                self.close()
        except (ConfigError, OSError) as exc:
            messagebox.showerror('Nastavení monitorů', str(exc), parent=self.win)

    def save_profile(self):
        try:
            data = self.draft()
            entry = save_named_profile(self.owner.profile_dir / 'profiles',
                self.entries[self.selected_profile], self.profile_name.get(), data, self.owner.projStyles)
            self.entries[self.selected_profile] = entry
            self.profile_name.set(entry['name'])
            self.original = dict(data, profile_name=entry['name'])
            self.refresh_profile_choices()
            self.baseline = self.state()
            self.status.set(f'Profil „{entry["name"]}“ uložen.')
            return True
        except (ConfigError, OSError) as exc:
            messagebox.showerror('Uložení profilu', str(exc), parent=self.win)
            return False

    def cancel(self):
        if self.confirm_transition():
            self.close()

    def close(self):
        self.win.grab_release()
        self.win.destroy()
