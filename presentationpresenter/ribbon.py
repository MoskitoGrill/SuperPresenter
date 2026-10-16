"""PresentationPresenter's collapsible, keyboard reachable command ribbon."""
import tkinter as tk


def wrap_row(frame, reserve_width=None):
    """Wrap command rows using actual requested sizes, including DPI scaling."""
    children = frame.winfo_children()
    positions = {}
    for child in children:
        child.pack_forget()
        child.grid_forget()

    def layout(width, place=False):
        y = used = row_height = 0
        for child in children:
            needed = child.winfo_reqwidth() + 4
            if used and used + needed > width:
                y, used, row_height = y+row_height, 0, 0
            if place:
                position = (used+2, y)
                if positions.get(child) != position:
                    child.place(x=position[0], y=position[1])
                    positions[child] = position
            used += needed
            row_height = max(row_height, child.winfo_reqheight())
        return y+row_height

    frame.wrapped_height = layout

    def arrange(event=None):
        height = layout(max(1, frame.winfo_width()), place=True)
        if reserve_width is not None:
            height = max(height, layout(reserve_width))
        if frame.winfo_reqheight() != height:
            frame.configure(height=height)
    frame.bind('<Configure>', arrange)
    arrange()
    return arrange


class Ribbon:
    def __init__(self, parent):
        self.frame = tk.Frame(parent)
        self.frame.pack(fill='x', padx=8, pady=(4, 0))
        self.tabs = tk.Frame(self.frame)
        self.tabs.pack(fill='x')
        self.toggle_button = tk.Button(self.tabs, text='Sbalit lištu ▴', command=self.toggle)
        self.toggle_button.pack(side='right')
        self.content = tk.Frame(self.frame)
        self.content.pack(fill='x')
        self.panels, self.buttons = {}, {}
        self.current = None
        self.expanded = True
        self.height_sources = []
        self.content.pack_propagate(False)
        self.content.bind('<Configure>', self.resize)

    def reserve_height(self, sources):
        self.height_sources = sources
        self.resize()

    def resize(self, event=None):
        width = self.content.winfo_width()
        if width > 1 and self.height_sources:
            height = max(measure(width) for measure in self.height_sources)
            if self.content.winfo_reqheight() != height:
                self.content.configure(height=height)

    def add(self, name):
        panel = tk.Frame(self.content, padx=4, pady=4)
        self.panels[name] = panel
        button = tk.Button(self.tabs, text=name, command=lambda: self.show(name))
        button.pack(side='left', padx=(0, 4))
        self.buttons[name] = button
        return panel

    def show(self, name):
        for panel in self.panels.values():
            panel.pack_forget()
        self.current = name
        self.panels[name].pack(fill='x')
        if not self.expanded:
            self.content.pack(fill='x')
        self.expanded = True
        self.toggle_button.configure(text='Sbalit lištu ▴')
        for label, button in self.buttons.items():
            button.configure(relief='sunken' if label == name else 'raised')

    def toggle(self):
        if self.expanded:
            self.content.pack_forget()
            self.expanded = False
            self.toggle_button.configure(text='Rozbalit lištu ▾')
            self.toggle_button.focus_set()
        else:
            self.show(self.current)
