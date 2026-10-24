"""Camera geometry drafts and an isolated monitor calibration slide."""
from dataclasses import replace
import tkinter as tk
from tkinter import ttk, messagebox
from .domain import CameraRegion, OutputConfig, Presentation, TextSection, TextBlock, TextRun
from .layout import geometry, paginate
from .rendering import draw
from .projection import ProjectionWindow, monitor_labels
from .settings import save_settings
from .ribbon import wrap_row
from .appearance import reserve_button_labels

FIELDS = (('x', 'Zleva'), ('y', 'Shora'), ('width', 'Šířka'), ('height', 'Výška'), ('gap', 'Odstup textu'))

def resize_anchor(position, size):
    at_start = abs(position) < .000001
    at_end = abs(position+size-1) < .000001
    return 'start' if at_start and not at_end else 'end' if at_end and not at_start else 'center'

def fit_camera(values, changed, previous=None, anchor=None):
    """Resize from an attached edge or the center; moves retain size."""
    v = {k: max(0, min(100, float(values[k]))) for k, _ in FIELDS}
    v['width'], v['height'] = max(1, v['width']), max(1, v['height'])
    v['x'], v['y'] = min(99, v['x']), min(99, v['y'])
    for position, size in (('x', 'width'), ('y', 'height')):
        if changed == size:
            if previous is not None:
                old_position, old_size = getattr(previous, position)*100, getattr(previous, size)*100
                mode = anchor or resize_anchor(old_position/100, old_size/100)
                pivot = old_position if mode == 'start' else old_position+old_size if mode == 'end' else old_position+old_size/2
                maximum = 100-pivot if mode == 'start' else pivot if mode == 'end' else 2*min(pivot, 100-pivot)
                v[size] = min(v[size], maximum)
                v[position] = pivot if mode == 'start' else pivot-v[size] if mode == 'end' else pivot-v[size]/2
            else:
                v[size] = min(v[size], 100-v[position])
        else:
            v[position] = min(v[position], 100-v[size])
    return CameraRegion(**{key: round(value/100, 6) for key, value in v.items()})

class CalibrationProjection(ProjectionWindow):
    def render(self):
        self.owner.paint(self.canvas)

