"""Draft-only mixed-content image editing with independent output previews."""
import tkinter as tk
from dataclasses import replace
from .domain import ImagePlacement
from .layout import paginate, LayoutError, geometry, Rect
from .composition import compose_pair, normalize, constrain, with_image_box
from .media import dimensions
from .rendering import draw
from .appearance import appearance, scrollbar
from .ribbon import wrap_row


class ImageEditor:
    def __init__(self, owner, section_id):
        self.owner, self.section_id = owner, section_id
        self.window = tk.Toplevel(owner.root)
        self.window.title('Obrázky a text — rozpracované rozložení')
        self.window.geometry('1120x780')
        self.window.minsize(900, 650)
        self.output = tk.StringVar(value='hall')
        self.selected_id = None
        self.page = 0
        self.drag = None
        self.document = None
        self.job = None
        self.scale = 1
        self.origin = (0, 0)
        top = tk.Frame(self.window)
        top.pack(fill='x', padx=8, pady=6)
        for label, value in (('Sál', 'hall'), ('Stream', 'stream')):
            tk.Radiobutton(top, text=label, variable=self.output, value=value, command=self.refresh).pack(side='left')
        self.linked = tk.BooleanVar()
        tk.Checkbutton(top, text='Propojit stream se sálem', variable=self.linked, command=self.change_link).pack(side='left', padx=12)
        tk.Button(top, text='Přepočítat stream ze sálu', command=self.recalculate).pack(side='left')
        tk.Button(top, text='Automatická mřížka', command=self.reset).pack(side='left', padx=6)
        help_label = tk.Label(self.window, text='Přesun: táhněte obrázek. Velikost: táhněte modrý roh. Text se přepočítá po uvolnění myši.\nRuční úprava streamu vypne propojení. Změny jsou pouze v návrhu; projekci potvrdíte v hlavním okně.', anchor='w', justify='left', wraplength=1050)
        help_label.pack(fill='x', padx=8)
        help_label.bind('<Configure>', lambda e: help_label.configure(wraplength=max(1, e.width)))
        sidebar = tk.Frame(self.window)
        sidebar.pack(side='left', fill='y', padx=8, pady=8)
        sidebar_canvas = tk.Canvas(sidebar, width=280, highlightthickness=0)
        sidebar_scroll = scrollbar(sidebar, command=sidebar_canvas.yview)
        sidebar_scroll.pack(side='right', fill='y')
        sidebar_canvas.pack(side='left', fill='both', expand=True)
        sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        controls = tk.Frame(sidebar_canvas)
        control_window = sidebar_canvas.create_window(0, 0, window=controls, anchor='nw')
        controls.bind('<Configure>', lambda e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox('all')))
        sidebar_canvas.bind('<Configure>', lambda e: sidebar_canvas.itemconfigure(control_window, width=e.width))
        tk.Label(controls, text='Obrázky v tomto úseku').pack(anchor='w')
        list_frame = tk.Frame(controls)
        list_frame.pack(fill='x')
        self.list = tk.Listbox(list_frame, width=24, height=4, exportselection=False)
        self.list.pack(side='left', fill='both', expand=True)
        list_scrollbar = scrollbar(list_frame, command=self.list.yview)
        list_scrollbar.pack(side='right', fill='y')
        self.list.configure(yscrollcommand=list_scrollbar.set)
        self.list.bind('<<ListboxSelect>>', self.select)
        for label, command in (('+ Obrázek', self.add), ('Odstranit obrázek', self.remove)):
            tk.Button(controls, text=label, command=command).pack(fill='x', pady=3)
        self.values = {}
        for label, field in (('X (% šířky)', 'x'), ('Y (% výšky)', 'y'), ('Šířka (%)', 'width')):
            tk.Label(controls, text=label).pack(anchor='w', pady=(8, 0))
            var = tk.StringVar()
            self.values[field] = var
            entry = tk.Entry(controls, textvariable=var)
            entry.pack(fill='x')
            entry.bind('<Return>', lambda e: self.apply_fields())
        tk.Button(controls, text='Použít rozměry', command=self.apply_fields).pack(fill='x', pady=8)
        self.repeat = tk.BooleanVar()
        tk.Checkbutton(controls, text='Na všech pokračováních', variable=self.repeat, command=self.change_repeat,
                       wraplength=240, justify='left').pack(anchor='w')
        tk.Label(controls, text='Vypnuto = jen první pokračování.', justify='left', wraplength=250).pack(anchor='w')
        history = tk.Frame(controls)
        history.pack(fill='x', pady=(12, 3))
        tk.Button(history, text='Zpět', command=self.undo).pack(side='left', fill='x', expand=True)
        tk.Button(history, text='Znovu', command=self.redo).pack(side='left', fill='x', expand=True)
        area = tk.Frame(self.window)
        area.pack(fill='both', expand=True, padx=8, pady=8)
        self.notice = tk.StringVar()
        notice_label = tk.Label(area, textvariable=self.notice, justify='left', wraplength=780, anchor='w')
        notice_label.pack(fill='x')
        nav = tk.Frame(area)
        nav.pack(side='bottom', fill='x')
        tk.Button(nav, text='← Pokračování', command=lambda: self.navigate(-1)).pack(side='left')
        self.caption = tk.StringVar()
        tk.Label(nav, textvariable=self.caption).pack(side='left', padx=12)
        tk.Button(nav, text='Pokračování →', command=lambda: self.navigate(1)).pack(side='left')
        self.canvas = tk.Canvas(area, bg='#303030', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda e: self.refresh())
        self.canvas.bind('<Button-1>', self.press)
        self.canvas.bind('<B1-Motion>', self.motion)
        self.canvas.bind('<ButtonRelease-1>', self.release)
        self.window.protocol('WM_DELETE_WINDOW', self.window.destroy)
        self.window.bind('<Destroy>', self.destroyed, add='+')
        theme = appearance(owner.root)
        theme.apply(self.window)
        wrap_row(top)
        notice_label.configure(fg=theme.error)
        self.refresh()
        self.job = self.window.after(250, self.poll)

    def section(self):
        return next((s for s in self.owner.document.sections if s.id == self.section_id), None)

    def item(self):
        section = self.section()
        return next((i for i in getattr(section, 'images', ()) if i.id == self.selected_id), None)

    def poll(self):
        self.job = None
        if self.owner.document is not self.document and not self.drag:
            self.refresh()
        self.job = self.window.after(250, self.poll)

    def commit(self, section):
        self.owner.commit(replace(self.owner.document, sections=tuple(section if s.id == section.id else s for s in self.owner.document.sections)))
        self.owner.rebuild()
        self.refresh()

    def refresh(self):
        if not self.window.winfo_exists():
            return
        self.document = self.owner.document
        section = self.section()
        self.list.delete(0, 'end')
        images = getattr(section, 'images', ())
        if self.selected_id not in {i.id for i in images}:
            self.selected_id = images[0].id if images else None
        assets = {a.id: a for a in self.document.media}
        for index, item in enumerate(images):
            size = dimensions(assets[item.media_id].locator)
            self.list.insert('end', f'{index+1}. Obrázek {size[0]} × {size[1]}')
            if item.id == self.selected_id:
                self.list.selection_set(index)
        self.linked.set(getattr(section, 'stream_linked', True))
        self.repeat.set(self.item().repeat if self.item() else True)
        self.canvas.delete('all')
        if section is None:
            self.notice.set('Úsek byl odstraněn. Lze jej vrátit pomocí Zpět.')
            return
        try:
            plan = paginate(self.document, self.owner.metrics, self.owner.typography)
            self.slides = [s for s in plan.slides if s.section_id == section.id and not s.black]
            self.page = min(self.page, max(0, len(self.slides)-1))
            if not self.slides:
                return
            slide = self.slides[self.page]
            output = self.output.get()
            self.layout = getattr(slide, output)
            w, h = self.layout.width, self.layout.height
            cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
            self.scale = min(cw/w, ch/h)
            self.origin = ((cw-w*self.scale)/2, (ch-h*self.scale)/2)
            draw(self.canvas, slide, output, self.owner.metrics, self.owner.typography, scale=self.scale, resize_canvas=False)
            self.canvas.move('all', *self.origin)
            ox, oy = self.origin
            background = self.canvas.create_rectangle(ox, oy, ox+w*self.scale, oy+h*self.scale, fill='black', outline='#777777')
            self.canvas.tag_lower(background)
            self.notice.set('\n'.join(self.layout.warnings))
            self.caption.set(f'{self.page+1} / {len(self.slides)}')
            # Numeric editing remains available for first-only images on later pages.
            first_layout = compose_pair(self.document, section)[0 if output == 'hall' else 1]
            placed = next((p for p in first_layout.images if p.item_id == self.selected_id), None)
            if placed:
                p = normalize(placed.box, getattr(self.document, output))
                for field, var in self.values.items():
                    var.set(f'{getattr(p, field)*100:.3f}')
            for placed in self.layout.images:
                if placed.item_id == self.selected_id:
                    self.outline(placed.box)
        except (LayoutError, ValueError) as exc:
            self.layout = None
            self.notice.set('Rozložení nemá místo pro obsah: '+str(exc)+'\nZmenšete obrázek nebo obnovte mřížku.')
            # Keep the image geometry editable even when the text cannot fit.
            output = self.output.get()
            w, h, _, _ = geometry(getattr(self.document, output))
            self.scale = min(max(1, self.canvas.winfo_width())/w, max(1, self.canvas.winfo_height())/h)
            self.origin = (0, 0)
            try:
                self.layout = compose_pair(self.document, section)[0 if output == 'hall' else 1]
                from .layout import Slide
                draw(self.canvas, Slide('edit', section.id, hall=self.layout, stream=self.layout), output,
                     self.owner.metrics, self.owner.typography, scale=self.scale, resize_canvas=False)
                for placed in self.layout.images:
                    if placed.item_id == self.selected_id:
                        p = normalize(placed.box, getattr(self.document, output))
                        for field, var in self.values.items():
                            var.set(f'{getattr(p, field)*100:.3f}')
                        self.outline(placed.box)
            except (LayoutError, ValueError):
                pass

    def outline(self, box):
        ox, oy = self.origin
        x, y = ox+box.x*self.scale, oy+box.y*self.scale
        right, bottom = x+box.width*self.scale, y+box.height*self.scale
        self.canvas.create_rectangle(x, y, right, bottom, outline='#00bfff', width=2, tags='selection')
        self.canvas.create_rectangle(right-7, bottom-7, right+7, bottom+7, fill='#00bfff', tags='selection')

    def select(self, event=None):
        selected = self.list.curselection()
        if selected and self.section():
            self.selected_id = self.section().images[selected[0]].id
            self.refresh()

    def add(self):
        if not self.section():
            return
        self.owner.selected_id = self.section_id
        self.owner.choose_image()
        images = self.section().images
        self.selected_id = images[-1].id if images else None
        self.refresh()

    def remove(self):
        section = self.section()
        if self.item():
            self.commit(replace(section, images=tuple(i for i in section.images if i.id != self.selected_id)))

    def detached(self, section):
        if not section.stream_linked:
            return section
        pair = compose_pair(self.owner.document, section)
        boxes = {p.item_id: normalize(p.box, self.owner.document.stream) for p in pair[1].images}
        return replace(section, stream_linked=False, images=tuple(replace(i, stream=boxes[i.id]) for i in section.images))

    def change_link(self):
        section = self.section()
        if section:
            self.commit(replace(section, stream_linked=True) if self.linked.get() else self.detached(section))

    def recalculate(self):
        section = self.section()
        if section:
            linked = replace(section, stream_linked=True)
            self.commit(linked if section.stream_linked else self.detached(linked))

    def reset(self):
        section = self.section()
        if section:
            output = self.output.get()
            if output == 'stream':
                section = self.detached(section)
            self.commit(replace(section, images=tuple(replace(i, **{output: None}) for i in section.images)))

    def change_repeat(self):
        item = self.item()
        if item:
            section = self.section()
            self.commit(replace(section, images=tuple(replace(i, repeat=self.repeat.get()) if i.id == item.id else i for i in section.images)))

    def set_box(self, box):
        item, section = self.item(), self.section()
        if not item:
            return
        output = self.output.get()
        config = getattr(self.owner.document, output)
        proposed = box
        box = constrain(box, config)
        section = with_image_box(self.owner.document, section, item.id, output, box)
        self.commit(section)
        if any(abs(getattr(box, field)-getattr(proposed, field)) > 1e-6 for field in ('x', 'y', 'width', 'height')):
            self.notice.set('Obrázek byl přizpůsoben hranicím plochy a limitu přesahu kamery.\n'+self.notice.get())

    def apply_fields(self):
        if not self.item():
            return
        try:
            p = ImagePlacement(*(float(self.values[field].get().replace(',', '.'))/100 for field in ('x', 'y', 'width')))
            asset = next(a for a in self.owner.document.media if a.id == self.item().media_id)
            iw, ih = dimensions(asset.locator)
            w, h, _, _ = geometry(getattr(self.owner.document, self.output.get()))
            self.set_box(Rect(p.x*w, p.y*h, p.width*w, p.width*w*ih/iw))
        except (ValueError, LayoutError) as exc:
            self.notice.set('Neplatné rozměry: '+str(exc))

    def press(self, event):
        if not getattr(self, 'layout', None):
            return
        x, y = (event.x-self.origin[0])/self.scale, (event.y-self.origin[1])/self.scale
        for placed in reversed(self.layout.images):
            b = placed.box
            if b.x-8/self.scale <= x <= b.x+b.width+8/self.scale and b.y-8/self.scale <= y <= b.y+b.height+8/self.scale:
                self.selected_id = placed.item_id
                resize = abs(x-b.x-b.width) <= 12/self.scale and abs(y-b.y-b.height) <= 12/self.scale
                self.refresh()
                self.drag = (event.x, event.y, b, resize)
                break

    def drag_box(self, event):
        x, y, box, resize = self.drag
        dx, dy = (event.x-x)/self.scale, (event.y-y)/self.scale
        if resize:
            width = max(4, box.width+dx)
            proposed = replace(box, width=width, height=width*box.height/box.width)
        else:
            proposed = replace(box, x=box.x+dx, y=box.y+dy)
        return constrain(proposed, getattr(self.owner.document, self.output.get()))

    def motion(self, event):
        if self.drag:
            self.canvas.delete('selection')
            self.outline(self.drag_box(event))

    def release(self, event):
        if self.drag:
            box = self.drag_box(event)
            self.drag = None
            self.set_box(box)

    def navigate(self, delta):
        self.page = max(0, self.page+delta)
        self.refresh()

    def undo(self):
        self.owner.undo()
        self.refresh()

    def redo(self):
        self.owner.redo()
        self.refresh()

    def destroyed(self, event):
        if event.widget is self.window:
            if self.job:
                self.window.after_cancel(self.job)
                self.job = None
            self.owner.image_editor = None
