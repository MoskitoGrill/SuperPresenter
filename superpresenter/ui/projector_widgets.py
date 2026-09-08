"""Extracted presentation widgets; legacy behavior is preserved."""
import tkinter as tk
import math
from PIL import ImageTk, Image
from superpresenter.services.projection_config import resource_path


class Widget_OneLine():
    def __init__(self, canvas:tk.Canvas, source, style, fonts):
        self.source = source[style['source']]
        self.steps = source[style['source']+'steps']
        self.fonts = fonts
        self.style = style
        self.canvas = canvas
        self.lines = []
        self.srcType = style['source']
        y = style['y'] -style['y1']*0.5
        for _ in self.source[1:]:
            y -= style['y2']*0.5
        self.lines.append(canvas.create_text(style['x'], y, fill=style['fill'],
            font=fonts[style['primaryFont']], text='', anchor = 'n'))
        y += style['y1']
        for _ in self.source[1:]:
            self.lines.append(canvas.create_text(style['x'], y, fill=style['fill'],
                font=fonts[style['secondaryFont']], text='', anchor = 'n'))
            y += style['y2']

    def switch(self, idx, *e):
        if idx == 0 or idx > len(self.steps):
            for id2 in self.lines:
                self.canvas.itemconfigure(id2, {'text':''})
        else:
            var = 0
            for id2 in self.lines:
                self.canvas.itemconfigure(
                    id2,{'text':self.source[var][self.steps[idx-1]]})
                var+=1
        return 0

    def switchSource(self, source):
        self.source = source[self.srcType]
        self.steps = source[self.srcType+'steps']
        for line in self.lines:
            self.canvas.delete(line)
        self.lines = []
        self.srcType = self.style['source']
        y = self.style['y'] -self.style['y1']*0.5
        for _ in self.source[1:]:
            y -= self.style['y2']*0.5
        self.lines.append(self.canvas.create_text(self.style['x'], y, fill=self.style['fill'],
            font=self.fonts[self.style['primaryFont']], text='', anchor = 'n'))
        y += self.style['y1']
        for _ in self.source[1:]:
            self.lines.append(self.canvas.create_text(self.style['x'], y, fill=self.style['fill'],
                font=self.fonts[self.style['secondaryFont']], text='', anchor = 'n'))
            y += self.style['y2']

    def widgetRaise2top(self):
        for line in self.lines:
            self.canvas.tag_raise(line)