class CameraSettingsWindow:
    def __init__(self, owner):
        self.owner, self.root = owner, owner.root
        self.test = None
        self.redraw_job = self.monitor_job = None
        self.adjusting = False
        self.config = owner.document.stream
        self.camera = self.config.camera or owner.settings.default_camera()
        self.resize_anchors = {'width': resize_anchor(self.camera.x, self.camera.width),
                               'height': resize_anchor(self.camera.y, self.camera.height)}
        self.sample = None
        self.projection_controls = self  # Isolated ProjectionWindow key adapter.
        self.window = tk.Toplevel(owner.root)
        self.window.title('Prostor pro kameru — stream')
        self.window.geometry('900x760')
        self.window.minsize(720, 630)
        self.window.transient(owner.root)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.bind('<Escape>', lambda e: self.close())
        self.window.bind('<Destroy>', self.destroyed, add='+')
        controls = tk.Frame(self.window)
        controls.pack(fill='x', padx=12, pady=8)
        controls.columnconfigure(1, weight=1)
        self.values = {}
        for row, (field, label) in enumerate(FIELDS):
            tk.Label(controls, text=label+' (%)', anchor='w').grid(row=row, column=0, sticky='w', padx=(0, 10))
            var = tk.DoubleVar(value=getattr(self.camera, field)*100)
            self.values[field] = var
            scale = tk.Scale(controls, variable=var, from_=1 if field in ('width', 'height') else 0,
                             to=100, resolution=.25 if field in ('x', 'y') else .5, orient='horizontal', showvalue=True,
                             command=lambda value, key=field: self.changed(key), highlightthickness=0)
            scale.grid(row=row, column=1, sticky='ew')
        tk.Button(controls, text='Načíst výchozí', command=self.load_default).grid(row=0, column=2, padx=10)
        tk.Label(controls, text='Stream '+self.config.aspect.value).grid(row=1, column=2, padx=10)
        footer = tk.Frame(self.window)
        footer.pack(side='bottom', fill='x', padx=12, pady=10)
        self.status = tk.StringVar(value='Posuvníky mění jen ukázku. Okraj kamery je růžový, bezpečný odstup žlutý.')
        self.status_label = tk.Label(footer, textvariable=self.status, wraplength=820, justify='left', anchor='w')
        self.status_label.pack(fill='x', pady=6)
        buttons = tk.Frame(footer)
        buttons.pack(fill='x')
        for text, action in (('Použít pro prezentaci', lambda: self.apply(False)),
                             ('Použít a uložit výchozí', lambda: self.apply(True)), ('Zavřít', self.close)):
            tk.Button(buttons, text=text, command=action).pack(side='left', padx=(0, 8))
        output = tk.Frame(self.window)
        output.pack(side='bottom', fill='x', padx=12)
        tk.Label(output, text='Monitor ukázky:').pack(side='left')
        self.monitor_ids = {}
        self.monitor_choice = tk.StringVar()
        self.monitor_box = ttk.Combobox(output, textvariable=self.monitor_choice, state='readonly', width=28)
        self.monitor_box.pack(side='left', fill='x', expand=True, padx=8)
        self.fullscreen = tk.BooleanVar(value=len(owner.monitor_inventory) > 1)
        tk.Checkbutton(output, text='Celá obrazovka', variable=self.fullscreen).pack(side='left')
        self.test_button = tk.Button(output, text='Promítnout ukázku', command=self.toggle_test)
        self.test_button.pack(side='left', padx=8)
        self.canvas = tk.Canvas(self.window, bg='#303030', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, padx=12, pady=8)
        self.canvas.bind('<Configure>', lambda e: self.paint(self.canvas))
        owner.appearance.apply(self.window)
        reserve_button_labels(self.test_button, 'Promítnout ukázku', 'Ukončit ukázku')
        wrap_row(buttons)
        wrap_row(output)
        self.window.bind('<Configure>', lambda e: self.status_label.configure(wraplength=max(300, e.width-32)) if e.widget is self.window else None, add='+')
        # Scale is not part of the shared theme defaults.
        for widget in controls.winfo_children():
            if isinstance(widget, tk.Scale):
                widget.configure(bg=owner.appearance.background, fg=owner.appearance.foreground,
                                 troughcolor=owner.appearance.panel, activebackground=owner.appearance.hover,
                                 font=owner.appearance.small)
        self.refresh_sample()
        self.refresh_monitors()
        self.window.grab_set()

    def changed(self, field):
        if self.adjusting:
            return
        values = {k: v.get() for k, v in self.values.items()}
        if all(abs(value-getattr(self.camera, key)*100) < .00001 for key, value in values.items()):
            return  # Ignore Scale callbacks caused by syncing another slider.
        camera = fit_camera(values, field, self.camera, self.resize_anchors.get(field))
        if field == 'x' and camera.x != self.camera.x:
            self.resize_anchors['width'] = resize_anchor(camera.x, camera.width)
        elif field == 'y' and camera.y != self.camera.y:
            self.resize_anchors['height'] = resize_anchor(camera.y, camera.height)
        self.adjusting = True
        for key, var in self.values.items():
            value = getattr(camera, key)*100
            if abs(var.get()-value) > .00001:
                var.set(value)
        self.adjusting = False
        self.camera = camera
        if self.redraw_job:
            self.window.after_cancel(self.redraw_job)
        self.redraw_job = self.window.after(35, self.redraw)

    def load_default(self):
        self.adjusting = True
        self.camera = self.owner.settings.default_camera()
        self.resize_anchors = {'width': resize_anchor(self.camera.x, self.camera.width),
                               'height': resize_anchor(self.camera.y, self.camera.height)}
        for field, var in self.values.items():
            var.set(getattr(self.camera, field)*100)
        self.adjusting = False
        self.redraw()

    def refresh_sample(self):
        config = replace(self.config, camera=self.camera)
        text = 'Ukázkový text streamu. Text se přizpůsobuje prostoru kolem kamery. '
        document = Presentation(sections=(TextSection('Ukázka prostoru pro kameru',
            tuple(TextBlock((TextRun(text*3, self.owner.default_content_style()),)) for _ in range(3)),
            break_before=False, break_after=False),), stream=config, hall=OutputConfig(config.aspect), black_start=False)
        try:
            self.sample = paginate(document, self.owner.metrics, self.owner.typography).slides[0]
        except ValueError:
            self.sample = None  # Geometry stays adjustable even with no room for text.

    def redraw(self):
        if self.redraw_job:
            self.window.after_cancel(self.redraw_job)
        self.redraw_job = None
        self.refresh_sample()
        self.paint(self.canvas)
        if self.test:
            self.test.render()

    def paint(self, canvas):
        config = replace(self.config, camera=self.camera)
        width, height, camera, exclusion = geometry(config)
        cw, ch = max(1, canvas.winfo_width()), max(1, canvas.winfo_height())
        scale = min(cw/width, ch/height)
        x, y = (cw-width*scale)/2, (ch-height*scale)/2
        canvas.delete('all')
        if self.sample:
            draw(canvas, self.sample, 'stream', self.owner.metrics, self.owner.typography,
                 show_camera=False, scale=scale, resize_canvas=False)
            canvas.move('all', x, y)
        background = canvas.create_rectangle(x, y, x+width*scale, y+height*scale, fill='black', outline='#38dfff', width=2, tags='slide_border')
        canvas.tag_lower(background)
        def rectangle(box, **options):
            return canvas.create_rectangle(x+box.x*scale, y+box.y*scale,
                                           x+(box.x+box.width)*scale, y+(box.y+box.height)*scale, **options)
        if exclusion:
            # Same expanded bounds as the actual paginator, clipped to the slide.
            from .layout import Rect
            clipped = Rect(max(0, exclusion.x), max(0, exclusion.y),
                           min(width, exclusion.x+exclusion.width)-max(0, exclusion.x),
                           min(height, exclusion.y+exclusion.height)-max(0, exclusion.y))
            rectangle(clipped, outline='#ffe266', dash=(6, 4), width=2, tags='camera_gap')
        rectangle(camera, fill='#242424', outline='#ff55bb', width=4, tags='camera_border')
        if camera.width*scale >= 80 and camera.height*scale >= 28:
            canvas.create_text(x+(camera.x+camera.width/2)*scale, y+(camera.y+camera.height/2)*scale,
                               text='KAMERA', fill='#ffb5e2', font=self.owner.metrics.font(self.owner.default_content_style(), max(8, round(28*scale))),
                               width=max(1, camera.width*scale-8), tags='camera_label')

    def refresh_monitors(self):
        if self.monitor_job:
            self.window.after_cancel(self.monitor_job)
        self.monitor_job = None
        inventory = self.owner.monitor_inventory
        if self.test and (self.owner.monitor_error or self.test.monitor not in inventory):
            self.stop_test()
            self.status.set('Monitor byl odpojen nebo změnil geometrii. Ukázka zastavena.')
        previous = self.monitor_ids.get(self.monitor_choice.get())
        labels = monitor_labels(inventory)
        self.monitor_ids = {label: m.id for label, m in zip(labels, inventory)}
        self.monitor_box.configure(values=labels)
        selected = previous or self.owner.monitor_choices['stream'].get()
        self.monitor_choice.set(next((label for label, mid in self.monitor_ids.items() if mid == selected), labels[0] if labels else ''))
        self.monitor_job = self.window.after(500, self.refresh_monitors)

    def toggle_test(self):
        if self.test:
            self.stop_test()
            return
        if self.owner.session or self.owner.projections:
            self.status.set('Před zkušební projekcí zastavte běžnou prezentaci.')
            return
        mid = self.monitor_ids.get(self.monitor_choice.get())
        monitor = next((m for m in self.owner.monitor_inventory if m.id == mid), None)
        if monitor is None or self.owner.monitor_error:
            self.status.set('Vyberte dostupný monitor ukázky.')
            return
        cx, cy = self.window.winfo_rootx()+self.window.winfo_width()/2, self.window.winfo_rooty()+self.window.winfo_height()/2
        if self.fullscreen.get() and monitor.x <= cx < monitor.x+monitor.width and monitor.y <= cy < monitor.y+monitor.height:
            self.status.set('Pro celou obrazovku vyberte jiný monitor než editor, nebo vypněte Celá obrazovka.')
            return
        self.redraw()
        try:
            self.test = CalibrationProjection(self, 'stream', monitor, self.fullscreen.get())
            self.test.window.title('Zkušební snímek — prostor kamery streamu')
            self.test_button.configure(text='Ukončit ukázku')
            self.status.set('Ukázka běží. Posuvníky mění její okraje; Escape v projekčním okně ji ukončí.')
        except (RuntimeError, tk.TclError) as exc:
            self.status.set('Ukázku nelze spustit: '+str(exc))

    def stop_test(self):
        test, self.test = self.test, None
        if test and test.window.winfo_exists():
            test.window.destroy()
        if self.test_button.winfo_exists():
            self.test_button.configure(text='Promítnout ukázku')

    def stop_projection(self, output=None):
        self.stop_test()

    def projection_destroyed(self, output, window):
        if self.test is window:
            self.test = None
            if self.test_button.winfo_exists():
                self.test_button.configure(text='Promítnout ukázku')

    def blackout_key(self, event):
        return 'break'

    def navigate_presenter(self, target):
        pass

    def start(self, from_current=False):
        pass

    def apply(self, permanent=False):
        self.owner.finish_editing()
        self.changed('x')
        document = replace(self.owner.document, stream=replace(self.owner.document.stream, camera=self.camera))
        try:
            paginate(document, self.owner.metrics, self.owner.typography)
            if permanent:
                settings = replace(self.owner.settings, **{'camera_'+key: getattr(self.camera, key) for key, _ in FIELDS})
                save_settings(settings)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Prostor kamery', str(exc), parent=self.window)
            return False
        if permanent:
            self.owner.settings = settings
        self.owner.commit(document)
        self.owner.rebuild()
        self.owner.status.set('Prostor kamery nastaven.' + (' Výchozí hodnoty uloženy pro nové prezentace.' if permanent else '')
                              + (' Živou verzi potvrďte přes Použít do projekce.' if self.owner.session else ''))
        self.close()
        return True

    def close(self):
        self.stop_test()
        self.window.destroy()

    def destroyed(self, event):
        if event.widget is self.window:
            for job in (self.redraw_job, self.monitor_job):
                if job:
                    self.window.after_cancel(job)
            self.redraw_job = self.monitor_job = None
            self.stop_test()
