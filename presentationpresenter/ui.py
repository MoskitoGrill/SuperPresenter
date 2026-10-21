"""PP3 draft editor. Preview and thumbnails share the measured slide plan."""
import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser, ttk
from dataclasses import replace
from difflib import SequenceMatcher
from .domain import *
from .settings import load_settings, save_settings
from .layout import paginate, Typography, LayoutError, geometry
from .rendering import TkMetrics, draw
from .editor import History, duplicate_section, blank_document, editable_section, merge_sections
from .keyboard_controls import bind_navigation, section_destination, TEXT_INPUTS
from .playback import Playback
from .session import ProjectionSession
from .projection import monitors, ProjectionWindow
from .projection_controls import ProjectionControls
from . import anchors
from . import storage, media
from .recovery import Recovery
from .settings import settings_path
from pathlib import Path
from .paths import presentation_directory
from .ribbon import Ribbon, wrap_row, command_group, space_control_rows
from .ribbon_icons import command_icon
from .navigation_bar import NavigationLayout
from .appearance import appearance, scrollbar, reserve_button_labels
from .window_paint import repaint_workspace

THUMBNAIL_WIDTH = 190
SLIDE_STRIP_HEIGHT = 190


class MainWindow:
    def default_document(self):
        document = blank_document(self.default_content_style())
        return replace(document, stream=replace(document.stream, camera=self.settings.default_camera()))

    def default_content_style(self):
        return TextStyle(family=self.settings.content_font_family, size=self.settings.content_font_size)

    def save_content_defaults(self):
        family = self.metrics.available_families.get(self.default_family.get().strip().casefold())
        if family is None:
            self.status.set('Vyberte nainstalovaný font.')
            return
        try:
            size = int(self.default_size.get().strip())
            if not 8 <= size <= 144:
                raise ValueError()
        except ValueError:
            self.status.set('Velikost musí být celé číslo od 8 do 144 px.')
            return
        updated = replace(self.settings, content_font_family=family, content_font_size=size)
        try:
            save_settings(updated)
        except OSError as exc:
            messagebox.showerror('Nastavení', f'Nastavení se nepodařilo uložit: {exc}', parent=self.root)
            return
        self.settings = updated
        self.default_family.set(family)
        self.default_size.set(str(size))
        self.status.set(f'Výchozí písmo uloženo: {family}, {size} px. Platí pro nový obsah.')

    def __init__(self, root, settings=None, recovery_dir=None):
        self.root, self.settings = root, settings or load_settings()
        self.appearance = appearance(root, self.settings)
        self.document = self.default_document()
        self.history = History(self.document)
        self.saved_document = self.document
        self.file_path = None
        self.document_files = {}
        self.file_context = object()
        self.document_contexts = {id(self.document): self.file_context}
        self.autosave_job = None
        self.resize_job = None
        self.resizing_workspace = False
        self.recovery = Recovery(recovery_dir or settings_path().parent / 'recovery')
        self.image_editor = None
        self.bible_window = None
        self.preflight_window = None
        self.metrics = TkMetrics(root, self.settings.font_family)
        self.typography = Typography()
        self.selected_id = self.document.sections[0].id
        self.current, self.plan = 1, None
        self.preview_section = None
        self.pending = self.group_timer = None
        self.loading = False
        self.styles, self.thumbnails = {}, []
        self.typing_override = None
        self.typing_position = None
        self.size_target = None
        self.thumbnail_width = THUMBNAIL_WIDTH
        self.strip_wheel_delta = 0
        self.session = None
        self.playback = Playback(root, lambda: self.session, self.playback_advance, self.playback_status)
        self.draft_plan = None
        self.live_anchor = None
        self.anchor_versions = {}
        self.deleted_anchor_start = None
        self.anchor_tracks = {}
        self.exact_positions = {}
        self.switch_slide_id = None
        self.preview_origin_id = None
        self.projected_thumbnail_index = None
        self.draft_current = 0
        self.projections = {}
        self.monitor_choices = {}
        self.monitor_menus = {}
        self.monitor_inventory = []
        self.monitor_error = None
        self.monitor_job = None
        root.title('PresentationPresenter — PP8L')
        root.geometry(self.settings.geometry)
        root.minsize(900, 600)
        chrome = tk.Frame(root)
        chrome.pack(fill='x')
        self.workspace = tk.PanedWindow(root, orient='vertical', sashwidth=8, showhandle=True,
                                       sashrelief='raised', background='#777777',
                                       sashcursor='sb_v_double_arrow', handlesize=14,
                                       opaqueresize=True)
        self.workspace.bind('<ButtonRelease-1>', self.finish_workspace_resize)
        self.bottom_bar = tk.Frame(self.workspace)
        self.ribbon = Ribbon(chrome, close=self.close, temporary_tabs=self.settings.temporary_ribbon_tabs)
        self.ribbon.frame.pack_configure(side='left', fill='both', expand=True)
        filebar = self.ribbon.add('Soubor')
        home = self.ribbon.add('Domů')
        sources = self.ribbon.add('Úseky')
        auto_bar = self.ribbon.add('Auto')
        display_bar = self.ribbon.add('Zobrazení')
        preferences = self.ribbon.add('Nastavení')
        visibility = command_group(preferences, 'Zobrazit ovládací tlačítka')
        self.visibility_vars = {}
        self.visibility_buttons = {}
        for field, label in (('show_projection_button', 'Spuštění / ukončení projekce'),
                             ('show_apply_button', 'Použít do projekce'),
                             ('show_navigation_buttons', 'Přepínání snímků a úseků')):
            var = tk.BooleanVar(value=getattr(self.settings, field))
            self.visibility_vars[field] = var
            button = tk.Button(visibility, text=label,
                command=lambda field=field: self.toggle_control_visibility(field), takefocus=True)
            button.pack(fill='x')
            self.visibility_buttons[field] = button
        self.visibility_save_button = self.button(visibility, 'Uložit defaultně', self.save_control_visibility)
        self.visibility_save_button.pack_configure(side='top', anchor='w', pady=(4, 0))
        defaults = command_group(preferences, 'Výchozí písmo')
        defaults_row = tk.Frame(defaults)
        defaults_row.pack(fill='x', padx=(0, 10))
        self.default_family = tk.StringVar(value=self.settings.content_font_family)
        self.default_size = tk.StringVar(value=str(self.settings.content_font_size))
        tk.Label(defaults_row, text='Font:').pack(side='left')
        self.default_family_box = ttk.Combobox(defaults_row, textvariable=self.default_family, width=18,
            values=sorted(self.metrics.available_families.values(), key=str.casefold), style='PP.TCombobox')
        self.default_family_box.pack(side='left', fill='x', expand=True, padx=(4, 2))
        defaults_size_row = tk.Frame(defaults)
        defaults_size_row.pack(fill='x', padx=(0, 10), pady=(4, 0))
        tk.Label(defaults_size_row, text='Velikost:').pack(side='left')
        self.default_size_box = ttk.Combobox(defaults_size_row, textvariable=self.default_size, width=4,
            values=(8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 60, 72, 96, 120, 144), style='PP.TCombobox')
        self.default_size_box.pack(side='left', padx=4)
        tk.Label(defaults_size_row, text='px').pack(side='left')
        self.default_save_button = self.button(defaults_size_row, 'Uložit', self.save_content_defaults)
        self.default_save_button.pack_configure(side='right')
        ribbon_preferences = command_group(preferences, 'Chování lišty')
        self.ribbon_mode_button = tk.Button(ribbon_preferences, command=self.toggle_ribbon_mode)
        self.ribbon_mode_button.pack(fill='x')
        reserve_button_labels(self.ribbon_mode_button, 'Trvale rozbalit', 'Přes obsah')
        self.update_ribbon_mode_label()
        self.ribbon_mode_save_button = self.button(ribbon_preferences, 'Uložit', self.save_ribbon_mode)
        self.ribbon_mode_save_button.pack_configure(side='top', anchor='w', pady=(4, 0))
        folders = command_group(preferences, 'Složky a kamera')
        self.folder_settings_button = self.button(folders, 'Nastavit složky…', self.show_folder_settings)
        self.folder_settings_button.pack_configure(side='top', fill='x')
        self.camera_settings_button = self.button(folders, 'Kamera streamu…', self.show_camera_settings)
        self.camera_settings_button.pack_configure(side='top', fill='x')
        image_preferences = command_group(preferences, 'Úpravy obrázků')
        self.direct_image_edit = tk.BooleanVar(value=self.settings.direct_image_edit)
        self.direct_image_edit_check = tk.Checkbutton(image_preferences,
            text='Úprava obrázků napřímo', indicatoron=False,
            selectcolor=self.appearance.selected, relief='raised', offrelief='raised',
            variable=self.direct_image_edit, command=self.save_direct_image_edit)
        self.direct_image_edit_check.pack(anchor='w')
        file_commands = command_group(filebar, 'Prezentace')
        file_rows = [tk.Frame(file_commands) for _ in range(4)]
        for row in file_rows:
            row.pack(fill='x')
        self.new_button = self.button(file_rows[0], 'Nová', self.new_document)
        self.open_button = self.button(file_rows[1], 'Otevřít', self.open_document)
        self.save_button = self.button(file_rows[2], 'Uložit', self.save_document)
        self.save_as_button = self.button(file_rows[3], 'Uložit jako', lambda: self.save_document(True))
        self.file_start_buttons = self.add_start_controls(filebar)
        self.preflight_button = self.button(self.file_start_buttons[0].master, 'Kontrola', self.show_preflight)
        self.preflight_button.pack_configure(side='top', fill='x')
        transfer = command_group(filebar, 'Přenos')
        for label, command in (('Import PPTX', self.import_pptx), ('Import JSON', self.import_document)):
            self.button(transfer, label, command).pack_configure(side='top', fill='x')
        for sequence, command in (('<Control-s>', self.save_document), ('<Control-o>', self.open_document)):
            root.bind(sequence, lambda e, c=command: (c(), 'break')[1])
        history = command_group(filebar, 'Historie')
        self.undo_button = self.button(history, 'Zpět', self.undo)
        self.redo_button = self.button(history, 'Znovu', self.redo)
        for button in (self.undo_button, self.redo_button):
            button.pack_configure(side='top', fill='x', pady=1)
        self.aspects = {}
        for label, field in (('Sál', 'hall'), ('Stream', 'stream')):
            var = tk.StringVar(value=getattr(self.document, field).aspect.value)
            self.aspects[field] = var
        self.black_start = tk.BooleanVar(value=True)
        self.black_end = tk.BooleanVar(value=True)
        self.black_end_button = tk.Checkbutton(command_group(filebar, 'Zakončení'), text='Černý konec',
            indicatoron=False, selectcolor=self.appearance.selected, relief='raised', offrelief='raised',
            variable=self.black_end, command=lambda: self.commit(replace(self.document, black_end=self.black_end.get())))
        self.black_end_button.pack(side='left')
        self.monitor_choices = {f: tk.StringVar() for f in ('hall', 'stream')}
        timing = command_group(auto_bar, 'Časování')
        auto_actions = command_group(auto_bar, 'Přehrávání')
        tk.Label(timing, text='Interval (s):').grid(row=0, column=0, padx=4)
        self.auto_interval = tk.StringVar(value='5')
        tk.Entry(timing, textvariable=self.auto_interval, width=8).grid(row=0, column=1, padx=4)
        self.auto_repeat = tk.BooleanVar(value=False)
        tk.Checkbutton(timing, text='Opakovat', variable=self.auto_repeat).grid(row=1, column=0, columnspan=2, sticky='w', padx=4)
        tk.Button(auto_actions, text='Zapnout', command=self.start_playback).grid(row=0, column=0, padx=4)
        self.auto_stop_button = tk.Button(auto_actions, text='Stop auto', command=self.playback.stop)
        self.auto_stop_button.grid(row=0, column=1, padx=4)
        self.auto_status = tk.StringVar(value='Zastaveno')
        tk.Label(auto_actions, textvariable=self.auto_status).grid(row=1, column=0, columnspan=2, sticky='w', padx=4)
        body = tk.PanedWindow(self.workspace, orient='horizontal', sashwidth=7,
                              opaqueresize=True)
        self.body = body
        body.bind('<ButtonRelease-1>', self.finish_workspace_resize)
        self.workspace.add(body, minsize=220, stretch='always')
        source_list = command_group(sources, 'Zdrojové úseky')
        self.sections = tk.Listbox(source_list, exportselection=False, height=4, width=16)
        self.section_scrollbar = scrollbar(source_list, command=self.sections.yview)
        self.sections.configure(yscrollcommand=self.section_scrollbar.set)
        self.section_scrollbar.pack(side='right', fill='y')
        self.sections.pack(fill='both', expand=True)
        self.sections.bind('<<ListboxSelect>>', self.select_section)
        self.sections_window_button = tk.Button(source_list, text='Zobrazit všechny…', command=self.show_sections_window)
        self.sections_window_button.pack(fill='x', pady=(4, 0))
        self.source_buttons = []
        movement = command_group(sources, 'Přesouvání')
        source_actions = command_group(sources, 'Úpravy úseků')
        for parent, label, command in ((movement, '↑ Nahoru', lambda: self.move_section(-1)), (movement, '↓ Dolů', lambda: self.move_section(1)), (source_actions, '+ Úsek', self.add_section), (source_actions, 'Smazat', self.delete_section), (source_actions, 'Duplikovat', self.copy_section)):
            button = tk.Button(parent, text=label, command=command)
            if parent is movement:
                button.pack(fill='x', pady=1)
            else:
                row, column = (0, 1) if label == 'Duplikovat' else (source_actions.grid_size()[1], 0)
                button.grid(row=row, column=column, sticky='ew', padx=(5, 0) if column else 0, pady=1)
            self.source_buttons.append(button)
        self.copy_slide_button = tk.Button(source_actions, text='Duplikovat slide', command=self.copy_slide)
        self.merge_button = tk.Button(source_actions, text='Sloučit s následujícím', command=self.merge_next_section)
        self.merge_button.grid(row=2, column=0, columnspan=2, sticky='ew', padx=3, pady=2)
        self.copy_slide_button.grid(row=1, column=1, sticky='ew', padx=(5, 0), pady=1)
        source_projection = command_group(sources, 'Projekce a předěly')
        tk.Button(source_projection, text='Zatemnit', command=self.toggle_blackout).pack(anchor='w', pady=1)
        self.break_before = tk.BooleanVar(value=True)
        tk.Checkbutton(source_projection, text='Černý předěl\npřed úsekem', justify='left', variable=self.break_before,
                       command=self.change_break).pack(anchor='w', pady=1)
        self.section_apply_button = self.button(source_projection, 'Použít do projekce', self.apply_live)
        self.section_apply_button.pack_configure(side='top', anchor='w')
        editor = tk.Frame(body)
        preview = tk.Frame(body)
        nav = tk.Frame(preview)
        self.projection_controls = ProjectionControls(self, display_bar, play_parent=nav)
        self.refresh_monitors()
        self.editor_title_label = tk.Label(editor, text='Název / odkaz')
        self.editor_title_label.pack(anchor='w')
        self.title = tk.StringVar()
        self.title_entry = tk.Entry(editor, textvariable=self.title)
        self.title_entry.pack(fill='x', pady=(0, 8))
        self.title.trace_add('write', self.title_changed)
        tk.Label(editor, text='Obsah').pack(anchor='w')
        formatting = command_group(home, 'Písmo')
        self.format_fonts = []
        size_controls = tk.Frame(formatting)
        size_controls.pack(side='left', padx=2)
        font_row = tk.Frame(size_controls)
        font_row.pack(anchor='w')
        self.font_family = tk.StringVar(value=self.metrics.fallback_family)
        self.family_box = ttk.Combobox(font_row, textvariable=self.font_family, width=14,
            values=sorted(self.metrics.available_families.values(), key=str.casefold), style='PP.TCombobox')
        self.family_box.pack(side='left')
        self.family_box.bind('<FocusIn>', self.capture_size_target)
        self.family_box.bind('<Return>', self.apply_font_family)
        self.family_box.bind('<<ComboboxSelected>>', self.apply_font_family)
        self.family_box.bind('<Escape>', self.cancel_font_size)
        self.family_box.bind('<FocusOut>', lambda e: self.sync_font_size())
        size_row = tk.Frame(font_row)
        size_row.pack(side='left', padx=(6, 0))
        self.font_size = tk.StringVar(value='36')
        self.size_box = ttk.Combobox(size_row, textvariable=self.font_size, width=4,
            values=(8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 60, 72, 96, 120, 144), style='PP.TCombobox')
        self.size_box.pack(side='left')
        tk.Label(size_row, text='px').pack(side='left')
        self.size_box.bind('<FocusIn>', self.capture_size_target)
        self.size_box.bind('<Return>', self.apply_font_size)
        self.size_box.bind('<<ComboboxSelected>>', self.apply_font_size)
        self.size_box.bind('<Escape>', self.cancel_font_size)
        self.size_box.bind('<FocusOut>', lambda e: self.sync_font_size())
        emphasis_row = tk.Frame(size_controls)
        emphasis_row.pack(anchor='w', pady=(4, 0))
        for label, field in (('B', 'bold'), ('I', 'italic'), ('U', 'underline')):
            button = self.button(emphasis_row, label, lambda f=field: self.format_selection(f))
            font = self.appearance.text.copy()
            font.configure(**{'bold': {'weight': 'bold'}, 'italic': {'slant': 'italic'}, 'underline': {'underline': True}}[field])
            self.format_fonts.append(font)
            button.configure(font=font, width=2)
        color_button = self.button(emphasis_row, 'Barva', self.choose_color)
        color_button.pack_configure(padx=(12, 2))
        color_button.icon = command_icon(root, 'bucket', self.appearance.foreground)
        color_button.configure(image=color_button.icon, width=color_button.icon.width()+8, height=color_button.icon.height()+4)
        bullets = self.button(command_group(home, 'Odstavce'), 'Odrážky / odstavce', self.toggle_bullets)
        bullets.icon = command_icon(root, 'bullets', self.appearance.foreground)
        bullets.configure(image=bullets.icon, width=bullets.icon.width()+8, height=bullets.icon.height()+4)
        self.numbered_button = self.button(bullets.master, 'Číslovaný seznam', lambda: self.toggle_bullets(BlockKind.NUMBERED))
        self.numbered_button.icon = command_icon(root, 'numbered', self.appearance.foreground)
        self.numbered_button.configure(image=self.numbered_button.icon, width=self.numbered_button.icon.width()+8, height=self.numbered_button.icon.height()+4)
        insertbar = command_group(home, 'Vložit')
        self.button(insertbar, 'Bible', self.open_bible)
        self.button(insertbar, 'Obrázek', self.choose_image)
        image_commands = command_group(home, 'Obrázky')
        self.button(image_commands, 'Rozložení obrázků', self.edit_images).pack_configure(side='top', fill='x')
        self.image_edit_button = self.button(image_commands, 'Upravit obrázky', lambda: self.preview_image_edit.toggle())
        self.image_edit_button.pack_configure(side='top', fill='x')
        self.ribbon.show('Domů')
        text_frame = tk.Frame(editor)
        self.editor_text_frame = text_frame
        text_frame.configure(highlightthickness=1, highlightbackground='#888888')
        text_frame.pack(fill='both', expand=True)
        self.text = tk.Text(text_frame, wrap='word', undo=False, exportselection=False, font=(self.settings.font_family, 12), padx=8, pady=8, highlightthickness=0)
        text_scrollbar = scrollbar(text_frame, command=self.text.yview)
        self.text.configure(yscrollcommand=text_scrollbar.set)
        text_scrollbar.pack(side='right', fill='y')
        self.text.pack(fill='both', expand=True)
        self.text.tag_configure('bullet', lmargin1=18, lmargin2=18, background='#505050')
        self.text.tag_configure('numbered', lmargin1=18, lmargin2=18, background='#50505e')
        self.text.tag_configure('preview_content', background='#5a5a5a')
        for level in range(3):
            self.text.tag_configure(f'listlevel:{level}', lmargin1=18+24*level, lmargin2=18+24*level)
        self.text.bind('<Tab>', lambda e: self.change_list_level(1, e))
        self.text.bind('<Shift-Tab>', lambda e: self.change_list_level(-1, e))
        if root.tk.call('tk', 'windowingsystem') == 'x11':
            self.text.bind('<ISO_Left_Tab>', lambda e: self.change_list_level(-1, e))
        self.text.bind('<<Modified>>', self.text_changed)
        self.text.bind('<KeyRelease>', lambda e: self.sync_font_size())
        self.text.bind('<ButtonRelease-1>', lambda e: self.sync_font_size())
        self.text_original = self.text._w + '_original'
        self.root.tk.call('rename', self.text._w, self.text_original)
        self.root.tk.createcommand(self.text._w, self.text_operation)
        self.text.bind('<Return>', self.insert_newline)
        self.text.bind('<<Paste>>', self.paste_text)
        for widget in (self.text, self.title_entry):
            widget.bind('<FocusOut>', lambda e: self.end_group())
        body.add(preview, width=650, minsize=300, stretch='never')
        panel_width = 380
        body.add(editor, width=panel_width, minsize=panel_width, stretch='always')
        root.minsize(max(900, panel_width+340), 600)
        output_bar = tk.Frame(preview)
        output_bar.pack(fill='x')
        self.preview_output_bar = output_bar
        output_actions = tk.Frame(output_bar)
        output_actions.pack(side='left', fill='x', expand=True)
        self.output = tk.StringVar(value='hall')
        self.view_version = tk.StringVar(value='live')
        self.draft_button = self.button(output_actions, 'Rozpracovaná verze', self.toggle_draft_preview)
        self.draft_button_background = self.draft_button.cget('background')
        self.output_button = self.button(output_actions, 'Stream', self.toggle_preview_output)
        reserve_button_labels(self.output_button, 'Sál', 'Stream')
        apply_row = tk.Frame(editor)
        self.editor_apply_row = apply_row
        apply_row.pack(side='bottom', fill='x', pady=(4, 0))
        self.apply_button = self.button(apply_row, 'Použít do projekce', self.apply_live)
        self.unapplied_changes = tk.StringVar()
        self.unapplied_label = tk.Label(apply_row, textvariable=self.unapplied_changes, anchor='w', fg=self.appearance.warning, font=self.appearance.small)
        self.unapplied_label.pack(side='left', padx=6)
        self.arrange_apply_row = wrap_row(apply_row)
        text_frame.pack_forget()
        text_frame.pack(fill='both', expand=True)
        self.version_status = tk.StringVar()
        self.layout_warning = tk.StringVar()
        self.layout_warning_label = tk.Label(preview, textvariable=self.layout_warning, fg=self.appearance.error, anchor='w', wraplength=400)
        self.preview = tk.Canvas(preview, bg='black', highlightthickness=0)
        self.preview.pack(fill='both', expand=True)
        self.preview.bind('<Configure>', self.queue_workspace_resize)
        body.bind('<Configure>', self.queue_workspace_resize)
        self.preview.bind('<Button-1>', lambda e: self.preview.focus_set())
        from .preview_image_edit import PreviewImageEdit
        self.preview_image_edit = PreviewImageEdit(self)
        nav.pack(side='bottom', fill='x')
        self.preview_navigation = nav
        self.projection_controls.play.pack(side='left', padx=2, anchor='n')
        self.navigation_group = tk.Frame(nav)
        self.previous_section_button = self.button(self.navigation_group, '<<', lambda: self.navigate_presenter('previous_section'))
        self.previous_slide_button = self.button(self.navigation_group, '<', lambda: self.jump(self.current-1))
        self.location = tk.StringVar()
        self.location_label = tk.Label(self.navigation_group, textvariable=self.location)
        self.location_label.pack(side='left', padx=4)
        self.next_slide_button = self.button(self.navigation_group, '>', lambda: self.jump(self.current+1))
        self.next_section_button = self.button(self.navigation_group, '>>', lambda: self.navigate_presenter('next_section'))
        self.navigation_layout = NavigationLayout(nav, self.projection_controls.play, self.navigation_group,
            (self.previous_section_button, self.previous_slide_button, self.next_slide_button, self.next_section_button),
            self.location_label, self.settings.font_family)
        self.header_location_label = tk.Label(output_bar, textvariable=self.location,
            font=self.navigation_layout.counter_font, width=11, anchor='e')
        self.body.paneconfigure(preview, minsize=self.navigation_layout.minimum_width)
        root.minsize(max(900, self.navigation_layout.minimum_width+panel_width+31), 600)
        wrap_row(output_actions)
        for panel in self.ribbon.panels.values():
            space_control_rows(panel)
            wrap_row(panel, stretch_groups=True)
        self.ribbon.reserve_height([
            lambda width, panel=panel: panel.wrapped_height(max(1, width-8))+8
            for panel in self.ribbon.panels.values()
        ])
        self.preview.pack_forget()
        self.preview.pack(fill='both', expand=True)
        self.status = tk.StringVar()
        self.file_status = tk.StringVar()
        self.display_status = tk.StringVar()
        self.status.trace_add('write', lambda *args: self.update_file_status())
        tk.Label(root, textvariable=self.display_status, anchor='w', fg=self.appearance.muted, font=self.appearance.small).pack(side='bottom', fill='x', padx=8)
        strip_frame = tk.Frame(self.bottom_bar)
        self.strip_frame = strip_frame
        strip_frame.pack(side='left', fill='both', expand=True)
        self.strip = tk.Canvas(strip_frame, height=SLIDE_STRIP_HEIGHT, highlightthickness=0)
        horizontal = scrollbar(strip_frame, orient='horizontal', command=self.strip.xview)
        self.strip.configure(xscrollcommand=horizontal.set, xscrollincrement=30)
        horizontal.pack(side='bottom', fill='x')
        self.strip.pack(fill='both', expand=True)
        self.strip_inner = tk.Frame(self.strip)
        self.strip.create_window(0, 0, window=self.strip_inner, anchor='nw')
        self.strip_inner.bind('<Configure>', lambda e: self.strip.configure(scrollregion=self.strip.bbox('all')))
        self.strip.bind('<Configure>', self.queue_workspace_resize)
        self.workspace.add(self.bottom_bar, minsize=100, height=SLIDE_STRIP_HEIGHT+horizontal.winfo_reqheight(), stretch='never')
        self.workspace.pack(fill='both', expand=True, padx=8, pady=6)
        for sequence in ('<MouseWheel>', '<Shift-MouseWheel>', '<Button-4>', '<Button-5>'):
            root.bind(sequence, self.thumbnail_wheel, add='+')
        # Toplevel bindings run after the native Panedwindow class binding.
        # Paint its completed move before processing the next motion event.
        root.bind('<B1-Motion>', self.paint_sash_motion, add='+')
        for sequence, command in (('<Control-z>', self.undo), ('<Control-y>', self.redo), ('<Control-Shift-Z>', self.redo)):
            root.bind(sequence, lambda e, c=command: (c(), 'break')[1])
        self.refresh_sections()
        self.load_editor()
        self.rebuild()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Delete>', self.delete_black_slide)
        root.bind('<Button-1>', self.leave_text_input, add='+')
        bind_navigation(root, self)
        root.bind('<KeyPress-b>', self.blackout_key)
        root.bind('<KeyPress-B>', self.blackout_key)
        self.bind_editing_shortcuts()
        from .font_suggestions import FontSuggestions
        self.font_suggestions = FontSuggestions(root, self.family_box, self.font_family,
            self.metrics.available_families.values(), self.apply_font_family, self.cancel_font_size, self.appearance)
        root.bind('<Destroy>', self.destroyed, add='+')
        self.projection_controls.update_summary()
        self.projection_controls.choose()
        if self.projection_controls.load_error:
            self.status.set('Profily nelze načíst: '+self.projection_controls.load_error)
        if hasattr(root, 'drop_target_register'):
            root.drop_target_register('DND_Files')
            root.dnd_bind('<<Drop>>', self.drop_images)
        self.autosave_job = root.after(1000, self.offer_recovery)
        self.apply_control_visibility()

    def update_ribbon_mode_label(self):
        self.ribbon_mode_button.configure(text=('Přes obsah'
            if self.ribbon.temporary_tabs else 'Trvale rozbalit'))

    def toggle_ribbon_mode(self):
        self.ribbon.set_temporary_tabs(not self.ribbon.temporary_tabs)
        self.update_ribbon_mode_label()
        self.status.set('Chování lišty změněno. Pro příští spuštění klikněte na Uložit.')

    def save_ribbon_mode(self):
        updated = replace(self.settings, temporary_ribbon_tabs=self.ribbon.temporary_tabs)
        try:
            save_settings(updated)
        except OSError as exc:
            messagebox.showerror('Nastavení', f'Nastavení se nepodařilo uložit: {exc}', parent=self.root)
            return
        self.settings = updated
        self.status.set('Výchozí chování lišty uloženo pro příští spuštění aplikace.')

    def save_control_visibility(self):
        updated = replace(self.settings, **{field: var.get() for field, var in self.visibility_vars.items()})
        try:
            save_settings(updated)
        except OSError as exc:
            messagebox.showerror('Nastavení', f'Nastavení se nepodařilo uložit: {exc}', parent=self.root)
            return
        self.settings = updated
        self.status.set('Výchozí zobrazení tlačítek uloženo.')

    def add_start_controls(self, panel):
        group = command_group(panel, 'Spuštění projekce')
        buttons = []
        for label, from_current in (('Spustit', False), ('Spustit od', True)):
            button = self.button(group, label,
                lambda current=from_current: self.projection_controls.start(from_current=current))
            button.pack_configure(side='top', fill='x')
            buttons.append(button)
        return buttons

    def toggle_control_visibility(self, field):
        var = self.visibility_vars[field]
        var.set(not var.get())
        self.apply_control_visibility()

    def apply_control_visibility(self):
        for field, button in self.visibility_buttons.items():
            color = self.appearance.panel if self.visibility_vars[field].get() else '#3c3c3c'
            button.configure(background=color, highlightbackground=color)
        self.navigation_layout.set_visibility(self.visibility_vars['show_projection_button'].get(),
                                              self.visibility_vars['show_navigation_buttons'].get())
        if self.visibility_vars['show_navigation_buttons'].get():
            self.header_location_label.pack_forget()
        else:
            self.header_location_label.pack(side='right', padx=(6, 4))
        self.apply_button.layout_hidden = not self.visibility_vars['show_apply_button'].get()
        self.arrange_apply_row()
        self.align_editor_preview()
        self.queue_workspace_resize()

    def save_direct_image_edit(self):
        updated = replace(self.settings, direct_image_edit=self.direct_image_edit.get())
        try:
            save_settings(updated)
        except OSError as exc:
            self.direct_image_edit.set(self.settings.direct_image_edit)
            messagebox.showerror('Nastavení', 'Volbu se nepodařilo uložit: '+str(exc), parent=self.root)
            return
        self.settings = updated
        self.preview_image_edit.preference_changed()

    def toggle_preview_output(self):
        self.output.set('stream' if self.output.get() == 'hall' else 'hall')
        self.output_button.configure(text='Sál' if self.output.get() == 'stream' else 'Stream')
        self.render_preview()

    def toggle_draft_preview(self):
        self.view_version.set('live' if self.view_version.get() == 'draft' else 'draft')
        self.switch_version()

    def queue_workspace_resize(self, event=None):
        # A timer, rather than after_idle: idle painting can starve while native
        # sash motion continuously supplies Windows events.
        if self.resize_job is None and not self.resizing_workspace:
            self.resize_job = self.root.after(16, self.flush_workspace_resize)

    def finish_workspace_resize(self, event=None):
        if self.resize_job is not None:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(0, self.flush_workspace_resize)

    def paint_sash_motion(self, event):
        if event.widget in (self.workspace, self.body):
            self.flush_workspace_resize()

    def flush_workspace_resize(self):
        if self.resize_job is not None:
            self.root.after_cancel(self.resize_job)
        self.resize_job = None
        if self.resizing_workspace:
            return
        self.resizing_workspace = True
        try:
            # Only service geometry/painting here, never input or timer events.
            # The guard suppresses Configure callbacks generated by this work.
            for _ in range(2):
                self.root.update_idletasks()
                if not self.fit_preview_width():
                    break
            self.root.update_idletasks()
            self.align_editor_preview()
            self.root.update_idletasks()
            self.ensure_editor_space()
            self.root.update_idletasks()
            self.resize_thumbnail_strip()
            self.render_preview()
            self.root.update_idletasks()
            self.redraw_resize_controls()
            self.root.update_idletasks()
        finally:
            repaint_workspace(self.workspace)
            self.resizing_workspace = False

    def ensure_editor_space(self):
        # A high-DPI ribbon must not squeeze the writing area to one pixel.
        # Reclaim only excess thumbnail height; keep the existing 100px minimum.
        linespace = int(self.root.tk.call('font', 'metrics', self.text.cget('font'), '-linespace'))
        minimum = 2*linespace+8
        required = (self.root.winfo_height()-self.workspace.winfo_height()
                    + self.body.winfo_height()-self.text.winfo_height()+minimum+110)
        width, height = self.root.minsize()
        minimum_height = max(600, min(required, self.root.winfo_screenheight()-80))
        if height != minimum_height:
            self.root.minsize(width, minimum_height)
        missing = minimum-self.text.winfo_height()
        if missing > 0 and self.workspace.winfo_height() > 110:
            x, y = self.workspace.sash_coord(0)
            target = min(y+missing, self.workspace.winfo_height()-110)
            if target > y:
                self.workspace.sash_place(0, x, target)

    def align_editor_preview(self):
        """Keep the writing fields aligned with the preview, including wrapped controls."""
        label = self.editor_title_label
        top = max(0, self.preview.winfo_y()-label.winfo_reqheight())
        label.pack_configure(pady=(top, 0))
        compact = not any(var.get() for var in self.visibility_vars.values())
        self.preview_navigation.configure(height=8 if compact else self.navigation_layout.normal_height)
        hide_actions = compact and not self.unapplied_changes.get()
        if hide_actions:
            self.editor_apply_row.pack_forget()
        else:
            self.editor_apply_row.pack(side='bottom', fill='x', before=self.editor_text_frame)
        navigation = self.preview_navigation.winfo_reqheight()
        actions = 0 if hide_actions else self.editor_apply_row.winfo_reqheight()+4
        footer = max(navigation, actions)
        self.preview.pack_configure(pady=(0, footer-navigation))
        self.editor_text_frame.pack_configure(pady=(0, footer) if hide_actions else 0)
        if not hide_actions:
            self.editor_apply_row.pack_configure(pady=(4, footer-actions))

    def redraw_resize_controls(self):
        # Native child-window moves on Windows can leave copied pixels behind.
        # Ask the moved controls to paint after all sibling geometry has settled.
        def expose(widget):
            if widget.winfo_class() == 'Text':
                return
            if widget.master is self.strip_inner:
                left = widget.winfo_rootx()
                strip_left = self.strip.winfo_rootx()
                if left+widget.winfo_width() < strip_left or left > strip_left+self.strip.winfo_width():
                    return
            if widget.winfo_class() in {'Frame', 'Panedwindow', 'Canvas', 'Label', 'Button', 'Checkbutton', 'Entry', 'Scrollbar'}:
                widget.event_generate('<Expose>')
            for child in widget.winfo_children():
                expose(child)
        expose(self.workspace)

    def thumbnail_wheel(self, event):
        widget = event.widget
        while widget is not None and widget is not self.strip_frame:
            widget = getattr(widget, 'master', None)
        if widget is None:
            return
        if getattr(event, 'num', None) in (4, 5):
            steps = 1 if event.num == 4 else -1
        else:
            self.strip_wheel_delta += event.delta / 120
            steps = int(self.strip_wheel_delta)
            self.strip_wheel_delta -= steps
        if steps:
            self.strip.xview_scroll(-steps*3, 'units')
        return 'break'

    def resize_thumbnail_strip(self, event=None):
        if not self.plan or not self.thumbnails or len(self.thumbnails) != len(self.plan.slides):
            return
        height = self.strip.winfo_height()
        if height < 2:
            return
        width, slide_height, _, _ = geometry(self.plan.source.hall)
        caption_height = self.thumbnails[0].master.winfo_children()[1].winfo_reqheight()
        target = max(60, round(max(30, height-caption_height-10)*width/slide_height))
        resized = target != self.thumbnail_width
        self.thumbnail_width = target
        for canvas, slide in zip(self.thumbnails, self.plan.slides):
            canvas.master.configure(width=target+12, height=height)
            if resized:
                canvas.configure(width=target, height=round(target*slide_height/width))
                draw(canvas, slide, 'hall', self.metrics, self.typography, scale=target/width)
        self.strip.configure(scrollregion=(0, 0, len(self.thumbnails)*(target+18), height))

    def fit_preview_width(self, event=None):
        # Limit the entire left workspace, not just the painted slide. The
        # editor receives the excess width for either hall/stream aspect.
        height = self.preview.winfo_height()
        if height < 40 or not self.preview.winfo_ismapped():
            return
        available = self.body.winfo_width() - 380 - 11
        target = max(self.navigation_layout.minimum_width, min(round(height * 16 / 9), available))
        x, _ = self.body.sash_coord(0)
        if abs(x-target) > 2:
            self.body.sash_place(0, target, 0)
            return True

    def leave_text_input(self, event):
        widget = event.widget
        if widget.winfo_exists() and widget.winfo_toplevel() == self.root and widget.winfo_class() not in TEXT_INPUTS | {'Scrollbar', 'TScrollbar'}:
            focused = self.root.focus_get()
            if focused is not None and focused.winfo_class() in TEXT_INPUTS:
                self.root.focus_set()

    def navigate_presenter(self, target):
        if self.session:
            slides = self.session.plan.slides
            if not slides:
                return
            current = next(i for i, slide in enumerate(slides) if slide.id == self.session.current_slide_id)
            if target in ('previous_section', 'next_section'):
                target_index = section_destination(self.session.plan, current, 1 if target == 'next_section' else -1)
                target = target_index - current
            index = 0 if target == 'first' else len(slides)-1 if target == 'last' else max(0, min(current + target, len(slides)-1))
            self.playback_advance(index)
            self.playback.reset()
        elif self.plan and self.plan.slides:
            if target in ('previous_section', 'next_section'):
                target = section_destination(self.plan, self.current, 1 if target == 'next_section' else -1) - self.current
            self.jump(0 if target == 'first' else len(self.plan.slides)-1 if target == 'last' else self.current + target)

    def playback_status(self):
        if hasattr(self, 'auto_status'):
            self.auto_status.set('Pozastaveno zatemněním' if self.playback.running and self.session and self.session.blackout else 'Běží' if self.playback.running else 'Zastaveno')

    def start_playback(self):
        try:
            if not self.playback.start(self.auto_interval.get(), self.auto_repeat.get()):
                self.status.set('Nejprve spusťte projekci.')
        except ValueError as exc:
            self.status.set(str(exc))

    def playback_advance(self, index):
        # Navigate the confirmed plan even while the operator inspects the draft.
        self.session = replace(self.session, current_slide_id=self.session.plan.slides[index].id)
        self.reset_anchor()
        for window in self.projections.values():
            window.render()
        if self.viewing_live():
            self.jump(index, preserve_anchor=True)
        else:
            self.update_version_status()

    def open_bible(self):
        if self.bible_window and self.bible_window.alive():
            self.bible_window.window.deiconify()
            self.bible_window.window.lift()
            self.bible_window.query_entry.focus_set()
            return self.bible_window
        from .bible_window import BibleWindow
        self.bible_window = BibleWindow(self.root, insert=self.insert_bible_section)
        return self.bible_window

    def insert_bible_section(self, section):
        style = self.default_content_style()
        section = replace(section, blocks=tuple(replace(block, runs=tuple(
            replace(run, style=replace(run.style, family=style.family, size=style.size))
            for run in block.runs)) for block in section.blocks))
        current = self.section()
        if (isinstance(current, TextSection) and not current.images
                and not current.title.strip() and not current.reference.strip()
                and not any(run.text.strip() for block in current.blocks for run in block.runs)):
            filled = replace(current, title=section.title, reference=section.reference,
                             blocks=section.blocks)
            self.preview_section = current.id
            self.commit(replace(self.document, sections=tuple(
                filled if s.id == current.id else s for s in self.document.sections)))
            self.title_entry.focus_set()
        else:
            self.add_section(section)

    def choose_image(self):
        directory = self.file_dialog_directory('image')
        if directory is None:
            return
        path = filedialog.askopenfilename(parent=self.root, initialdir=str(directory), filetypes=[('Obrázky', '*.png *.jpg *.jpeg *.gif *.bmp *.webp')])
        if path:
            self.insert_image(path)

    def insert_image(self, path):
        try:
            asset = media.from_path(path)
            section = editable_section(self.section())
            sections = list(self.document.sections)
            if section is None:
                section = blank_document(self.default_content_style()).sections[0]
                sections.append(section)
            section = replace(section, images=section.images+(ImageItem(asset.id),))
            sections = [section if s.id == section.id else s for s in sections]
            self.selected_id = section.id
            self.preview_section = section.id
            self.commit(replace(self.document, sections=tuple(sections), media=self.document.media+(asset,)))
            self.rebuild()
        except (OSError, ValueError) as exc:
            messagebox.showerror('Obrázek', str(exc), parent=self.root)

    def edit_images(self):
        if self.image_editor and self.image_editor.window.winfo_exists():
            self.image_editor.window.lift()
            return
        section = editable_section(self.section())
        if section is None:
            return
        if section != self.section():
            self.update_section(section)
            self.load_editor()
        from .image_editor import ImageEditor
        self.image_editor = ImageEditor(self, section.id)

    def drop_images(self, event):
        for path in self.root.tk.splitlist(event.data):
            self.insert_image(path)
        return 'copy'

    def finish_editing(self):
        self.text_changed()
        self.end_group()

    def remember_file(self):
        self.document_files[self.file_context] = (self.file_path, self.saved_document)
        self.document_contexts[id(self.document)] = self.file_context

    def update_file_status(self):
        name = Path(self.file_path).name if self.file_path else 'Nová prezentace'
        state = ('neuložené změny' if self.document != self.saved_document else 'uloženo') if self.file_path else 'dosud neuloženo'
        self.file_status.set(f'{name} • {state}')
        missing = set(self.metrics.missing_families(self.document))
        if self.session:
            missing.update(self.metrics.missing_families(self.session.plan.source))
        warning = ('Chybí font: '+', '.join(sorted(missing))+' → '+self.metrics.fallback_family+'   |   ') if missing else ''
        self.display_status.set(f'{self.file_status.get()}   |   {warning}{self.status.get()}')
        self.root.title(f'PresentationPresenter — {name}' + (' *' if self.document != self.saved_document else ''))

    def confirm_document_change(self):
        self.finish_editing()
        if self.document == self.saved_document:
            return True
        answer = messagebox.askyesnocancel('Neuložené změny',
            'Uložit současnou prezentaci před pokračováním?\nAno = uložit, Ne = pokračovat bez uložení, Zrušit = zůstat zde.', parent=self.root)
        return answer is not None and (not answer or self.save_document())

    def bind_editing_shortcuts(self):
        # Run before Tk class bindings (Ctrl+I/M otherwise insert a tab/newline).
        tag = f'PresentationCommands:{self.root}'
        def attach(widget):
            widget.bindtags((tag,) + widget.bindtags())
            for child in widget.winfo_children():
                attach(child)
        attach(self.root)

        def bind(sequence, command, scope=None, keep_list=False):
            def invoke(event):
                if event.state & (0x8 | 0x20000) and not sequence.startswith('<Alt-'):
                    return
                if scope is not None and event.widget is not scope:
                    return
                self.finish_editing()
                command()
                if keep_list:
                    self.sections.focus_set()
                return 'break'
            self.root.bind_class(tag, sequence, invoke)
            self.root.bind(sequence, invoke)

        for sequence, command in (
            ('<Control-n>', self.new_document), ('<Control-o>', self.open_document),
            ('<Control-s>', self.save_document), ('<Control-Shift-S>', lambda: self.save_document(True)),
            ('<Control-m>', self.add_section), ('<Control-Shift-D>', self.copy_slide),
            ('<Control-Return>', lambda: self.apply_live() if self.session else None),
            ('<Control-z>', self.undo), ('<Control-y>', self.redo), ('<Control-Shift-Z>', self.redo)):
            bind(sequence, command)
        for key, field in (('b', 'bold'), ('i', 'italic'), ('u', 'underline')):
            bind(f'<Control-{key}>', lambda field=field: self.format_selection(field), self.text)
        bind('<Control-d>', self.copy_section, self.sections, True)
        bind('<Alt-Up>', lambda: self.move_section(-1), self.sections, True)
        bind('<Alt-Down>', lambda: self.move_section(1), self.sections, True)

    def save_document(self, save_as=False):
        self.finish_editing()
        path = None if save_as else self.file_path
        if not path:
            directory = self.file_dialog_directory('save')
            if directory is None:
                return False
            path = filedialog.asksaveasfilename(parent=self.root, initialdir=str(directory), defaultextension='.ppres', filetypes=[('PresentationPresenter', '*.ppres')])
        if not path:
            return False
        if Path(path).suffix.lower() != '.ppres':
            messagebox.showerror('Uložení', 'Použijte příponu .ppres; původní JSON nelze přepsat.', parent=self.root)
            return False
        try:
            storage.save(path, self.document)
            self.file_path = path
            self.saved_document = self.document
            self.remember_file()
            self.status.set('Uloženo: '+str(path))
            return True
        except (OSError, ValueError) as exc:
            messagebox.showerror('Uložení', str(exc), parent=self.root)
            return False

    def show_folder_settings(self):
        existing = getattr(self, 'folder_settings_window', None)
        if existing and existing.window.winfo_exists():
            existing.window.lift()
            return
        from .folder_settings_window import FolderSettingsWindow
        self.folder_settings_window = FolderSettingsWindow(self)

    def show_camera_settings(self):
        existing = getattr(self, 'camera_settings_window', None)
        if existing and existing.window.winfo_exists():
            existing.window.lift()
            return
        self.finish_editing()
        from .camera_settings_window import CameraSettingsWindow
        self.camera_settings_window = CameraSettingsWindow(self)

    def file_dialog_directory(self, purpose='open'):
        try:
            configured = getattr(self.settings, purpose+'_directory')
            if configured:
                directory = Path(configured)
                try:
                    available = directory.is_dir()
                except OSError:
                    available = False
                if available:
                    return directory
                self.status.set('Výchozí složka není dostupná; použita složka presentation: '+configured)
            return presentation_directory()
        except OSError as exc:
            messagebox.showerror('Složka prezentací', 'Složku presentation nelze připravit: '+str(exc), parent=self.root)
            return None

    def open_document(self):
        if not self.confirm_document_change():
            return
        directory = self.file_dialog_directory()
        if directory is None:
            return
        path = filedialog.askopenfilename(parent=self.root, initialdir=str(directory), filetypes=[('PresentationPresenter', '*.ppres')])
        if not path:
            return
        try:
            document = storage.load(path)
            paginate(document, self.metrics, self.typography)
            self.remember_file()
            self.commit(document)
            self.file_path, self.saved_document = path, document
            self.file_context = object()
            self.remember_file()
            self.rebuild()
            self.refresh_monitors()
            self.status.set('Otevřena rozpracovaná verze. Místní monitory znovu ověřte před projekcí.')
        except (OSError, ValueError) as exc:
            messagebox.showerror('Otevření', str(exc), parent=self.root)

    def import_document(self):
        if not self.confirm_document_change():
            return
        directory = self.file_dialog_directory('import')
        if directory is None:
            return
        path = filedialog.askopenfilename(parent=self.root, initialdir=str(directory), filetypes=[('Původní prezentace', '*.json')])
        if not path:
            return
        try:
            document, warnings = storage.import_legacy(path)
            document = replace(document, stream=replace(document.stream, camera=self.settings.default_camera()))
            paginate(document, self.metrics, self.typography)
            self.remember_file()
            self.commit(document)
            self.file_path = None
            self.saved_document = None
            self.file_context = object()
            self.remember_file()
            self.rebuild()
            messagebox.showwarning('Import JSON', '\n'.join(warnings[:30]), parent=self.root)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Import JSON', str(exc), parent=self.root)

    def import_pptx(self):
        self.finish_editing()
        directory = self.file_dialog_directory('import')
        if directory is None:
            return
        path = filedialog.askopenfilename(parent=self.root, initialdir=str(directory),
                                          filetypes=[('PowerPoint', '*.pptx')])
        if not path:
            return
        from .pptx_import_window import ImportWindow
        review = ImportWindow(self, path)
        self.root.wait_window(review.window)
        if review.accepted is not None:
            try:
                self.insert_pptx_document(review.accepted)
            except (ValueError, OSError) as exc:
                messagebox.showerror('Import PPTX', str(exc), parent=self.root)

    def insert_pptx_document(self, imported):
        """One undo step. Preserve current file context, outputs and live session."""
        self.finish_editing()
        sections = list(self.document.sections)
        index = next((i+1 for i, s in enumerate(sections) if s.id == self.selected_id), len(sections))
        # Replace only the untouched empty starter, not intentional blank sections.
        starter = (self.file_path is None and self.document == self.saved_document and len(sections) == 1
                   and not sections[0].title and isinstance(sections[0], TextSection)
                   and not sections[0].images and not any(r.text for b in sections[0].blocks for r in b.runs))
        if starter:
            sections, index = [], 0
        incoming = list(imported.sections)
        if imported.black_start:
            incoming[0] = replace(incoming[0], break_before=True)
        if imported.black_end and index < len(sections):
            sections[index] = replace(sections[index], break_before=True)
        end = imported.black_end if starter else self.document.black_end or (imported.black_end and index == len(sections))
        sections[index:index] = incoming
        document = replace(self.document, sections=tuple(sections), media=self.document.media+imported.media,
                           black_end=end, black_start=False if starter else self.document.black_start)
        storage.encode(document)
        paginate(document, self.metrics, self.typography)
        self.selected_id = incoming[0].id
        self.preview_section = self.selected_id
        self.commit(document)
        self.rebuild()
        self.status.set('PPTX vloženo do návrhu. Originál beze změny; Zpět vrátí celý import. Živou projekci potvrďte zvlášť.')

    def offer_recovery(self):
        if self.autosave_job:
            self.root.after_cancel(self.autosave_job)
        self.autosave_job = None
        try:
            candidates = self.recovery.candidates()
        except OSError as exc:
            candidates = []
            self.status.set('Seznam obnovy nelze načíst: '+str(exc))
        for path in candidates:
            try:
                document = storage.load(path)
                paginate(document, self.metrics, self.typography)
            except (OSError, ValueError):
                self.status.set('Poškozená rozpracovaná verze ponechána: '+str(path))
                continue
            if messagebox.askyesno('Obnova', f'Obnovit rozpracovanou prezentaci {document.title}?\n{path.name}\nPůvodní recovery soubor zůstane zachován.', parent=self.root):
                self.remember_file()
                self.commit(document)
                self.file_path = None
                self.saved_document = None
                self.file_context = object()
                self.remember_file()
                self.rebuild()
                try:
                    # Save the adopted version before retiring any old journal.
                    self.recovery.write(self.document)
                except (OSError, ValueError) as exc:
                    self.status.set('Obnovenou verzi nelze bezpečně uložit; nabídka obnovy zůstává: '+str(exc))
                    self.autosave_job = self.root.after(5000, self.autosave)
                    return
                break
        for path in candidates:
            try:
                self.recovery.archive(path)
            except (OSError, ValueError) as exc:
                self.status.set('Starší obnovu nelze archivovat; může se nabídnout znovu: '+str(exc))
        self.autosave_job = self.root.after(5000, self.autosave)

    def autosave(self):
        if self.autosave_job:
            self.root.after_cancel(self.autosave_job)
        self.autosave_job = None
        try:
            if self.document != self.saved_document:
                self.recovery.write(self.document)
            else:
                self.recovery.clean()
                self.recovery.last = None
        except (OSError, ValueError) as exc:
            self.status.set('Automatické uložení selhalo: '+str(exc))
        self.autosave_job = self.root.after(5000, self.autosave)

    def refresh_monitors(self):
        if self.monitor_job:
            self.root.after_cancel(self.monitor_job)
        self.monitor_job = None
        try:
            inventory = monitors(self.root)
            self.monitor_error = None
            self.monitor_inventory = inventory
            for field, choice in self.monitor_choices.items():
                if not choice.get() and inventory:
                    choice.set(inventory[min(0 if field == 'hall' else 1, len(inventory)-1)].id)
            if self.projection_controls.editor:
                self.projection_controls.editor.refresh_monitors()
            if hasattr(self, 'status'):
                self.projection_controls.update_summary()
            available = {m.id: m for m in inventory}
            for field, window in list(self.projections.items()):
                if available.get(window.monitor.id) != window.monitor:
                    self.stop_projection(field)
                    self.status.set('Monitor byl odpojen nebo změnil geometrii. Výstup zastaven; vyberte monitor a spusťte jej znovu.')
        except RuntimeError as exc:
            self.monitor_error = str(exc)
            if hasattr(self, 'status'):
                self.status.set(str(exc))
        self.monitor_job = self.root.after(1000, self.refresh_monitors)

    def collect_preflight(self, outputs=None, refresh=True):
        from .preflight import check, Issue
        self.text_changed()
        if refresh:
            self.refresh_monitors_now()
        issues = check(self.document, self.metrics, self.typography, self.monitor_inventory,
                     {f: v.get() for f, v in self.monitor_choices.items()},
                     self.projection_controls.fullscreen,
                     outputs if outputs is not None else self.projection_controls.outputs(),
                     self.draft_plan)
        return issues + ((Issue('Nelze ověřit monitory: '+self.monitor_error),) if self.monitor_error else ())

    def show_preflight(self):
        from .preflight_window import PreflightWindow
        if self.preflight_window and self.preflight_window.win.winfo_exists():
            self.preflight_window.refresh()
            self.preflight_window.win.lift()
        else:
            self.preflight_window = PreflightWindow(self)

    def navigate_preflight(self, issue):
        if not issue.section_id:
            self.ribbon.show('Zobrazení')
            fields = self.projection_controls.outputs()
            if issue.output in fields:
                self.projection_controls.output_index = fields.index(issue.output)
                self.projection_controls.update_summary()
            self.root.lift()
            return
        if not any(s.id == issue.section_id for s in self.document.sections):
            self.status.set('Úsek již neexistuje; obnovte kontrolu.')
            return
        self.text_changed()
        self.view_version.set('draft')
        self.selected_id = issue.section_id
        self.refresh_sections()
        self.preview_section = issue.section_id
        if issue.output:
            self.output.set(issue.output)
            self.output_button.configure(text='Sál' if issue.output == 'stream' else 'Stream')
        self.rebuild()
        if issue.slide_id and self.plan and self.plan.source == self.document:
            index = next((n for n, s in enumerate(self.plan.slides) if s.id == issue.slide_id), None)
            if index is not None:
                self.jump(index)
        self.load_editor()
        self.ribbon.show('Úseky')
        self.root.lift()

    def start_projection(self, outputs, from_current=True):
        camera = getattr(self, 'camera_settings_window', None)
        if camera and camera.test is not None:
            self.status.set('Nejprve ukončete zkušební projekci kamery.')
            return False
        self.text_changed()
        self.refresh_monitors_now()
        if self.monitor_error:
            self.status.set('Projekci nelze spustit: nelze ověřit dostupnost monitorů. '+self.monitor_error)
            return False
        outputs = tuple(outputs)
        if not outputs or any(f not in ('hall', 'stream') for f in outputs):
            self.status.set('Vyberte alespoň jeden platný výstup (Sál / Stream).')
            return False
        if self.session is None:
            issues = self.collect_preflight(outputs, refresh=False)
            if any(i.blocking for i in issues):
                self.show_preflight()
                self.status.set('Projekci nelze spustit: opravte chyby v kontrole před projekcí.')
                return False
        else:
            issues = ()
        targets = {f: next((m for m in self.monitor_inventory if m.id == self.monitor_choices[f].get()), None) for f in outputs}
        if any(m is None for m in targets.values()):
            self.status.set('Vybraný monitor není dostupný. Vyberte dostupný monitor.')
            return False
        if any(f in self.projections and (self.projections[f].monitor != m or self.projections[f].fullscreen != self.projection_controls.fullscreen[f]) for f, m in targets.items()):
            self.status.set('Před změnou monitoru nebo režimu okna zastavte příslušný výstup.')
            return False
        occupied = {f: (w.monitor.id, w.fullscreen) for f, w in self.projections.items()}
        occupied.update({f: (m.id, self.projection_controls.fullscreen[f]) for f, m in targets.items()})
        if len(occupied) > 1 and len({m for m, full in occupied.values()}) < len(occupied) and any(full for m, full in occupied.values()):
            self.status.set('Pro dva výstupy na stejném monitoru vypněte Celá obrazovka u obou.')
            return False
        if self.session is None:
            self.rebuild()
            if not self.plan or self.plan.source != self.document or not self.plan.slides:
                self.status.set('Projekci nelze spustit: připravte platný dokument se snímky.')
                return False
            self.session = replace(ProjectionSession.confirm(self.plan), current_slide_id=self.plan.slides[self.current if from_current else 0].id)
            self.reset_anchor()
        created = []
        try:
            for field, monitor in targets.items():
                if field in self.projections:
                    continue
                self.projections[field] = ProjectionWindow(self, field, monitor, self.projection_controls.fullscreen[field])
                created.append(field)
        except (tk.TclError, RuntimeError) as exc:
            for field in created:
                self.stop_projection(field)
            if not self.projections:
                self.session = None
            self.status.set('Spuštění projekce selhalo: '+str(exc))
            return False
        self.view_version.set('live')
        self.plan = None
        self.rebuild()
        self.projection_controls.update_summary()
        if issues:
            self.status.set(f'Kontrola: {len(issues)} upozornění. Podrobnosti: Soubor → Kontrola.')
        return True

    def refresh_monitors_now(self):
        if self.monitor_job:
            self.root.after_cancel(self.monitor_job)
        self.refresh_monitors()

    def projection_destroyed(self, output, window):
        if self.projections.get(output) is window:
            self.projections.pop(output)
            self.finish_projection()

    def stop_projection(self, output=None):
        for field in ([output] if output else list(self.projections)):
            window = self.projections.pop(field, None)
            if window:
                window.window.destroy()
        self.finish_projection()

    def finish_projection(self):
        if not self.projections:
            self.playback.stop()
        if not self.projections and self.session:
            self.session = None
            self.live_anchor = None
            self.anchor_versions.clear()
            self.anchor_tracks.clear()
            self.exact_positions.clear()
            self.preview_origin_id = None
            self.plan = None
            if self.strip_inner.winfo_exists():
                self.rebuild()
        if self.projection_controls.frame.winfo_exists():
            self.projection_controls.update_summary()

    def blackout_key(self, event):
        if getattr(event, 'state', 0) & (0x4 | 0x8 | 0x20000):
            return
        if event.widget.winfo_class() in ('Text', 'Entry', 'TEntry', 'Spinbox', 'TSpinbox', 'TCombobox'):
            return
        if self.session:
            self.toggle_blackout()
            return 'break'

    def toggle_blackout(self):
        if self.session:
            self.session = replace(self.session, blackout=not self.session.blackout)
            self.playback.reset()
            for window in self.projections.values():
                window.render()
            self.status.set('Projekce zatemněna (B vrátí obsah)' if self.session.blackout else 'Živá potvrzená session • editor je rozpracovaná verze')
            self.update_version_status()

    def reset_anchor(self):
        if self.session.current_slide_id not in self.anchor_tracks or self.session.plan.source not in next(iter(self.anchor_tracks.values())):
            self.anchor_tracks = {}
            for slide in self.session.plan.slides:
                original = anchors.capture(self.session.plan, slide)
                mapped = anchors.relocate(original, self.session.plan.source, self.document)
                self.anchor_tracks[slide.id] = {self.session.plan.source: original, self.document: mapped}
        self.anchor_versions = self.anchor_tracks[self.session.current_slide_id]
        self.live_anchor = self.anchor_versions[self.document]
        self.deleted_anchor_start = None

    def update_anchor(self, document):
        if self.session:
            for sid, versions in self.anchor_tracks.items():
                if document in versions:
                    continue
                anchor = versions[self.document]
                if sid in self.exact_positions:
                    section = next((s for s in document.sections if s.id == anchor.section_id), None)
                    offset = self.exact_positions[sid]
                    for block in section.blocks:
                        length = len(anchors.text(block))
                        if offset <= length:
                            anchor = anchors.Anchor(section.id, block.id, offset)
                            break
                        offset -= length + 1
                    else:
                        anchor = anchors.first(section)
                else:
                    anchor = anchors.relocate(anchor, self.document, document)
                versions[document] = anchor
            self.live_anchor = self.anchor_versions.get(document, self.live_anchor)
        self.exact_positions.clear()

    def text_operation(self, *args):
        insertion_style = None
        if not self.loading and args[0] == 'insert' and args[1] == 'insert' and len(args) == 3:
            insertion_style = self.cursor_style()
            tags = tuple(t for t in self.text.tag_names('insert') if t in ('bullet', 'numbered') or t.startswith('listlevel:'))
            args += (tags + (self.style_tag(insertion_style),),)
        # Intercept the actual edit range before Tk changes it. This distinguishes
        # identical occurrences even when their text and formatting are equal.
        if not self.loading and self.session and args[0] in ('insert', 'delete', 'replace') and self.live_anchor:
            self.text_changed()
            start = self.text.index(args[1])
            end = self.text.index(args[2] if len(args) > 2 else start+'+1c') if args[0] != 'insert' else start
            value = self.text.get('1.0', 'end-1c')
            a = min(len(value), len(self.text.get('1.0', start)))
            b = min(len(value), len(self.text.get('1.0', end)))
            inserted = args[2] if args[0] == 'insert' else (args[3] if args[0] == 'replace' else '')
            for sid, versions in self.anchor_tracks.items():
                tracked = versions[self.document]
                mark = 'block:' + str(tracked.block_id)
                if tracked.section_id != self.selected_id or not tracked.block_id or mark not in self.text.mark_names():
                    continue
                offset = len(self.text.get('1.0', mark)) + tracked.offset
                mapped = anchors.edit(replace(tracked, offset=offset), value, a, b, inserted)
                # The first content slide is the section's beginning, including
                # newly prepended text. Later continuations keep their old text.
                first_slide = next((s for s in self.session.plan.slides if s.section_id == tracked.section_id and not s.black), None)
                if first_slide and first_slide.id == sid and start == end and a == 0:
                    mapped = replace(mapped, offset=0)
                if sid == self.session.current_slide_id:
                    sentence_start, sentence_end = anchors.sentence(value, offset)
                    if args[0] == 'insert' and self.deleted_anchor_start == a:
                        mapped = replace(mapped, offset=a)
                    if args[0] == 'delete' and a <= sentence_start and b >= sentence_end:
                        self.deleted_anchor_start = a
                    elif args[0] != 'insert' or self.deleted_anchor_start != a:
                        self.deleted_anchor_start = None
                self.exact_positions[sid] = mapped.offset
        result = self.root.tk.call(self.text_original, *args)
        if insertion_style is not None:
            self.typing_override = insertion_style
            self.typing_position = self.text.index('insert')
        return result

    def viewing_live(self):
        return self.session is not None and self.view_version.get() == 'live'

    def update_version_status(self):
        if not self.session:
            self.view_version.set('draft')
        draft = self.view_version.get() == 'draft'
        self.draft_button.configure(state='normal' if self.session else 'disabled',
                                    relief='sunken' if draft else 'raised',
                                    background=self.appearance.hover if draft else self.draft_button_background,
                                    highlightbackground=self.appearance.foreground if draft else self.draft_button_background,
                                    disabledforeground=self.appearance.foreground if draft else self.appearance.disabled)
        dirty = self.session and self.session.plan.source != self.document
        self.apply_button.configure(state='normal' if dirty else 'disabled')
        self.section_apply_button.configure(state='normal' if dirty else 'disabled')
        self.unapplied_changes.set('Nepoužité změny' if dirty else '')
        self.arrange_apply_row()
        self.queue_workspace_resize()
        text = ('ŽIVÁ verze • navigace ovládá projekci' if self.viewing_live() else 'ROZPRACOVANÁ verze • navigace mění jen náhled')
        if dirty:
            text += ' • Nepoužité změny'
        if self.session and self.session.blackout:
            text += ' • Projekce zatemněna'
        if self.viewing_live() and self.plan is self.session.plan and self.plan.slides and self.plan.slides[self.current].id != self.session.current_slide_id:
            index = next((i+1 for i, s in enumerate(self.session.plan.slides) if s.id == self.session.current_slide_id), None)
            text += f' • Promítá se snímek {index}'
        self.version_status.set(text)

    def switch_version(self):
        self.text_changed()
        if self.session and self.plan and ((self.plan is self.session.plan) == self.viewing_live()):
            return
        if self.session and self.plan and self.plan.slides:
            slide = self.plan.slides[self.current]
            if self.plan is self.session.plan and not self.viewing_live():
                try:
                    draft = paginate(self.document, self.metrics, self.typography)
                except ValueError as exc:
                    self.view_version.set('live')
                    self.status.set('Rozpracovaný náhled není dostupný: '+str(exc))
                    self.update_version_status()
                    return
                self.switch_slide_id = anchors.locate(draft, self.anchor_tracks[slide.id][self.document])
                self.preview_origin_id = slide.id
            elif self.plan is not self.session.plan and self.viewing_live():
                target = anchors.capture(self.plan, slide)
                target = anchors.relocate(target, self.plan.source, self.document)
                mapped = {sid: versions[self.document] for sid, versions in self.anchor_tracks.items()}
                self.switch_slide_id = self.preview_origin_id or anchors.locate(self.session.plan, target, mapped, self.document)
        self.preview_section = None
        self.plan = None
        self.rebuild()

    def apply_live(self):
        self.text_changed()
        if not self.session:
            return False
        try:
            plan = paginate(self.document, self.metrics, self.typography)
            from .preflight import check
            issues = check(self.document, self.metrics, self.typography, self.monitor_inventory,
                           {f: v.get() for f, v in self.monitor_choices.items()},
                           self.projection_controls.fullscreen, self.projection_controls.outputs(), plan)
            failure = next((i for i in issues if i.blocking and i.section_id), None)
            if failure:
                self.status.set('Změny nebyly použity: '+failure.message+' Otevřete Soubor → Kontrola.')
                return False
            position = anchors.confirmed_position(self.session.plan, self.session.current_slide_id, plan, self.live_anchor)
            session = ProjectionSession(plan, position, self.session.blackout)
        except (LayoutError, ValueError) as exc:
            self.status.set('Změny nebyly použity: '+str(exc))
            return False
        # One publication, no update()/event processing between output renders.
        self.session = session
        self.playback.reset()
        self.preview_origin_id = None
        self.anchor_tracks.clear()
        if position:
            self.reset_anchor()
        for window in self.projections.values():
            window.render()
        self.view_version.set('live')
        self.plan = None
        self.rebuild()
        self.status.set('Změny použity do obou výstupů; pokračování zachováno, případně vybráno poslední zbývající.')
        return True

    @staticmethod
    def button(parent, label, command):
        button = tk.Button(parent, text=label, command=command, takefocus=True)
        button.pack(side='left', padx=2)
        return button

    def section(self):
        return next((s for s in self.document.sections if s.id == self.selected_id), None)

    def cursor_style(self):
        cursor = self.text.index('insert')
        if self.typing_override is not None and cursor == self.typing_position:
            return self.typing_override
        self.typing_override = None
        self.typing_position = None
        at = self.text.index(cursor+'-1c') if not cursor.endswith('.0') else cursor
        tags = self.text.tag_names(at)
        style = next((self.styles[t] for t in reversed(tags) if t in self.styles), None)
        if style is not None:
            return style
        section = self.section()
        if isinstance(section, TextSection):
            block = next((b for b in reversed(section.blocks) if 'block:'+b.id in self.text.mark_names()
                          and self.text.compare('block:'+b.id, '<=', cursor)), None)
            if block and block.runs and not any(r.text for r in block.runs):
                return block.runs[0].style
        return TextStyle()

    def sync_font_size(self, clear=False):
        if clear:
            self.typing_override = None
            self.typing_position = None
        if not isinstance(self.section(), TextSection):
            self.size_box.configure(state='disabled')
            self.family_box.configure(state='disabled')
            return
        self.size_box.configure(state='normal')
        self.family_box.configure(state='normal')
        selection = self.text.tag_ranges('sel')
        if selection:
            sizes = set()
            families = set()
            at, end = map(str, selection)
            while self.text.compare(at, '<', end):
                tags = self.text.tag_names(at)
                style = next((self.styles[t] for t in reversed(tags) if t in self.styles), TextStyle())
                if self.text.get(at, at+'+1c') != '\n':
                    sizes.add(style.size)
                    families.add(self.metrics.available_families.get(style.family.casefold(), style.family) if style.family else self.metrics.fallback_family)
                at = self.text.index(at+'+1c')
            self.font_size.set(str(next(iter(sizes))) if len(sizes) == 1 else '')
            self.font_family.set(next(iter(families)) if len(families) == 1 else '')
        else:
            style = self.cursor_style()
            self.font_size.set(str(style.size))
            self.font_family.set(self.metrics.available_families.get(style.family.casefold(), style.family) if style.family else self.metrics.fallback_family)

    def capture_size_target(self, event=None):
        self.finish_editing()
        self.size_target = (self.selected_id, tuple(map(str, self.text.tag_ranges('sel'))), self.text.index('insert'))

    def cancel_font_size(self, event=None):
        self.sync_font_size()
        self.text.focus_set()
        return 'break'

    def apply_font_size(self, event=None):
        try:
            value = int(self.font_size.get())
            if not 8 <= value <= 144:
                raise ValueError()
        except ValueError:
            self.status.set('Velikost písma musí být celé číslo od 8 do 144 px.')
            return 'break'
        return self.apply_text_style('size', value)

    def apply_font_family(self, event=None):
        value = self.metrics.available_families.get(self.font_family.get().strip().casefold())
        if value is None:
            self.status.set('Vyberte nainstalovaný font ze seznamu.')
            return 'break'
        return self.apply_text_style('family', value)

    def apply_text_style(self, field, value):
        if not isinstance(self.section(), TextSection):
            return 'break'
        if self.size_target and self.size_target[0] == self.selected_id:
            _, selection, cursor = self.size_target
            self.text.mark_set('insert', cursor)
            self.text.tag_remove('sel', '1.0', 'end')
            if selection:
                self.text.tag_add('sel', *selection)
        if self.text.tag_ranges('sel'):
            self.typing_override = None
            self.format_selection(field, value)
        else:
            self.typing_override = replace(self.cursor_style(), **{field: value})
            self.typing_position = self.text.index('insert')
        self.size_target = None
        self.text.focus_set()
        self.sync_font_size()
        return 'break'

    def style_tag(self, style):
        for tag, value in self.styles.items():
            if value == style:
                return tag
        tag = f'style{len(self.styles)}'
        self.styles[tag] = style
        self.text.tag_configure(tag, font=self.metrics.font(style, max(4, round(style.size*16/36))), foreground=style.color)
        return tag

    def load_editor(self):
        self.loading = True
        self.typing_override = None
        self.typing_position = None
        section = self.section()
        self.title_entry.configure(state='normal')
        self.text.configure(state='normal')
        self.title.set(' • '.join(part for part in (section.title, section.reference) if part) if section else '')
        for mark in self.text.mark_names():
            if mark.startswith('block:'):
                self.text.mark_unset(mark)
        self.text.delete('1.0', 'end')
        if isinstance(section, TextSection):
            for i, block in enumerate(section.blocks):
                if i:
                    self.text.insert('end', '\n', ())
                start = self.text.index('end-1c')
                for run in block.runs:
                    run_start = self.text.index('end-1c')
                    self.text.insert('end', run.text, (self.style_tag(run.style), 'run:'+run.id))
                    for offset, char in enumerate(run.text):
                        if char == '\n':
                            at = run_start+f'+{offset}c'
                            self.text.tag_add('soft', at, at+'+1c')
                self.text.mark_set('block:'+block.id, start)
                self.text.mark_gravity('block:'+block.id, 'left')
                if block.kind in (BlockKind.BULLET, BlockKind.NUMBERED):
                    self.text.tag_add(block.kind.value, start, 'end-1c')
                    self.text.tag_add(f'listlevel:{block.level}', start, 'end-1c')
            self.break_before.set(section.break_before)
        else:
            if isinstance(section, ImageSection):
                self.text.insert('1.0', 'Obrázkový úsek — proporce jsou zachovány.\nMédium je vloženo do prezentace.')
                self.break_before.set(section.break_before)
            else:
                self.title_entry.configure(state='disabled')
            self.text.configure(state='disabled')
        self.text.edit_modified(False)
        self.loading = False
        self.sync_font_size()

        self.update_preview_highlight()

    def update_preview_highlight(self, scroll=False):
        """Paint exact preview source spans, independently of the user's selection."""
        self.text.tag_remove('preview_content', '1.0', 'end')
        if not self.plan or not self.plan.slides or (getattr(self, 'layout_failed', False) and not self.viewing_live()):
            return
        slide = self.plan.slides[self.current]
        section = self.section()
        if slide.black or not isinstance(section, TextSection) or slide.section_id != section.id:
            return
        source = next((s for s in self.plan.source.sections if s.id == section.id), None)
        # A live snapshot can differ from the editable draft. Never pretend that
        # changed draft text is the old projected content.
        if not isinstance(source, TextSection) or source.blocks != section.blocks:
            return
        if self.text.get('1.0', 'end-1c') != '\n'.join(''.join(r.text for r in b.runs) for b in section.blocks):
            return
        starts = {}
        for block in section.blocks:
            mark = 'block:'+block.id
            if mark not in self.text.mark_names():
                return
            offset = 0
            for run in block.runs:
                starts[run.id] = (self.text.index(mark), offset)
                offset += len(run.text)
        for span in slide.ranges:
            mark, offset = starts[span.run_id]
            self.text.tag_add('preview_content', f'{mark}+{offset+span.start}c', f'{mark}+{offset+span.end}c')
        self.text.tag_raise('preview_content')
        self.text.tag_raise('sel')
        ranges = self.text.tag_ranges('preview_content')
        if scroll and ranges:
            self.text.yview(ranges[0])

    def read_blocks(self):
        # Marks retain source identities; tagged source newlines stay inside blocks.
        section = self.section()
        text = self.text.get('1.0', 'end-1c')
        old = section.blocks
        old_lines = [''.join(r.text for r in b.runs) for b in old]
        lines, starts = [''], ['1.0']
        for offset, char in enumerate(text):
            index = self.text.index(f'1.0+{offset}c')
            if char == '\n' and 'soft' not in self.text.tag_names(index):
                lines.append('')
                starts.append(self.text.index(index+'+1c'))
            else:
                lines[-1] += char
        mapping = {}
        for op, a, b, c, d in SequenceMatcher(None, old_lines, lines, autojunk=False).get_opcodes():
            if op == 'equal' or op == 'replace':
                mapping.update({c+i: old[a+i] for i in range(min(b-a, d-c))})
        used, used_blocks = set(), set()
        marked = {self.text.index('block:'+b.id): b for b in old if 'block:'+b.id in self.text.mark_names()}
        blocks = []
        for number, line in enumerate(lines):
            chunks = []
            for offset, char in enumerate(line):
                index = self.text.index(starts[number]+f'+{offset}c')
                tags = self.text.tag_names(index)
                style = next((self.styles[t] for t in reversed(tags) if t in self.styles), TextStyle())
                rid = next((t[4:] for t in tags if t.startswith('run:')), None)
                if chunks and chunks[-1][1:3] == (style, rid):
                    chunks[-1] = (chunks[-1][0]+char, style, rid, chunks[-1][3])
                else:
                    chunks.append((char, style, rid, index))
            runs = []
            previous = mapping.get(number) or marked.get(starts[number])
            if previous and any(n != number and b.id == previous.id for n, b in mapping.items()):
                previous = None
            if previous and previous.id in used_blocks:
                previous = None
            for value, style, rid, start in chunks:
                if not runs and not rid and previous and len(previous.runs) == 1 and not previous.runs[0].text:
                    rid = previous.runs[0].id
                rid = rid if rid and rid not in used else new_id()
                used.add(rid)
                run = TextRun(value, style, rid)
                runs.append(run)
                for tag in self.text.tag_names(start):
                    if tag.startswith('run:'):
                        self.text.tag_remove(tag, start, start+f'+{len(value)}c')
                self.text.tag_add('run:'+rid, start, start+f'+{len(value)}c')
            if not runs:
                rid = previous.runs[0].id if previous and previous.runs and previous.runs[0].id not in used else new_id()
                used.add(rid)
                empty_style = self.typing_override if self.typing_override is not None and self.typing_position == starts[number] else previous.runs[0].style if previous and previous.runs else TextStyle()
                runs = [] if previous and not previous.runs else [TextRun('', style=empty_style, id=rid)]
            tags = self.text.tag_names(starts[number])
            kind = BlockKind.NUMBERED if 'numbered' in tags else BlockKind.BULLET if 'bullet' in tags else BlockKind.PARAGRAPH
            if previous and not line:
                kind = previous.kind
            elif previous and previous.kind in (BlockKind.NUMBERED, BlockKind.BULLET) and kind == BlockKind.PARAGRAPH:
                kind = previous.kind
            bid = previous.id if previous else new_id()
            level = next((int(tag.split(':')[1]) for tag in tags if tag.startswith('listlevel:')),
                         previous.level if previous else 0) if kind != BlockKind.PARAGRAPH else 0
            used_blocks.add(bid)
            blocks.append(TextBlock(tuple(runs), kind, bid, level))
        for mark in self.text.mark_names():
            if mark.startswith('block:'):
                self.text.mark_unset(mark)
        for block, start in zip(blocks, starts):
            self.text.mark_set('block:'+block.id, start)
            self.text.mark_gravity('block:'+block.id, 'left')
        return tuple(blocks)

    def update_section(self, section, group=None):
        self.commit(replace(self.document, sections=tuple(section if s.id == section.id else s for s in self.document.sections)), group, reload=False)

    def text_changed(self, event=None):
        if self.loading or not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        if isinstance(self.section(), TextSection):
            self.update_section(replace(self.section(), blocks=self.read_blocks()), ('text', self.selected_id))

    def insert_newline(self, event=None):
        self.text_changed()
        next_style = self.cursor_style()
        section = self.section()
        at = str(self.text.tag_ranges('sel')[0]) if self.text.tag_ranges('sel') else self.text.index('insert')
        active = next((i for i in range(len(section.blocks)-1, -1, -1)
                       if self.text.compare('block:'+section.blocks[i].id, '<=', at)), 0) if isinstance(section, TextSection) else None
        numbered = active is not None and section.blocks[active].kind in (BlockKind.NUMBERED, BlockKind.BULLET)
        list_kind = section.blocks[active].kind if numbered else None
        level = section.blocks[active].level if numbered else 0
        if numbered and not self.text.tag_ranges('sel') and not ''.join(r.text for r in section.blocks[active].runs).strip():
            blocks = list(section.blocks)
            blocks[active] = replace(blocks[active], level=max(0, level-1), kind=list_kind if level else BlockKind.PARAGRAPH)
            self.update_section(replace(section, blocks=tuple(blocks)))
            self.load_editor()
            self.text.mark_set('insert', at)
            self.typing_override = next_style
            self.typing_position = at
            self.sync_font_size()
            return 'break'
        if numbered:
            self.end_group()
        if self.text.tag_ranges('sel'):
            self.text.delete('sel.first', 'sel.last')
        self.text.insert('insert', '\n', (self.style_tag(next_style),))
        self.typing_override = next_style
        self.typing_position = self.text.index('insert')
        if numbered:
            cursor = self.text.index('insert')
            self.text_changed()
            section = self.section()
            blocks = list(section.blocks)
            index = next(i for i, b in enumerate(blocks) if self.text.index('block:'+b.id) == cursor)
            blocks[index] = replace(blocks[index], kind=list_kind, level=level)
            self.update_section(replace(section, blocks=tuple(blocks)), ('text', self.selected_id))
            self.load_editor()
            self.text.mark_set('insert', cursor)
            self.typing_override = next_style
            self.typing_position = cursor
        self.sync_font_size()
        return 'break'

    def paste_text(self, event=None):
        try:
            value = self.root.clipboard_get().replace('\r\n', '\n').replace('\r', '\n')
        except tk.TclError:
            return 'break'
        self.text_changed()
        paste_style = self.cursor_style()
        tags = tuple(t for t in self.text.tag_names('insert') if t in self.styles or t in ('bullet', 'numbered') or t.startswith('listlevel:'))
        tags = tuple(t for t in tags if t not in self.styles) + (self.style_tag(paste_style),)
        section = self.section()
        at = str(self.text.tag_ranges('sel')[0]) if self.text.tag_ranges('sel') else self.text.index('insert')
        if isinstance(section, TextSection):
            active = next((b for b in reversed(section.blocks) if self.text.compare('block:'+b.id, '<=', at)), None)
            if active and active.kind in (BlockKind.NUMBERED, BlockKind.BULLET):
                tags = tuple(t for t in tags if t not in ('bullet', 'numbered') and not t.startswith('listlevel:'))
                tags += (active.kind.value, f'listlevel:{active.level}')
        if self.text.tag_ranges('sel'):
            self.text.delete('sel.first', 'sel.last')
        self.end_group()
        self.text.insert('insert', value, tags)
        self.typing_override = paste_style
        self.typing_position = self.text.index('insert')
        return 'break'

    def title_changed(self, *args):
        if not self.loading and self.section():
            self.update_section(replace(self.section(), title=self.title.get(), reference=''), ('title', self.selected_id))

    def end_group(self):
        self.history.group = None

    def commit(self, document, group=None, reload=True):
        if not self.history.apply(document, group):
            return
        self.update_anchor(document)
        self.document = document
        self.document_contexts[id(document)] = self.file_context
        if self.group_timer:
            self.root.after_cancel(self.group_timer)
        self.group_timer = self.root.after(700, self.end_group)
        self.refresh_sections()
        if reload:
            self.load_editor()
        if self.pending:
            self.root.after_cancel(self.pending)
        self.pending = self.root.after(180, self.rebuild)
        self.history_buttons()
        self.update_version_status()

        self.update_preview_highlight()

    def history_buttons(self):
        self.update_file_status()
        self.undo_button.configure(state='normal' if self.history.past else 'disabled')
        self.redo_button.configure(state='normal' if self.history.future else 'disabled')

    def refresh_sections(self):
        from .sections_window import section_label
        if self.selected_id not in {s.id for s in self.document.sections}:
            self.selected_id = self.document.sections[0].id if self.document.sections else None
        self.sections.delete(0, 'end')
        for i, section in enumerate(self.document.sections):
            label = section_label(section)
            self.sections.insert('end', f'{i+1}. {label}')
            if section.id == self.selected_id:
                self.sections.selection_set(i)
                self.sections.see(i)
        for field, var in self.aspects.items():
            var.set(getattr(self.document, field).aspect.value)
        self.black_start.set(self.document.black_start)
        self.black_end.set(self.document.black_end)
        if hasattr(self, 'projection_controls'):
            self.projection_controls.update_summary()
        overview = getattr(self, 'sections_window', None)
        if overview and overview.alive():
            overview.refresh()

    def show_sections_window(self):
        overview = getattr(self, 'sections_window', None)
        if overview and overview.alive():
            overview.window.deiconify()
            overview.window.lift()
        else:
            from .sections_window import SectionsWindow
            overview = self.sections_window = SectionsWindow(self)
        return overview

    def choose_source_section(self, sid):
        index = next((i for i, s in enumerate(self.document.sections) if s.id == sid), None)
        if index is not None:
            self.finish_editing()
            self.sections.selection_clear(0, 'end')
            self.sections.selection_set(index)
            self.sections.see(index)
            self.select_section()

    def reorder_source_section(self, sid, slot):
        self.finish_editing()
        sections = list(self.document.sections)
        index = next((i for i, s in enumerate(sections) if s.id == sid), None)
        if index is None:
            return
        destination = max(0, min(len(sections), slot)) - (slot > index)
        if destination == index:
            return
        sections.insert(destination, sections.pop(index))
        self.selected_id = sid
        self.end_group()
        self.commit(replace(self.document, sections=tuple(sections)))

    def select_section(self, event=None):
        selected = self.sections.curselection()
        if selected:
            sid = self.document.sections[selected[0]].id
            if sid != self.selected_id:
                self.end_group()
                self.selected_id = sid
                self.load_editor()
                overview = getattr(self, 'sections_window', None)
                if overview and overview.alive():
                    overview.refresh()
                if self.plan and not self.viewing_live():
                    index = next((i for i, s in enumerate(self.plan.slides) if s.section_id == sid and not s.black), None)
                    if index is not None:
                        self.jump(index)

    def new_document(self):
        self.finish_editing()
        had_changes = self.document != self.saved_document
        if not self.confirm_document_change():
            return
        if had_changes or messagebox.askyesno('Nová prezentace', 'Vytvořit prázdnou prezentaci? Současnou lze vrátit pomocí Zpět.', parent=self.root):
            document = self.default_document()
            self.remember_file()
            self.selected_id = document.sections[0].id
            self.preview_section = self.selected_id
            self.commit(document)
            self.file_path = None
            self.saved_document = document
            self.file_context = object()
            self.remember_file()
            self.update_file_status()
            self.title_entry.focus_set()

    def add_section(self, section=None):
        section = section or blank_document(self.default_content_style()).sections[0]
        sections = list(self.document.sections)
        index = next((i+1 for i, s in enumerate(sections) if s.id == self.selected_id), len(sections))
        sections.insert(index, section)
        self.selected_id = section.id
        self.preview_section = section.id
        self.commit(replace(self.document, sections=tuple(sections)))
        self.title_entry.focus_set()

    def move_section(self, delta):
        sections = list(self.document.sections)
        index = next((i for i, s in enumerate(sections) if s.id == self.selected_id), -1)
        if index >= 0 and 0 <= index+delta < len(sections):
            sections[index], sections[index+delta] = sections[index+delta], sections[index]
            self.commit(replace(self.document, sections=tuple(sections)))

    def copy_section(self):
        if isinstance(self.section(), (TextSection, ImageSection)):
            self.add_section(duplicate_section(self.section()))

    def merge_next_section(self):
        self.finish_editing()
        sections = list(self.document.sections)
        index = next((i for i, s in enumerate(sections) if s.id == self.selected_id), -1)
        if index < 0 or index+1 >= len(sections):
            self.status.set('Za vybraným úsekem není další úsek ke sloučení.')
            return
        first, second = sections[index:index+2]
        details = ('Zůstane název/odkaz prvního úseku. Texty se spojí jako odstavce a znovu automaticky rozdělí. '
                   'Obrázky dostanou automatickou mřížku pro sál i stream; volba prvního/všech pokračování zůstane. Operaci lze vrátit Zpět.')
        if second.break_before or first.break_after:
            details += '\nČerný předěl mezi úseky bude tímto ručním sloučením odstraněn.'
        if (first.title, first.reference) != (second.title, second.reference):
            details += f'\nDruhý název/odkaz „{second.title} {second.reference}“ se neponechá v hlavičce.'
        if not messagebox.askyesno('Sloučit dva úseky?', details, parent=self.root):
            return
        try:
            sections[index:index+2] = [merge_sections(first, second)]
            document = replace(self.document, sections=tuple(sections))
            paginate(document, self.metrics, self.typography)
            self.preview_section = first.id
            self.commit(document)
            self.rebuild()
            self.status.set('Dva úseky sloučeny a znovu rozděleny. Živá projekce se změní až po potvrzení.')
        except (ValueError, LayoutError) as exc:
            messagebox.showerror('Sloučení úseků', str(exc), parent=self.root)

    def delete_section(self):
        if self.section():
            sections = list(self.document.sections)
            index = next(i for i, s in enumerate(sections) if s.id == self.selected_id)
            sections.pop(index)
            self.selected_id = sections[min(index, len(sections)-1)].id if sections else None
            self.commit(replace(self.document, sections=tuple(sections)))

    def change_break(self):
        if self.section():
            self.update_section(replace(self.section(), break_before=self.break_before.get()))

    def thumbnail_clicked(self, index):
        self.jump(index, select=True)
        self.thumbnails[self.current].focus_set()

    def delete_black_slide(self, event):
        if self.viewing_live():
            return
        if event.widget not in self.thumbnails and event.widget is not self.preview:
            return
        self.rebuild()
        if not self.plan or self.plan.source != self.document or not self.plan.slides:
            return
        slide = self.plan.slides[self.current]
        if not slide.black:
            return
        # Remove all contributing flags when adjacent black requests collapsed.
        flags = {f'{self.document.id}:start': ('black_start', None),
                 f'{self.document.id}:end': ('black_end', None)}
        for section in self.document.sections:
            flags[f'{section.id}:before'] = ('break_before', section.id)
            flags[f'{section.id}:after'] = ('break_after', section.id)
        from .layout import with_black_breaks
        content = tuple(s for s in self.plan.slides if not s.black)
        document = self.document
        index = self.current
        while True:
            plan = with_black_breaks(document, content)
            if index >= len(plan.slides) or not plan.slides[index].black:
                break
            flag, sid = flags[plan.slides[index].id]
            if sid is None:
                document = replace(document, **{flag: False})
            else:
                document = replace(document, sections=tuple(replace(s, **{flag: False}) if s.id == sid else s for s in document.sections))
        self.commit(document)
        self.rebuild()
        if self.thumbnails:
            self.thumbnails[self.current].focus_set()
        return 'break'

    def change_aspect(self, field, value):
        self.commit(replace(self.document, **{field: replace(getattr(self.document, field), aspect=Aspect(value))}))
        self.rebuild()

    def undo(self):
        self.restore(self.history.undo())

    def redo(self):
        self.restore(self.history.redo())

    def restore(self, document):
        self.remember_file()
        self.file_context = self.document_contexts.get(id(document), object())
        self.file_path, self.saved_document = self.document_files.get(self.file_context, (None, None))
        cursor = self.text.index('insert')
        section_id = self.selected_id
        self.update_anchor(document)
        self.document = document
        self.refresh_sections()
        self.load_editor()
        if self.selected_id == section_id:
            self.text.mark_set('insert', cursor)
            self.text.see('insert')
        self.rebuild()
        self.history_buttons()

    def format_selection(self, field, value=None):
        if not self.text.tag_ranges('sel'):
            self.status.set('Pro formátování nejprve označte text v obsahu.')
            self.text.focus_set()
            return
        start, end = map(str, self.text.tag_ranges('sel'))
        tags = self.text.tag_names(start)
        first = next((self.styles[t] for t in reversed(tags) if t in self.styles), TextStyle())
        value = value if value is not None else not getattr(first, field)
        index = start
        while self.text.compare(index, '<', end):
            following = self.text.index(index+'+1c')
            tags = self.text.tag_names(index)
            style = next((self.styles[t] for t in reversed(tags) if t in self.styles), TextStyle())
            for tag in tags:
                if tag in self.styles:
                    self.text.tag_remove(tag, index, following)
            self.text.tag_add(self.style_tag(replace(style, **{field: value})), index, following)
            index = following
        self.end_group()
        self.update_section(replace(self.section(), blocks=self.read_blocks()))
        self.text.focus_set()

    def choose_color(self):
        color = colorchooser.askcolor(parent=self.root, title='Barva označeného textu')[1]
        if color:
            self.format_selection('color', color)

    def change_list_level(self, delta, event=None):
        if event is not None and event.state & (0x4 | 0x8 | 0x20000):
            return
        self.finish_editing()
        insertion_style = self.cursor_style()
        section = self.section()
        if not isinstance(section, TextSection):
            return
        selection = tuple(map(str, self.text.tag_ranges('sel')))
        cursor = self.text.index('insert')
        start, end = selection if selection else (cursor, cursor)
        if selection and end.endswith('.0') and self.text.compare(end, '>', start):
            end = self.text.index(end+'-1c')
        blocks = list(section.blocks)
        indices = [i for i, block in enumerate(blocks)
                   if self.text.compare('block:'+block.id, '<=', end)
                   and (i+1 == len(blocks) or self.text.compare('block:'+blocks[i+1].id, '>', start))]
        if not any(blocks[i].kind != BlockKind.PARAGRAPH for i in indices):
            return
        for i in indices:
            if blocks[i].kind != BlockKind.PARAGRAPH:
                blocks[i] = replace(blocks[i], level=max(0, min(2, blocks[i].level+delta)))
        if tuple(blocks) != section.blocks:
            self.update_section(replace(section, blocks=tuple(blocks)))
            self.load_editor()
            self.text.mark_set('insert', cursor)
            self.typing_override = insertion_style
            self.typing_position = cursor
            if selection:
                self.text.tag_add('sel', *selection)
            self.text.see('insert')
            self.sync_font_size()
        return 'break'

    def toggle_bullets(self, list_kind=BlockKind.BULLET):
        if not isinstance(self.section(), TextSection):
            return
        insertion_style = self.cursor_style()
        selection = self.text.tag_ranges('sel')
        start = self.text.index(str(selection[0])+' linestart' if selection else 'insert linestart')
        end = self.text.index(str(selection[1]) if selection else 'insert lineend')
        if selection and end.endswith('.0') and self.text.compare(end, '>', start):
            end = self.text.index(end+'-1c')
        blocks = list(self.section().blocks)
        indices = [i for i, block in enumerate(blocks) if
                   self.text.compare('block:'+block.id, '<=', end) and
                   (i+1 == len(blocks) or self.text.compare('block:'+blocks[i+1].id, '>', start))]
        if not indices:
            return
        kind = BlockKind.PARAGRAPH if all(blocks[i].kind == list_kind for i in indices) else list_kind
        for i in indices:
            blocks[i] = replace(blocks[i], kind=kind, level=0 if kind == BlockKind.PARAGRAPH else blocks[i].level)
        cursor = self.text.index('insert')
        self.update_section(replace(self.section(), blocks=tuple(blocks)))
        self.load_editor()
        self.text.mark_set('insert', cursor)
        self.typing_override = insertion_style
        self.typing_position = cursor
        self.sync_font_size()
        self.text.focus_set()

    def copy_slide(self):
        if self.viewing_live():
            return
        self.rebuild()
        if self.plan and self.plan.source == self.document and self.plan.slides:
            slide = self.plan.slides[self.current]
            section = next((s for s in self.document.sections if s.id == slide.section_id), None)
            if isinstance(section, (TextSection, ImageSection)) and not slide.black:
                self.selected_id = section.id
                self.add_section(duplicate_section(section, slide))

    def rebuild(self):
        if self.pending:
            self.root.after_cancel(self.pending)
            self.pending = None
        previous = self.plan.slides[self.current] if self.plan and self.plan.slides else None
        previous_plan = self.plan
        had_layout_error = getattr(self, 'layout_failed', False)
        try:
            self.draft_plan = paginate(self.document, self.metrics, self.typography)
            self.layout_failed = False
            plan = self.session.plan if self.viewing_live() else self.draft_plan
        except ValueError as exc:
            self.layout_failed = True
            self.status.set('Náhled není aktuální: '+str(exc))
            self.copy_slide_button.configure(state='disabled')
            self.update_version_status()
            if self.viewing_live():
                plan = self.session.plan
            else:
                self.update_preview_highlight()
                return
        self.update_version_status()
        if plan == self.plan:
            self.update_preview_highlight()
            if had_layout_error and not self.layout_failed:
                self.jump(self.current, preserve_anchor=True)
                self.status.set(self.version_status.get() if self.session else 'Rozpracovaná prezentace • náhled je aktuální')
            return
        self.plan = plan
        self.current = next((i for i, s in enumerate(plan.slides) if previous and s.id == previous.id), min(self.current, max(0, len(plan.slides)-1)))
        if self.viewing_live():
            self.current = next((i for i, s in enumerate(plan.slides) if s.id == self.session.current_slide_id), 0)
        elif self.session and previous is None:
            self.current = min(self.draft_current, max(0, len(plan.slides)-1))
        elif previous and not self.viewing_live() and previous_plan.source != plan.source:
            target = anchors.relocate(anchors.capture(previous_plan, previous), previous_plan.source, plan.source)
            selected = anchors.locate(plan, target)
            self.current = next((i for i, s in enumerate(plan.slides) if s.id == selected), self.current)
        if self.switch_slide_id:
            self.current = next((i for i, s in enumerate(plan.slides) if s.id == self.switch_slide_id), self.current)
            self.switch_slide_id = None
        if self.preview_section and not self.viewing_live():
            self.current = next((i for i, s in enumerate(plan.slides) if s.section_id == self.preview_section and not s.black), self.current)
            self.preview_section = None
        for widget in self.strip_inner.winfo_children():
            widget.destroy()
        self.projected_thumbnail_index = None
        self.thumbnails = []
        self.labels = []
        for i, slide in enumerate(plan.slides):
            frame = tk.Frame(self.strip_inner, width=self.thumbnail_width+12, height=max(SLIDE_STRIP_HEIGHT, self.strip.winfo_height()))
            frame.pack(side='left', padx=3)
            frame.pack_propagate(False)
            width, height, _, _ = geometry(plan.source.hall)
            canvas = tk.Canvas(frame, width=self.thumbnail_width, height=round(self.thumbnail_width*height/width), bg='black', highlightthickness=3, highlightbackground='#666666', highlightcolor='#666666')
            canvas.pack()
            draw(canvas, slide, 'hall', self.metrics, self.typography, scale=self.thumbnail_width/width)
            if slide.black:
                label = 'Černý konec' if slide.id.endswith(':end') else ('Černý začátek' if slide.section_id is None else 'Černý předěl')
            else:
                source = next(s for s in plan.source.sections if s.id == slide.section_id)
                label = ' • '.join(part for part in (source.title, source.reference) if part) or 'Bez názvu'
            self.labels.append(label)
            caption = tk.Label(frame, text=f'{i+1}. {label}', anchor='w', font=self.appearance.small)
            caption.pack(fill='x')
            for widget in (canvas, caption):
                widget.bind('<Button-1>', lambda e, index=i: self.thumbnail_clicked(index))
            self.thumbnails.append(canvas)
        self.status.set(self.version_status.get() if self.session else 'Rozpracovaná prezentace • spuštění projekce potvrdí aktuální dokument')
        self.resize_thumbnail_strip()
        self.jump(self.current, preserve_anchor=True)
        self.history_buttons()

    def jump(self, index, select=False, preserve_anchor=False):
        if not self.plan or not self.plan.slides:
            self.preview.delete('all')
            self.location.set('Žádné snímky • přidejte úsek')
            self.copy_slide_button.configure(state='disabled')
            self.update_preview_highlight()
            return
        previous = self.current
        self.current = max(0, min(index, len(self.plan.slides)-1))
        if not preserve_anchor:
            self.preview_origin_id = None
        if self.viewing_live() and not preserve_anchor:
            moved = self.session.current_slide_id != self.session.plan.slides[self.current].id
            self.session = replace(self.session, current_slide_id=self.session.plan.slides[self.current].id)
            self.playback.reset()
            if moved:
                self.reset_anchor()
            for window in self.projections.values():
                window.render()
        elif not self.viewing_live():
            self.draft_current = self.current
        if previous < len(self.thumbnails):
            self.thumbnails[previous].configure(highlightbackground='#666666', highlightcolor='#666666')
        if self.projected_thumbnail_index is not None and self.projected_thumbnail_index < len(self.thumbnails):
            self.thumbnails[self.projected_thumbnail_index].configure(highlightbackground='#666666', highlightcolor='#666666')
        self.thumbnails[self.current].configure(highlightbackground='#00bfff', highlightcolor='#00bfff')
        self.projected_thumbnail_index = None
        if self.viewing_live():
            projected = next((i for i, s in enumerate(self.plan.slides) if s.id == self.session.current_slide_id), None)
            if projected is not None and projected != self.current:
                self.thumbnails[projected].configure(highlightbackground='#36b36b', highlightcolor='#36b36b')
                self.projected_thumbnail_index = projected
        slide = self.plan.slides[self.current]
        if (select or not preserve_anchor) and slide.section_id in {s.id for s in self.document.sections} and self.selected_id != slide.section_id:
            self.selected_id = slide.section_id
            self.end_group()
            self.refresh_sections()
            self.load_editor()
        self.copy_slide_button.configure(state='disabled' if self.viewing_live() or slide.black or self.plan.source != self.document else 'normal')
        self.location.set(f'{self.current+1}/{len(self.plan.slides)}')
        stride = self.thumbnail_width+18
        total = len(self.thumbnails)*stride
        visible = max(1, self.strip.winfo_width())
        left, x = self.strip.canvasx(0), self.current*stride
        if x < left or x+stride > left+visible:
            self.strip.xview_moveto(max(0, min(x, total-visible))/max(1, total))
        self.render_preview()
        self.update_version_status()
        self.update_preview_highlight(scroll=not preserve_anchor)

    def render_preview(self):
        if not self.plan or not self.plan.slides:
            return
        output = self.output.get()
        layout = getattr(self.plan.slides[self.current], output)
        self.layout_warning.set('\n'.join(layout.warnings) if layout else '')
        if self.layout_warning.get():
            self.layout_warning_label.pack(fill='x', before=self.preview)
        else:
            self.layout_warning_label.pack_forget()
        width, height, _, _ = geometry(getattr(self.plan.source, output))
        scale = min(max(1, self.preview.winfo_width())/width, max(1, self.preview.winfo_height())/height)
        draw(self.preview, self.plan.slides[self.current], output, self.metrics, self.typography, scale=scale, resize_canvas=False)
        self.preview.configure(bg='#303030')
        x = (self.preview.winfo_width()-width*scale)/2
        y = (self.preview.winfo_height()-height*scale)/2
        self.preview_geometry = (scale, (x, y))
        self.preview.move('all', x, y)
        background = self.preview.create_rectangle(x, y, x+width*scale, y+height*scale, fill='black', outline='#777777')
        self.preview.tag_lower(background)
        self.preview_image_edit.painted()

    def close(self):
        self.finish_editing()
        if self.document != self.saved_document:
            answer = messagebox.askyesnocancel('Zavřít', 'Uložit rozpracovanou prezentaci před zavřením?', parent=self.root)
            if answer is None or (answer and not self.save_document()):
                return
        try:
            save_settings(replace(self.settings, geometry=self.root.geometry()))
        except OSError as exc:
            messagebox.showwarning('Nastavení', f'Nastavení se nepodařilo uložit: {exc}', parent=self.root)
        self.stop_projection()
        try:
            self.recovery.clean()
        except OSError as exc:
            messagebox.showwarning('Obnova', 'Recovery soubor nelze odstranit: '+str(exc), parent=self.root)
        self.root.destroy()

    def destroyed(self, event):
        if event.widget is self.root:
            self.playback.stop()
            self.recovery.release()
            self.root.tk.deletecommand(self.text._w)
            for job in (self.pending, self.group_timer, self.monitor_job, self.autosave_job, self.resize_job):
                if job:
                    self.root.after_cancel(job)
            self.pending = self.group_timer = None
            self.monitor_job = None
            self.resize_job = None
            self.projections.clear()
            self.session = None