class Widget_FlowLines():
    def __init__(self, canvas:tk.Canvas, source, style, fonts):
        self.source = source[style['source']]
        self.steps = source[style['source']+'steps']
        self.laststep = max(self.steps+[-1])+1
        self.canvas = canvas
        self.lines = []
        self.yCoords = []
        self.style = style
        self.fonts = fonts
        self.idx = 0
        self.animation = 0
        y = style['y'] - style['y1']*0.5
        for _ in self.source[1:]:
            y -= style['y2']*0.5
        self.row = style['y1'] + (len(self.source)-1)*style['y2'] +\
            style['gap']
        for idx in range(len(self.source[0])):
            self.lines.append(canvas.create_text(style['x'], y, fill=style['fill'],
                font=fonts[style['primaryFont']], text=self.source[0][idx],
                anchor = 'n'))
            self.yCoords.append(y)
            y += style['y1']
            for idx2 in range(1,len(self.source)):
                self.lines.append(canvas.create_text(style['x'], y, fill=style['fill'],
                    font=fonts[style['secondaryFont']], text=self.source[idx2][idx],
                    anchor = 'n'))
                self.yCoords.append(y)
                y += style['y2']
            y += style['gap']

        self.animationPath()

    def switch(self, idx, e):
        if e == 0:
            return self.switchTo(idx)
        else:
            return self.switchAnimation(idx)

    def switchTo(self, idx):
        self.animation = 0
        if idx == 0:
            id3 = 0
            for id2 in self.lines:
                self.canvas.coords(id2, self.style['x'],
                self.yCoords[id3] + self.style['stp_in'] + \
                self.row)
                id3 += 1
        elif idx == len(self.steps)+1:
            id3 = 0
            for id2 in self.lines:
                self.canvas.coords(id2, self.style['x'],
                self.yCoords[id3] - self.style['stp_out'] - \
                self.row*(self.laststep))
                id3 += 1
        else:
            id3 = 0
            for id2 in self.lines:
                self.canvas.coords(id2, self.style['x'],
                self.yCoords[id3] - self.row*self.steps[idx-1])
                id3 += 1
        self.idx = idx
        return 0

    def switchAnimation(self, idx):
        if self.animation:
            if self.animStep == self.style['path_steps']:
                self.animation = 0
                return 0
            for id2 in self.lines:
                self.canvas.move(id2, 0, self.step*self.path[self.animStep])
            self.animStep += 1
            return 1

        else:
            if idx == self.idx:
                return 0
            self.animation = 1
            if self.idx == 0:
                self.step = - self.style['stp_in'] - self.row
            elif self.idx == len(self.steps)+1:
                self.step = self.style['stp_out'] + (self.laststep)*self.row
            else:
                self.step = self.steps[self.idx-1]*self.row
            if idx == 0:
                self.step += self.style['stp_in'] + self.row
            elif idx == len(self.steps)+1:
                self.step -= self.style['stp_out'] + (self.laststep)*self.row
            else:
                self.step -= self.steps[idx-1]*self.row
            self.idx = idx
            self.animStep = 0
            return 1

    def animationPath(self):
        n = self.style['path_steps']
        if self.style['path'] == 'linear':
            fun = lambda x: x
        elif self.style['path'] == 'cubic':
            fun = lambda x: -2*(x)**3 + 3*(x)**2
        elif self.style['path'] == 'sinusoidal':
            fun = lambda x: 0.5*(1-math.cos(x*math.pi))
        elif self.style['path'] == 'poly5':
            fun = lambda x: 6*x**5 - 15*x**4 + 10*x**3
        else:
            fun = lambda x: x
        y0 = 0
        self.path = []
        for x in range(1,n+1):
            y = fun(x/n)
            self.path.append(y - y0)
            y0 = y
        if y != 1:
            self.path = [x/y for x in self.path]

    def switchSource(self, source):
        self.source = source[self.style['source']]
        self.steps = source[self.style['source']+'steps']
        self.laststep = max(self.steps+[-1])+1
        for line in self.lines:
            self.canvas.delete(line)
        self.lines = []
        self.yCoords = []
        self.idx = 0
        y = self.style['y'] - self.style['y1']*0.5
        for _ in self.source[1:]:
            y -= self.style['y2']*0.5
        self.row = self.style['y1'] + (len(self.source)-1)*self.style['y2'] + \
            self.style['gap']
        for idx in range(len(self.source[0])):
            self.lines.append(self.canvas.create_text(self.style['x'], y,
                fill=self.style['fill'], font=self.fonts[self.style['primaryFont']],
                text=self.source[0][idx], anchor = 'n'))
            self.yCoords.append(y)
            y += self.style['y1']
            for idx2 in range(1,len(self.source)):
                self.lines.append(self.canvas.create_text(self.style['x'], y,
                    fill=self.style['fill'],
                    font=self.fonts[self.style['secondaryFont']],
                    text=self.source[idx2][idx], anchor = 'n'))
                self.yCoords.append(y)
                y += self.style['y2']
            y += self.style['gap']

        self.switchTo(0)

    def widgetRaise2top(self):
        for line in self.lines:
            self.canvas.tag_raise(line)


