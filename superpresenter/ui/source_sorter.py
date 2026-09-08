"""Extracted presentation sorter; legacy behavior is preserved."""
import tkinter as tk
from tkinter import font as tkFont
import time


class SortingWin():
    def __init__(self, masterWin:tk.Tk, winStyle, lines, positions):
        self.win = tk.Toplevel(masterWin)
        self.win.configure(winStyle['window'])
        self.win.geometry(f'+{masterWin.winfo_rootx() + 100}'+\
            f'+{masterWin.winfo_rooty() + 100}')

        self.selected = 0

        myfont = tkFont.Font(name=winStyle['font']['name'],
            family=winStyle['font']['family'],
            size=winStyle['font']['size'],
            weight=winStyle['font']['weight'])
        self.lines = []
        self.labels = []
        self.positions = positions
        self.positions0 = positions
        idx = 0
        self.win.bind('<B1-Motion>',self.motion)
        for line in lines:
            col = 2*int(idx/winStyle['rows'])
            row = idx % winStyle['rows']

            self.labels.append(tk.Label(self.win, font=myfont, text=f' {idx+1}.'))
            self.labels[-1].config(winStyle['order'])
            self.labels[-1].grid(column = col, row = row)

            self.lines.append(tk.Label(self.win, font=myfont, text= line))
            self.lines[-1].config(winStyle['lines'])
            self.lines[-1].grid(column = col+1, row = row)
            self.lines[-1].bind('<Button>', self.click)
            self.lines[-1].bind('<ButtonRelease>', self.place)

            idx += 1
        self.rows = winStyle['rows']
        self.win.update()
        self.w = self.lines[0].winfo_x() + self.lines[0].winfo_width()
        self.h = self.lines[0].winfo_y() + self.lines[0].winfo_height()

    def click(self, e:tk.Event):
        self.x = e.x_root - self.win.winfo_rootx()
        self.y = e.y_root - self.win.winfo_rooty()
        self.idx = int(self.x/self.w)*self.rows + int(self.y/self.h)
        self.t = time.time()
        self.c1 = 0
        self.selected = 1
        self.win.after(30, self.drag)
        self.skip = 0

    def motion(self, e):
        self.x = e.x_root - self.win.winfo_rootx()
        self.y = e.y_root - self.win.winfo_rooty()

    def drag(self):
        if self.selected:
            self.c1 += 1
            self.lines[self.idx].lift()
            self.lines[self.idx].place(x= self.x, y= self.y, anchor = 'center')
            if self.c1 > 10:
                self.c1 = 0
                self.skip = 1
                idx = self.place()
                self.skip = 0
                self.idx = idx
                self.selected = 1
            self.win.after(30, self.drag)

    def place(self, *e):
        self.selected = 0
        idx = min(int(self.x/self.w)*self.rows + int(self.y/self.h),
            len(self.lines)-1)
        line = self.lines.pop(self.idx)
        self.lines.insert(idx, line)
        pos = self.positions.pop(self.idx)
        self.positions.insert(idx, pos)
        for idx2 in range(min(self.idx, idx), len(self.lines)):
            if self.skip:
                if idx2 == idx:
                    continue
            col = 2*int(idx2/self.rows)
            row = idx2 % self.rows
            self.lines[idx2].grid(column = col+1, row = row)
        self.win.update()
        return idx
