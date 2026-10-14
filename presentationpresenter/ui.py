"""PP3 draft editor. Preview and thumbnails share the measured slide plan."""
import tkinter as tk
from tkinter import messagebox, colorchooser, filedialog
from dataclasses import replace
from difflib import SequenceMatcher
from .domain import *
from .settings import load_settings, save_settings
from .layout import paginate, Typography, LayoutError, geometry
from .rendering import TkMetrics, draw
from .editor import History, duplicate_section, blank_document, editable_section
from .session import ProjectionSession
from .projection import monitors, ProjectionWindow
from .projection_controls import ProjectionControls
from . import anchors
from . import storage, media
from .recovery import Recovery
from .settings import settings_path
from pathlib import Path
from .paths import presentation_directory


class MainWindow:
    def __init__(self, root, settings=None, recovery_dir=None):
        self.root, self.settings = root, settings or load_settings()
        self.document = blank_document()
        self.history = History(self.document)
        self.saved_document = self.document
        self.file_path = None
        self.autosave_job = None
        self.recovery = Recovery(recovery_dir or settings_path().parent / 'recovery')
        self.image_editor = None
        self.bible_window = None
        self.metrics = TkMetrics(root, self.settings.font_family)
        self.typography = Typography()
        self.selected_id = self.document.sections[0].id
        self.current, self.plan = 1, None
        self.preview_section = None
        self.pending = self.group_timer = None
        self.loading = False
        self.styles, self.thumbnails = {}, []
        self.session = None
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
        self.monitor_job = None
        root.title('PresentationPresenter — PP7')
        root.geometry(self.settings.geometry)
        root.minsize(950, 800)
        header = tk.Frame(root)
        header.pack(fill='x', padx=8, pady=6)
        toolbar = tk.Frame(header)
        toolbar.pack(side='left', anchor='n')
        self.button(toolbar, 'Nová prezentace', self.new_document)
        filebar = tk.Frame(root)
        filebar.pack(fill='x', padx=8)
        for label, command in (('Otevřít', self.open_document), ('Uložit', self.save_document), ('Uložit jako', lambda: self.save_document(True)), ('Import JSON', self.import_document), ('+ Obrázek', self.choose_image)):
            self.button(filebar, label, command)
        self.button(filebar, 'Bible', self.open_bible)
        for sequence, command in (('<Control-s>', self.save_document), ('<Control-o>', self.open_document)):
            root.bind(sequence, lambda e, c=command: (c(), 'break')[1])
        self.undo_button = self.button(toolbar, 'Zpět', self.undo)
        self.redo_button = self.button(toolbar, 'Znovu', self.redo)
        self.apply_button = self.button(toolbar, 'Použít do projekce', self.apply_live)
        self.aspects = {}
        for label, field in (('Sál', 'hall'), ('Stream', 'stream')):
            var = tk.StringVar(value=getattr(self.document, field).aspect.value)
            self.aspects[field] = var
        self.black_start = tk.BooleanVar(value=True)
        self.black_end = tk.BooleanVar(value=True)
        tk.Checkbutton(toolbar, text='Černý konec', variable=self.black_end, command=lambda: self.commit(replace(self.document, black_end=self.black_end.get()))).pack(side='left')
        self.monitor_choices = {f: tk.StringVar() for f in ('hall', 'stream')}
        self.projection_controls = ProjectionControls(self, header)
        self.refresh_monitors()
        body = tk.PanedWindow(root, orient='horizontal', sashwidth=7)
        body.pack(fill='both', expand=True, padx=8)
        sources = tk.Frame(body)
        tk.Label(sources, text='Zdrojové úseky').pack()
        self.sections = tk.Listbox(sources, exportselection=False)
        self.sections.pack(fill='both', expand=True)
        self.sections.bind('<<ListboxSelect>>', self.select_section)
        self.source_buttons = []
        for label, command in reversed((('+ Úsek', self.add_section), ('↑ Nahoru', lambda: self.move_section(-1)), ('↓ Dolů', lambda: self.move_section(1)), ('Duplikovat úsek', self.copy_section), ('Smazat úsek', self.delete_section))):
            button = tk.Button(sources, text=label, command=command)
            button.pack(side='bottom', fill='x', pady=2)
            self.source_buttons.append(button)
        self.sections.pack_forget()
        self.sections.pack(fill='both', expand=True)
        editor = tk.Frame(body)
        tk.Label(editor, text='Název / odkaz').pack(anchor='w')
        self.title = tk.StringVar()
        self.title_entry = tk.Entry(editor, textvariable=self.title)
        self.title_entry.pack(fill='x', pady=(0, 8))
        self.title.trace_add('write', self.title_changed)
        tk.Label(editor, text='Obsah • Enter = odstavec').pack(anchor='w')
        formatting = tk.Frame(editor)
        formatting.pack(fill='x')
        for label, field in (('Tučné', 'bold'), ('Kurzíva', 'italic'), ('Podtržení', 'underline')):
            self.button(formatting, label, lambda f=field: self.format_selection(f))
        self.button(formatting, 'Barva', self.choose_color)
        tk.Button(editor, text='Obrázky / rozložení', command=self.edit_images, takefocus=False).pack(anchor='w')
        tk.Button(editor, text='• Odrážky / odstavce', command=self.toggle_bullets, takefocus=False).pack(anchor='w')
        text_frame = tk.Frame(editor)
        text_frame.pack(fill='both', expand=True)
        self.text = tk.Text(text_frame, wrap='word', undo=False, exportselection=False, bg='#282828', fg='white', insertbackground='white', font=(self.settings.font_family, 12), padx=8, pady=8)
        scrollbar = tk.Scrollbar(text_frame, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.text.pack(fill='both', expand=True)
        self.text.tag_configure('bullet', lmargin1=18, lmargin2=18, background='#353535')
        self.text.bind('<<Modified>>', self.text_changed)
        self.text_original = self.text._w + '_original'
        self.root.tk.call('rename', self.text._w, self.text_original)
        self.root.tk.createcommand(self.text._w, self.text_operation)
        self.text.bind('<Return>', self.insert_newline)
        self.text.bind('<<Paste>>', self.paste_text)
        for widget in (self.text, self.title_entry):
            widget.bind('<FocusOut>', lambda e: self.end_group())
        self.break_before = tk.BooleanVar(value=True)
        tk.Checkbutton(editor, text='Černý předěl před úsekem', variable=self.break_before, command=self.change_break).pack(side='bottom', anchor='w')
        text_frame.pack_forget()
        text_frame.pack(fill='both', expand=True)
        preview = tk.Frame(body)
        body.add(preview, width=500, minsize=300, stretch='always')
        body.add(editor, width=360, minsize=290, stretch='never')
        body.add(sources, width=185, minsize=150, stretch='never')
        output_bar = tk.Frame(preview)
        output_bar.pack(fill='x')
        self.output = tk.StringVar(value='hall')
        for label, value in (('Náhled sálu', 'hall'), ('Náhled streamu', 'stream')):
            tk.Radiobutton(output_bar, text=label, variable=self.output, value=value, command=self.render_preview).pack(side='left')
        version_bar = tk.Frame(preview)
        version_bar.pack(fill='x')
        self.view_version = tk.StringVar(value='live')
        for label, value in (('Živá verze', 'live'), ('Rozpracovaná verze', 'draft')):
            tk.Radiobutton(version_bar, text=label, variable=self.view_version, value=value, command=self.switch_version).pack(side='left')
        self.version_status = tk.StringVar()
        tk.Label(preview, textvariable=self.version_status, anchor='w', wraplength=400).pack(fill='x')
        self.layout_warning = tk.StringVar()
        self.layout_warning_label = tk.Label(preview, textvariable=self.layout_warning, fg='#b02020', anchor='w', wraplength=400)
        aspect_bar = tk.Frame(preview)
        aspect_bar.pack(fill='x')
        tk.Label(aspect_bar, text='Poměr návrhu:').pack(side='left')
        for label, field in (('Sál', 'hall'), ('Stream', 'stream')):
            tk.Label(aspect_bar, text=label).pack(side='left')
            tk.OptionMenu(aspect_bar, self.aspects[field], *(a.value for a in Aspect), command=lambda v, f=field: self.change_aspect(f, v)).pack(side='left')
        self.preview = tk.Canvas(preview, bg='black', highlightthickness=0)
        self.preview.pack(fill='both', expand=True)
        self.preview.bind('<Configure>', lambda e: self.render_preview())
        self.preview.bind('<Button-1>', lambda e: self.preview.focus_set())
        nav = tk.Frame(preview)
        nav.pack(side='bottom', fill='x')
        self.button(nav, '←', lambda: self.jump(self.current-1))
        self.button(nav, '→', lambda: self.jump(self.current+1))
        self.copy_slide_button = self.button(nav, 'Snímek → nový úsek', self.copy_slide)
        self.location = tk.StringVar()
        tk.Label(preview, textvariable=self.location, wraplength=280).pack(side='bottom', fill='x')
        self.preview.pack_forget()
        self.preview.pack(fill='both', expand=True)
        self.status = tk.StringVar()
        tk.Label(root, textvariable=self.status, anchor='w', fg='#802020').pack(side='bottom', fill='x', padx=8)
        strip_frame = tk.Frame(root)
        strip_frame.pack(side='bottom', fill='x', padx=8, pady=6)
        self.strip = tk.Canvas(strip_frame, height=145, highlightthickness=0)
        horizontal = tk.Scrollbar(strip_frame, orient='horizontal', command=self.strip.xview)
        self.strip.configure(xscrollcommand=horizontal.set)
        horizontal.pack(side='bottom', fill='x')
        self.strip.pack(fill='x')
        self.strip_inner = tk.Frame(self.strip)
        self.strip.create_window(0, 0, window=self.strip_inner, anchor='nw')
        self.strip_inner.bind('<Configure>', lambda e: self.strip.configure(scrollregion=self.strip.bbox('all')))
        # Allocate toolbar and bottom strip before giving the editor the remaining space.
        body.pack_forget()
        body.pack(fill='both', expand=True, padx=8)
        for sequence, command in (('<Control-z>', self.undo), ('<Control-y>', self.redo), ('<Control-Shift-Z>', self.redo)):
            root.bind(sequence, lambda e, c=command: (c(), 'break')[1])
        self.refresh_sections()
        self.load_editor()
        self.rebuild()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Delete>', self.delete_black_slide)
        root.bind('<KeyPress-b>', self.blackout_key)
        root.bind('<KeyPress-B>', self.blackout_key)
        root.bind('<Destroy>', self.destroyed, add='+')
        self.projection_controls.update_summary()
        self.projection_controls.choose()
        if self.projection_controls.load_error:
            self.status.set('Profily nelze načíst: '+self.projection_controls.load_error)
        if hasattr(root, 'drop_target_register'):
            root.drop_target_register('DND_Files')
            root.dnd_bind('<<Drop>>', self.drop_images)
        self.autosave_job = root.after(1000, self.offer_recovery)

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
        path = filedialog.askopenfilename(parent=self.root, filetypes=[('Obrázky', '*.png *.jpg *.jpeg *.gif *.bmp *.webp')])
        if path:
            self.insert_image(path)

    def insert_image(self, path):
        try:
            asset = media.from_path(path)
            section = editable_section(self.section())
            sections = list(self.document.sections)
            if section is None:
                section = blank_document().sections[0]
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

    def save_document(self, save_as=False):
        path = None if save_as else self.file_path
        if not path:
            directory = self.file_dialog_directory()
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
            self.status.set('Uloženo: '+str(path))
            return True
        except (OSError, ValueError) as exc:
            messagebox.showerror('Uložení', str(exc), parent=self.root)
            return False

    def file_dialog_directory(self):
        try:
            return presentation_directory()
        except OSError as exc:
            messagebox.showerror('Složka prezentací', 'Složku presentation nelze připravit: '+str(exc), parent=self.root)
            return None

    def open_document(self):
        directory = self.file_dialog_directory()
        if directory is None:
            return
        path = filedialog.askopenfilename(parent=self.root, initialdir=str(directory), filetypes=[('PresentationPresenter', '*.ppres')])
        if not path:
            return
        try:
            document = storage.load(path)
            paginate(document, self.metrics, self.typography)
            self.commit(document)
            self.file_path, self.saved_document = path, document
            self.rebuild()
            self.refresh_monitors()
            self.status.set('Otevřena rozpracovaná verze. Místní monitory znovu ověřte před projekcí.')
        except (OSError, ValueError) as exc:
            messagebox.showerror('Otevření', str(exc), parent=self.root)

    def import_document(self):
        directory = self.file_dialog_directory()
        if directory is None:
            return
        path = filedialog.askopenfilename(parent=self.root, initialdir=str(directory), filetypes=[('Původní prezentace', '*.json')])
        if not path:
            return
        try:
            document, warnings = storage.import_legacy(path)
            paginate(document, self.metrics, self.typography)
            self.commit(document)
            self.file_path = None
            self.rebuild()
            messagebox.showwarning('Import JSON', '\n'.join(warnings[:30]), parent=self.root)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Import JSON', str(exc), parent=self.root)

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
                self.commit(document)
                self.file_path = None
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
            if hasattr(self, 'status'):
                self.status.set(str(exc))
        self.monitor_job = self.root.after(1000, self.refresh_monitors)

    def start_projection(self, outputs):
        self.text_changed()
        self.refresh_monitors_now()
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
            self.session = replace(ProjectionSession.confirm(self.plan), current_slide_id=self.plan.slides[self.current].id)
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
        if event.widget.winfo_class() in ('Text', 'Entry', 'TEntry', 'Spinbox', 'TSpinbox', 'TCombobox'):
            return
        if self.session:
            self.toggle_blackout()
            return 'break'

    def toggle_blackout(self):
        if self.session:
            self.session = replace(self.session, blackout=not self.session.blackout)
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
        return self.root.tk.call(self.text_original, *args)

    def viewing_live(self):
        return self.session is not None and self.view_version.get() == 'live'

    def update_version_status(self):
        dirty = self.session and self.session.plan.source != self.document
        self.apply_button.configure(state='normal' if dirty else 'disabled')
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
                except LayoutError as exc:
                    self.view_version.set('live')
                    self.status.set('Rozpracovaný náhled není dostupný: '+str(exc))
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
            position = anchors.confirmed_position(self.session.plan, self.session.current_slide_id, plan, self.live_anchor)
            session = ProjectionSession(plan, position, self.session.blackout)
        except (LayoutError, ValueError) as exc:
            self.status.set('Změny nebyly použity: '+str(exc))
            return False
        # One publication, no update()/event processing between output renders.
        self.session = session
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
        button = tk.Button(parent, text=label, command=command, takefocus=False)
        button.pack(side='left', padx=2)
        return button

    def section(self):
        return next((s for s in self.document.sections if s.id == self.selected_id), None)

    def style_tag(self, style):
        for tag, value in self.styles.items():
            if value == style:
                return tag
        tag = f'style{len(self.styles)}'
        self.styles[tag] = style
        self.text.tag_configure(tag, font=self.metrics.font(style, 16), foreground=style.color)
        return tag

    def load_editor(self):
        self.loading = True
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
                if block.kind == BlockKind.BULLET:
                    self.text.tag_add('bullet', start, 'end-1c')
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
                runs = [] if previous and not previous.runs else [TextRun('', id=rid)]
            kind = BlockKind.BULLET if 'bullet' in self.text.tag_names(starts[number]) else BlockKind.PARAGRAPH
            if previous and not line:
                kind = previous.kind
            bid = previous.id if previous else new_id()
            used_blocks.add(bid)
            blocks.append(TextBlock(tuple(runs), kind, bid))
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
        if self.text.tag_ranges('sel'):
            self.text.delete('sel.first', 'sel.last')
        self.text.insert('insert', '\n', ())
        return 'break'

    def paste_text(self, event=None):
        try:
            value = self.root.clipboard_get().replace('\r\n', '\n').replace('\r', '\n')
        except tk.TclError:
            return 'break'
        tags = tuple(t for t in self.text.tag_names('insert') if t in self.styles or t == 'bullet')
        if self.text.tag_ranges('sel'):
            self.text.delete('sel.first', 'sel.last')
        self.end_group()
        self.text.insert('insert', value, tags)
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

    def history_buttons(self):
        self.undo_button.configure(state='normal' if self.history.past else 'disabled')
        self.redo_button.configure(state='normal' if self.history.future else 'disabled')

    def refresh_sections(self):
        if self.selected_id not in {s.id for s in self.document.sections}:
            self.selected_id = self.document.sections[0].id if self.document.sections else None
        self.sections.delete(0, 'end')
        for i, section in enumerate(self.document.sections):
            self.sections.insert('end', f'{i+1}. {section.title or "Bez názvu"}')
            if section.id == self.selected_id:
                self.sections.selection_set(i)
        for field, var in self.aspects.items():
            var.set(getattr(self.document, field).aspect.value)
        self.black_start.set(self.document.black_start)
        self.black_end.set(self.document.black_end)

    def select_section(self, event=None):
        selected = self.sections.curselection()
        if selected:
            sid = self.document.sections[selected[0]].id
            if sid != self.selected_id:
                self.end_group()
                self.selected_id = sid
                self.load_editor()
                if self.plan and not self.viewing_live():
                    index = next((i for i, s in enumerate(self.plan.slides) if s.section_id == sid and not s.black), None)
                    if index is not None:
                        self.jump(index)

    def new_document(self):
        if messagebox.askyesno('Nová prezentace', 'Vytvořit prázdnou prezentaci? Současnou lze vrátit pomocí Zpět.', parent=self.root):
            document = blank_document()
            self.selected_id = document.sections[0].id
            self.preview_section = self.selected_id
            self.commit(document)
            self.file_path = None
            self.title_entry.focus_set()

    def add_section(self, section=None):
        section = section or blank_document().sections[0]
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

    def toggle_bullets(self):
        if not self.section():
            return
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
        kind = BlockKind.PARAGRAPH if blocks[indices[0]].kind == BlockKind.BULLET else BlockKind.BULLET
        for i in indices:
            blocks[i] = replace(blocks[i], kind=kind)
        cursor = self.text.index('insert')
        self.update_section(replace(self.section(), blocks=tuple(blocks)))
        self.load_editor()
        self.text.mark_set('insert', cursor)
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
        try:
            self.draft_plan = paginate(self.document, self.metrics, self.typography)
            plan = self.session.plan if self.viewing_live() else self.draft_plan
        except LayoutError as exc:
            self.status.set('Náhled není aktuální: '+str(exc))
            self.copy_slide_button.configure(state='disabled')
            self.update_version_status()
            if self.viewing_live():
                plan = self.session.plan
            else:
                return
        self.update_version_status()
        if plan == self.plan:
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
        counts = {}
        for i, slide in enumerate(plan.slides):
            frame = tk.Frame(self.strip_inner, width=162, height=140)
            frame.pack(side='left', padx=3)
            frame.pack_propagate(False)
            width, height, _, _ = geometry(plan.source.hall)
            canvas = tk.Canvas(frame, width=150, height=round(150*height/width), bg='black', highlightthickness=3, highlightbackground='#666666', highlightcolor='#666666')
            canvas.pack()
            draw(canvas, slide, 'hall', self.metrics, self.typography, scale=150/width)
            if slide.black:
                label = 'Černý konec' if slide.id.endswith(':end') else ('Černý začátek' if slide.section_id is None else 'Černý předěl')
            else:
                counts[slide.section_id] = counts.get(slide.section_id, 0)+1
                number = counts[slide.section_id]
                source = next(s for s in plan.source.sections if s.id == slide.section_id)
                label = ('Úsek' if number == 1 else f'↳ Pokračování {number}')+': '+(source.title or 'Bez názvu')
            self.labels.append(label)
            caption = tk.Label(frame, text=f'{i+1}. {label}', width=22, anchor='w')
            caption.pack()
            for widget in (canvas, caption):
                widget.bind('<Button-1>', lambda e, index=i: self.thumbnail_clicked(index))
            self.thumbnails.append(canvas)
        self.status.set(self.version_status.get() if self.session else 'Rozpracovaná prezentace • spuštění projekce potvrdí aktuální dokument')
        self.jump(self.current, preserve_anchor=True)
        self.history_buttons()

    def jump(self, index, select=False, preserve_anchor=False):
        if not self.plan or not self.plan.slides:
            self.preview.delete('all')
            self.location.set('Žádné snímky • přidejte úsek')
            self.copy_slide_button.configure(state='disabled')
            return
        previous = self.current
        self.current = max(0, min(index, len(self.plan.slides)-1))
        if not preserve_anchor:
            self.preview_origin_id = None
        if self.viewing_live() and not preserve_anchor:
            moved = self.session.current_slide_id != self.session.plan.slides[self.current].id
            self.session = replace(self.session, current_slide_id=self.session.plan.slides[self.current].id)
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
        if select and slide.section_id in {s.id for s in self.document.sections} and self.selected_id != slide.section_id:
            self.selected_id = slide.section_id
            self.end_group()
            self.refresh_sections()
            self.load_editor()
        self.copy_slide_button.configure(state='disabled' if self.viewing_live() or slide.black or self.plan.source != self.document else 'normal')
        self.location.set(f'Snímek {self.current+1} / {len(self.plan.slides)} • '+self.labels[self.current])
        total = len(self.thumbnails)*168
        visible = max(1, self.strip.winfo_width())
        left, x = self.strip.canvasx(0), self.current*168
        if x < left or x+168 > left+visible:
            self.strip.xview_moveto(max(0, min(x, total-visible))/max(1, total))
        self.render_preview()
        self.update_version_status()

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
        draw(self.preview, self.plan.slides[self.current], output, self.metrics, self.typography, scale=scale)
        self.preview.configure(bg='#303030')
        x = (self.preview.winfo_width()-width*scale)/2
        y = (self.preview.winfo_height()-height*scale)/2
        self.preview.move('all', x, y)
        background = self.preview.create_rectangle(x, y, x+width*scale, y+height*scale, fill='black', outline='#777777')
        self.preview.tag_lower(background)

    def close(self):
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
            self.recovery.release()
            self.root.tk.deletecommand(self.text._w)
            for job in (self.pending, self.group_timer, self.monitor_job, self.autosave_job):
                if job:
                    self.root.after_cancel(job)
            self.pending = self.group_timer = None
            self.monitor_job = None
            self.projections.clear()
            self.session = None