class Widget_StanzaPaged():
    """
    Statické promítání po slokách/stránkách.
    Na plátně drží n řádků (default 8). Přepíná se stránka,
    když zvolený řádek (stream / long) spadne mimo aktuální stránku.
    """
    def __init__(self, canvas: tk.Canvas, source, style, fonts):
        self.canvas = canvas
        self.style = style
        self.fonts = fonts

        # zdroj dat
        src_key = style.get('source', 'long')
        self.source = source[src_key]                  # [var0][lines], [var1]...
        self.steps  = source[src_key + 'steps']        # 0..N-1
        self.group_lengths = source.get('group_lengths', [])
        self.pairmap = source.get('short2pairmap', [])

        # parametry rozložení
        self.page_size = int(style.get('lines_per_page', 8))
        self.x = style['x']
        self.y = style['y']
        self.y1 = style['y1']          # mezera hlavní řádky
        self.y2 = style['y2']          # mezera mezi variantami
        self.gap = style.get('gap', 12)
        self.fill = style['fill']
        self.primaryFont = fonts[style['primaryFont']]
        self.secondaryFont = fonts[style['secondaryFont']]

        # vypočti začátky stránek podle skupin (slok)
        self._rebuild_page_starts()

        # předkresli textová pole (max page_size řádků × počet variant)
        self._build_text_items()

        # žádná stránka není vykreslená
        self.cur_page = None

    def _rebuild_page_starts(self):
        self.page_starts = []
        pos = 0
        for L in self.group_lengths:
            k = 0
            while k < L:
                self.page_starts.append(pos + k)   # index prvního řádku na stránce
                k += self.page_size
            pos += L
        # sentinel pro hranici konce
        self.page_starts.append(pos)

    def _build_text_items(self):
        self.text_items = []
        n_vars = len(self.source)
        y = self.y - self.y1 * 0.5

        # ZMĚNA: Vytvoříme rezervu 100 řádků, aby se tam vešla i celá píseň
        max_rows_to_create = 100

        for _row in range(max_rows_to_create):
            row_ids = []
            row_ids.append(self.canvas.create_text(
                self.x, y, fill=self.fill, font=self.primaryFont,
                text='', anchor='n'
            ))
            y += self.y1
            for _v in range(1, n_vars):
                row_ids.append(self.canvas.create_text(
                    self.x, y, fill=self.fill, font=self.secondaryFont,
                    text='', anchor='n'
                ))
                y += self.y2
            y += self.gap
            self.text_items.append(row_ids)

    def _clear(self):
        for row in self.text_items:
            for cid in row:
                self.canvas.itemconfigure(cid, {'text': ''})

    def _page_of(self, line_idx_0based: int) -> int | None:
        if not self.page_starts or line_idx_0based < 0:
            return None
        # binární hledání by bylo rychlejší, ale lineární stačí
        for i in range(len(self.page_starts) - 1):
            if self.page_starts[i] <= line_idx_0based < self.page_starts[i + 1]:
                return i
        return None

    def _render_page(self, page_i: int):
        if page_i is None or page_i < 0 or page_i >= len(self.page_starts) - 1:
            self._clear()
            self.cur_page = None
            return

        start = self.page_starts[page_i]

        # ZMĚNA: Odstraníme "min(..., start + self.page_size)"
        # a vezmeme prostě vše až do konce aktuální sekce/skupiny
        end = self.page_starts[page_i + 1]

        rows_to_show = max(0, end - start)
        n_vars = len(self.source)

        # Promazání starých textů před vykreslením (důležité!)
        self._clear()

        for r in range(rows_to_show): # Vykreslíme jen tolik řádků, kolik je v sekci
            for v in range(n_vars):
                text = ''
                idx = start + r
                if idx < len(self.source[v]):
                    text = self.source[v][idx]
                # Kontrola, abychom nepřetekli vytvořené položky (pojistka)
                if r < len(self.text_items):
                    self.canvas.itemconfigure(self.text_items[r][v], {'text': text})

        self.cur_page = page_i

    def switch(self, idx, e):
        """
        idx může být:
          - int (kompatibilita: index do steps, 0 = úvod, len+1 = konec)
          - tuple (pair_index, long_index)
        """
        # vyzobej long_index (krok pro 'long'), 0/len+1 = mezistavy
        if isinstance(idx, tuple):
            _, long_idx = idx
        else:
            long_idx = idx

        if long_idx == 0:
            self._clear()
            return 0
        if long_idx >= len(self.steps) + 1:
            self._clear()
            return 0

        # steps = [0,1,2,...] → reálný index řádku
        line_idx = self.steps[long_idx - 1]
        page_i = self._page_of(line_idx)
        if page_i != self.cur_page:
            self._render_page(page_i)
        return 0

    def switchSource(self, source):
        src_key = self.style.get('source', 'long')
        self.source = source[src_key]
        self.steps  = source[src_key + 'steps']
        self.group_lengths = source.get('group_lengths', [])
        self.pairmap = source.get('short2pairmap', [])
        self._rebuild_page_starts()
        self._render_page(None)

    def widgetRaise2top(self):
        for row in self.text_items:
            for cid in row:
                self.canvas.tag_raise(cid)


class Widget_Image():
    def __init__(self, canvas: tk.Canvas, style:dict, win):
        self.canvas = canvas
        source = resource_path(style['source'])
        image = Image.open(source)
        if 'resize' in style.keys():
            image = image.resize((style['resize'][0],style['resize'][1]), 1)
            pass
        self.image = ImageTk.PhotoImage(image)
        self.id = canvas.create_image(style['x'], style['y'],
            anchor=style['anchor'], image=self.image)

    def widgetRaise2top(self):
        self.canvas.tag_raise(self.id)
