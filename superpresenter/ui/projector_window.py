"""Extracted presentation projector; legacy behavior is preserved."""
from __future__ import annotations
from typing import TYPE_CHECKING
import tkinter as tk
from tkinter import font as tkFont
from superpresenter.services.projection_config import resource_path
from superpresenter.services.stationary_navigation import StationaryPageWidget, style_mode
from superpresenter.ui.projector_widgets import Widget_OneLine, Widget_FlowLines, Widget_StanzaPaged, Widget_Image
if TYPE_CHECKING:
    from superpresenter.ui.main_window import GUI


class ProjWindow():
    COLLECTION_CFG = {
        'source': 'images/sbirka_qr.png',
        'relx': 0.65,
        'rely': 0.30,
        'size': 360,
        'anchor': 'center'
    }

    def __init__(self, master:GUI):
        self.master = master
        self.monitor = 0
        self.style = 0
        self.fullscreen = 1
        self.winPlacement = ''
        self.window_position = None
        self.animation = 0

        # nově:
        self.collection = False
        self.collection_item = None  # canvas image id
        self.collection_img = None

    def _get_collection_cfg(self):
        stl = self.master.projStyles[self.style]
        if 'collection' not in stl:
            return None
        cfg = dict(self.COLLECTION_CFG)
        cfg.update(stl['collection'])
        return cfg

    def project(self):
        stl = self.master.projStyles[self.style]

        self.win = tk.Toplevel(self.master.win)
        self.win.bind('<Shift-Right>', self.master.nextSlideKey)
        self.win.bind('<Shift-Left>', self.master.prevSlideKey)
        self.win.bind('<Right>', self.master.nextStepKey)
        self.win.bind('<Left>', self.master.prevStepKey)
        self.win.bind('<Escape>',self.master.runButtFun)

        self.win.title(f'projector window {stl["name"]}')

        if self.fullscreen:
            mon = self.master.monitors[self.monitor]
            self.win.overrideredirect(1)
            self.win.geometry(f'{mon.width}x{mon.height}{mon.x:+d}{mon.y:+d}')
            try:
                self.win.configure(background=stl['win']['background'])
            except (KeyError, tk.TclError):
                pass
            # self.win.attributes('-fullscreen', True)
        elif self.winPlacement == '':
            mon = self.master.monitors[self.monitor]
            self.win.geometry(f'{mon.x:+d}{mon.y:+d}')
            self.win.config(stl["win"])
        else:
            self.win.geometry(self.winPlacement)
            self.win.config(stl["win"])
        # if self.fullscreen:
        #     self.win.attributes('-fullscreen', True)



        self.canvas = tk.Canvas(self.win)
        self.canvas.config(stl["canvas"])

        self.animated = []
        self.others = []
        self.tops = []
        fonts = {}
        for font in stl['fonts'].keys():
            fnt = stl['fonts'][font]
            fonts[font] = tkFont.Font(
                family=fnt['family'],
                size=fnt['size'],
                weight=fnt['weight'],
                slant=fnt['slant']
            )
        for widget in stl["widgets"]:
            if (style_mode(stl) != 'legacy_scroll'
                    and widget['type'] in ('one_line', 'flow_lines', 'stanza_paged')):
                idx = len(self.animated)
                self.animated.append(StationaryPageWidget(
                    self.canvas, widget, fonts, style_mode(stl)))
                x = 'animated'
            elif widget["type"] == 'one_line':
                if len(self.master.onlineSources) == 0:
                    continue
                idx = len(self.animated)
                self.animated.append(Widget_OneLine(self.canvas,
                    self.master.onlineSources[\
                    self.master.runningSlide].lines, widget, fonts))
                x = 'animated'
            elif widget["type"] == 'flow_lines':
                if len(self.master.onlineSources) == 0:
                    continue
                idx = len(self.animated)
                self.animated.append(Widget_FlowLines(self.canvas,
                    self.master.onlineSources[\
                    self.master.runningSlide].lines, widget, fonts))
                self.animated[-1].switch(0,0)
                x = 'animated'
            elif widget['type'] == 'image':
                idx = len(self.others)
                self.others.append(Widget_Image(self.canvas, widget, self.win))
                x = 'others'
            elif widget["type"] == 'stanza_paged':
                if len(self.master.onlineSources) == 0:
                    continue
                idx = len(self.animated)
                self.animated.append(Widget_StanzaPaged(
                    self.canvas,
                    self.master.onlineSources[self.master.runningSlide].lines,
                    widget,
                    fonts
                ))
                self.animated[-1].switch(0, 0)
                x = 'animated'
            if 'topmost' in widget.keys():
                if widget['topmost']:
                    self.tops.append([x, idx])

        # self.canvas.place(relx=0.5, rely=0.5, anchor='center')
        self.canvas.place(stl["canvas.place"])
        self.collection_item = None
        self.collection_img = None
        self._build_collection_overlay()
        self.set_collection_visible(self.collection)
        self.canvas.bind('<Configure>', self._reposition_collection_overlay)
        self.win.protocol("WM_DELETE_WINDOW", self.master.onProjectorClose)

    def _reposition_collection_overlay(self, *_):
        if self.collection_item is None:
            return
        cfg = self._get_collection_cfg()
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        x = int(float(cfg.get('relx', 0.87)) * w)
        y = int(float(cfg.get('rely', 0.55)) * h)
        self.canvas.coords(self.collection_item, x, y)

    def stopProjection(self):
        try:
            if not self.fullscreen:
                self.window_position = [self.win.winfo_x(), self.win.winfo_y()]
                self.winPlacement = f'{self.window_position[0]:+d}{self.window_position[1]:+d}'
            self.win.destroy()
            del self.win
        except (AttributeError, tk.TclError):
            pass

    def showStationaryPage(self, page):
        for widget in self.animated:
            widget.show_page(page)

    def switch(self, idx, e):
        # idx může být int (zpětná kompatibilita) nebo tuple (pair_idx, long_idx)
        is_tuple = isinstance(idx, tuple)

        if self.animation:
            stillAnimated = []
            for idx2 in self.stillAnimated:
                widget = self.animated[idx2]
                widx = idx
                if not isinstance(widget, Widget_StanzaPaged):
                    if is_tuple:
                        if isinstance(widget, Widget_OneLine) and getattr(widget, "srcType", "") == "short2":
                            widx = idx[0] if idx[0] is not None else idx[1]
                        elif isinstance(widget, Widget_FlowLines):
                            widx = idx[1]
                        else:
                            widx = idx[1]
                a = widget.switch(widx, e)
                if a:
                    stillAnimated.append(idx2)
            self.animation = len(stillAnimated) > 0
            if self.animation:
                self.stillAnimated = stillAnimated
            return self.animation
        else:
            self.stillAnimated = []
            self.animation = 1
            for i, widget in enumerate(self.animated):
                widx = idx
                if not isinstance(widget, Widget_StanzaPaged):
                    if is_tuple:
                        if isinstance(widget, Widget_OneLine) and getattr(widget, "srcType", "") == "short2":
                            widx = idx[0] if idx[0] is not None else idx[1]
                        elif isinstance(widget, Widget_FlowLines):
                            widx = idx[1]
                        else:
                            widx = idx[1]
                a = widget.switch(widx, e)
                if a:
                    self.stillAnimated.append(i)
            self.animation = (len(self.stillAnimated) > 0)
            return self.animation

    def switchSource(self):
        for widget in self.animated:
            widget.switchSource(self.master.onlineSources\
                [self.master.runningSlide].lines)
        for x in self.tops:
            if x[0] == 'animated':
                self.animated[x[1]].widgetRaise2top()
            elif x[0] == 'others':
                self.others[x[1]].widgetRaise2top()
        if self.collection_item is not None:
            self.canvas.tag_raise(self.collection_item)

    def _build_collection_overlay(self):
        from PIL import Image, ImageTk
        cfg = self._get_collection_cfg()
        if cfg is None:
            return  # tento styl sbírku nepodporuje

        src = resource_path(cfg['source'], self.master.dir)

        img = Image.open(src)
        sz = int(cfg.get('size', 360))
        if sz > 0:
            img = img.resize((sz, sz), Image.LANCZOS)

        self.collection_img = ImageTk.PhotoImage(img)

        self.canvas.update_idletasks()
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        x = int(float(cfg.get('relx', 0.87)) * w)
        y = int(float(cfg.get('rely', 0.55)) * h)
        anchor = cfg.get('anchor', 'center')

        if self.collection_item is not None:
            try:
                self.canvas.delete(self.collection_item)
            except tk.TclError:
                pass

        self.collection_item = self.canvas.create_image(
            x, y, image=self.collection_img, anchor=anchor, state='hidden'
        )
        self.canvas.tag_raise(self.collection_item)

    def set_collection_visible(self, show: bool):
        """Zapne/vypne QR jen u stylů, které ho mají definovaný."""
        if self._get_collection_cfg() is None:
            return  # pro tento styl ignoruj přepínač
        self.collection = bool(show)
        if self.collection_item is None:
            self._build_collection_overlay()
            if self.collection_item is None:
                return
        self.canvas.itemconfigure(self.collection_item,
                                  state=('normal' if self.collection else 'hidden'))
        try:
            self._reposition_collection_overlay()
        except Exception:
            pass
        self.canvas.tag_raise(self.collection_item)
        self.canvas.update_idletasks()
