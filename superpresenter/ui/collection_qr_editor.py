"""Transactional QR editor with the same geometry as the hall overlay."""
from copy import deepcopy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

from superpresenter.paths import PROJECT_ROOT
from superpresenter.windows_shell import style_title_bar
from superpresenter.services.projection_config import resource_path
from superpresenter.services.collection_qr import (
    default_settings, validate_settings, encode_image, decode_image, geometry, render_image,
)


class CollectionQREditor:
    def __init__(self, parent, style, settings, on_apply, hall_rows=8):
        self.style, self.on_apply, self.hall_rows = style, on_apply, hall_rows
        self.settings = deepcopy(settings) if settings is not None else default_settings(style)
        self._draw_job = None
        self._background_size = None
        self._photo_key = None
        self.win = tk.Toplevel(parent)
        self.win.title('Nastavení QR sbírky')
        self.win.transient(parent)
        self.win.protocol('WM_DELETE_WINDOW', self.cancel)
        self.win.bind('<Escape>', lambda event: self.cancel())
        self.win.columnconfigure(0, weight=1)
        self.win.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self.win, width=640, height=360, background='black', highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky='nsew', padx=12, pady=12)
        controls = ttk.Frame(self.win, padding=12)
        controls.grid(row=1, column=0, sticky='ew')
        controls.columnconfigure(1, weight=1)
        self.image_name = tk.StringVar(self.win)
        ttk.Button(controls, text='Vybrat obrázek QR…', command=self.choose_image).grid(row=0, column=0, padx=4)
        ttk.Label(controls, textvariable=self.image_name, wraplength=380).grid(row=0, column=1, columnspan=2, sticky='w')
        self.values = {}
        for index, (key, label) in enumerate((('size_pct', 'Velikost (% kratší strany)'),
                                             ('x_pct', 'Vodorovně (%)'), ('y_pct', 'Svisle (%)')), 1):
            value = tk.StringVar(self.win, value=f'{self.settings[key]:.2f}')
            self.values[key] = value
            ttk.Label(controls, text=label).grid(row=index, column=0, sticky='w', pady=4)
            ttk.Scale(controls, from_=1 if key == 'size_pct' else 0, to=100,
                      command=lambda n, var=value: var.set(f'{float(n):.2f}'),
                      variable=value).grid(row=index, column=1, sticky='ew', padx=8)
            ttk.Entry(controls, textvariable=value, width=8).grid(row=index, column=2)
            value.trace_add('write', self.schedule_draw)
        presets = ttk.Frame(controls)
        presets.grid(row=4, column=0, columnspan=3, pady=6)
        for index, (label, x, y) in enumerate([('Vlevo nahoře', 0, 0), ('Vpravo nahoře', 100, 0),
                                              ('Vlevo dole', 0, 100), ('Vpravo dole', 100, 100)]):
            ttk.Button(presets, text=label, command=lambda x=x, y=y: self.position(x, y)).grid(
                row=index // 2, column=index % 2, sticky='ew', padx=4, pady=4)
        ttk.Label(controls, text='QR lze přetáhnout v náhledu. Poloha 0 % = levý/horní okraj, 100 % = pravý/dolní.\n'
                  'Bílý okraj je součástí velikosti. Text v náhledu je pouze ukázka.', wraplength=600).grid(row=5, column=0, columnspan=3, pady=4)
        self.status = tk.StringVar(self.win)
        ttk.Label(controls, textvariable=self.status, foreground='#ff9999').grid(row=6, column=0, columnspan=3)
        buttons = ttk.Frame(controls)
        buttons.grid(row=7, column=0, columnspan=3, sticky='ew', pady=6)
        ttk.Button(buttons, text='Obnovit výchozí nastavení', command=self.reset).pack(side='left')
        ttk.Button(buttons, text='Použít', command=self.apply).pack(side='right', padx=4)
        ttk.Button(buttons, text='Zrušit', command=self.cancel).pack(side='right', padx=4)
        self.configure_appearance()
        self.image = None
        self.load_image()
        self.canvas.bind('<Configure>', self.schedule_draw)
        self.canvas.bind('<ButtonPress-1>', self.start_drag)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.drag_offset = None
        self.win.grab_set()
        self.win.update_idletasks()
        width = min(self.win.winfo_reqwidth(), self.win.winfo_screenwidth() - 80)
        height = min(self.win.winfo_reqheight(), self.win.winfo_screenheight() - 100)
        self.win.geometry(f'{width}x{height}')
        self.win.minsize(min(width, 720), min(height, controls.winfo_reqheight() + 140))
        self.draw()
        style_title_bar(self.win)

    def configure_appearance(self):
        """Reuse the enclosing projection editor's application styles."""
        background = self.win.master.cget('background')
        self.win.configure(background=background)
        theme = ttk.Style(self.win)
        theme.configure('Projection.Horizontal.TScale', background=background,
                        troughcolor='#222222', bordercolor=background,
                        lightcolor='#666666', darkcolor='#444444')
        theme.map('Projection.Horizontal.TScale', background=[('active', '#666666')])
        styles = {'TFrame': 'Projection.TFrame', 'TLabel': 'Projection.TLabel',
                  'TButton': 'Projection.TButton', 'TEntry': 'Projection.TEntry',
                  'TScale': 'Projection.Horizontal.TScale'}
        def configure_children(parent):
            for child in parent.winfo_children():
                kind = child.winfo_class()
                if kind in styles:
                    child.configure(style=styles[kind])
                    if kind == 'TEntry':
                        child.configure(font=theme.lookup('Projection.TLabel', 'font'))
                    elif kind == 'TLabel' and (child.cget('wraplength') or child.cget('textvariable') == str(self.status)):
                        child.configure(style='Projection.Status.TLabel')
                configure_children(child)
        configure_children(self.win)

    def load_image(self):
        try:
            if 'image_data' in self.settings:
                self.image = decode_image(self.settings['image_data'])
                self.image_name.set(self.settings.get('image_name', 'Vlastní QR'))
            else:
                source = self.style.get('collection', {}).get('source', 'images/sbirka_qr.png')
                with Image.open(resource_path(source, PROJECT_ROOT)) as image:
                    self.image = image.convert('RGBA')
                self.image_name.set(Path(source).name)
            self.status.set('')
        except (OSError, ValueError) as exc:
            self.image = None
            self.status.set(str(exc))

    def current(self):
        settings = dict(self.settings)
        try:
            settings.update({key: float(var.get().replace(',', '.')) for key, var in self.values.items()})
        except ValueError:
            raise ValueError('Zadejte číselnou velikost a polohu.') from None
        # Image is decoded on selection, not on every drag event.
        validate_settings({k: v for k, v in settings.items() if k != 'image_data'})
        return settings

    def choose_image(self):
        path = filedialog.askopenfilename(parent=self.win, title='Vybrat obrázek QR',
                                         filetypes=[('Obrázky', '*.png *.jpg *.jpeg *.bmp *.gif'), ('Všechny soubory', '*.*')])
        if not path:
            return
        try:
            data = encode_image(path)
            image = decode_image(data)
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            messagebox.showerror('Obrázek QR', str(exc), parent=self.win)
            return
        self.settings.update(image_data=data, image_name=Path(path).name)
        self.image = image
        self.image_name.set(Path(path).name)
        self.draw()

    def schedule_draw(self, *_):
        if self._draw_job is None:
            self._draw_job = self.win.after(16, self._scheduled_draw)

    def _scheduled_draw(self):
        self._draw_job = None
        self.draw()

    def draw(self, *_):
        if not hasattr(self, 'image'):
            return
        try:
            settings = self.current()
        except ValueError as exc:
            self.status.set(str(exc))
            return
        if self.image is None:
            return
        self.status.set('')
        canvas = self.canvas
        width, height = max(1, canvas.winfo_width()), max(1, canvas.winfo_height())
        sw, sh = self.style['canvas'].get('width', 1920), self.style['canvas'].get('height', 1080)
        scale = min(width / sw, height / sh)
        w, h = sw * scale, sh * scale
        left, top = (width - w) / 2, (height - h) / 2
        self.preview_rect = (left, top, w, h)
        if self._background_size != (width, height):
            canvas.delete('background')
            self._draw_background(left, top, w, h, scale)
            self._background_size = (width, height)
        x, y, side = geometry(settings, w, h)
        photo_key = (self.image, side)
        if self._photo_key != photo_key:
            self.photo = ImageTk.PhotoImage(render_image(self.image, side), master=self.win)
            self._photo_key = photo_key
        self.qr_rect = (left + x, top + y, side)
        if canvas.find_withtag('qr'):
            canvas.coords('qr', left + x, top + y)
            canvas.itemconfigure('qr', image=self.photo)
        else:
            canvas.create_image(left + x, top + y, image=self.photo, anchor='nw', tags='qr')
        canvas.tag_raise('qr')

    def _draw_background(self, left, top, w, h, scale):
        canvas = self.canvas
        sw = self.style['canvas'].get('width', 1920)
        canvas.create_rectangle(left, top, left + w, top + h,
                                fill=self.style['canvas'].get('background', 'black'),
                                outline='#888', tags='background')
        text_style = next((item for item in self.style['widgets'] if item['type'] != 'image'), {})
        spacing = text_style.get('y1', 48) * min(1, 8 / max(1, self.hall_rows))
        font_size = self.style['fonts'].get(text_style.get('primaryFont'), {}).get('size', 33)
        for row in range(self.hall_rows):
            canvas.create_text(left + text_style.get('x', sw / 2) * scale,
                               top + (text_style.get('y', 100) + row * spacing) * scale,
                               text='Ukázkový text písně' if row % 2 == 0 else 'Další řádek společné chvály',
                               fill=text_style.get('fill', 'white'), anchor='n',
                               font=('Arial', max(1, round(font_size * scale * min(1, 8 / self.hall_rows)))),
                               tags='background')

    def position(self, x, y):
        self.values['x_pct'].set(f'{x:.2f}')
        self.values['y_pct'].set(f'{y:.2f}')

    def start_drag(self, event):
        self.drag_offset = None
        if not hasattr(self, 'qr_rect'):
            return
        x, y, side = self.qr_rect
        if x <= event.x <= x + side and y <= event.y <= y + side:
            self.drag_offset = (event.x - x, event.y - y)

    def drag(self, event):
        if self.drag_offset is None:
            return
        left, top, width, height = self.preview_rect
        side = self.qr_rect[2]
        x = 100 * (event.x - self.drag_offset[0] - left) / max(1, width - side)
        y = 100 * (event.y - self.drag_offset[1] - top) / max(1, height - side)
        self.position(max(0, min(100, x)), max(0, min(100, y)))

    def reset(self):
        self.settings = default_settings(self.style)
        self.load_image()
        for key, var in self.values.items():
            var.set(f'{self.settings[key]:.2f}')
        self.draw()

    def apply(self):
        try:
            settings = self.current()
            validate_settings(settings)
            if self.image is None:
                raise ValueError('Vyberte platný obrázek QR.')
        except ValueError as exc:
            messagebox.showerror('Nastavení QR', str(exc), parent=self.win)
            return
        self.on_apply(settings)
        self.cancel()

    def cancel(self):
        if self._draw_job is not None:
            self.win.after_cancel(self._draw_job)
            self._draw_job = None
        parent = self.win.master
        self.win.grab_release()
        self.win.destroy()
        if parent.winfo_exists():
            parent.grab_set()
