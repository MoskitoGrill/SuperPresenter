"""PresentationPresenter's collapsible, keyboard reachable command ribbon."""
import tkinter as tk
from .appearance import appearance, reserve_button_labels
from .window_chrome import TabTitleBar


def command_group(parent, name):
    """A layout group using the current native appearance, with its label below."""
    frame = tk.Frame(parent, padx=6, pady=2)
    frame.pack(side='left', anchor='n', padx=(0, 6))
    content = tk.Frame(frame)
    content.pack(fill='x', anchor='n')
    theme = appearance(parent)
    frame.command_caption = tk.Label(frame, text=name, font=theme.small, fg=theme.muted)
    frame.command_caption.pack(side='bottom', pady=(5, 0))
    frame.command_separator = tk.Frame(frame, width=1, bg='#777777')
    frame.command_separator.ribbon_separator = True
    return content


def space_control_rows(widget):
    """Add breathing room between stacked ribbon rows, including labels and fields."""
    children = widget.winfo_children()
    if not hasattr(widget, 'command_caption'):
        packed = [child for child in children if child.winfo_manager() == 'pack'
                  and child.pack_info()['side'] in ('top', 'bottom')]
        gridded = [child for child in children if child.winfo_manager() == 'grid']
        rows = {int(child.grid_info()['row']) for child in gridded}
        targets = packed if len(packed) > 1 else []
        targets += gridded if len(rows) > 1 else []
        for child in targets:
            manager = child.winfo_manager()
            options = child.pack_info() if manager == 'pack' else child.grid_info()
            value = options['pady']
            values = value if isinstance(value, (tuple, list)) else child.tk.splitlist(str(value))
            pads = [child.winfo_pixels(value)+2 for value in values]
            if manager == 'pack':
                child.pack_configure(pady=tuple(pads))
            else:
                child.grid_configure(pady=tuple(pads))
    for child in children:
        space_control_rows(child)


def wrap_row(frame, reserve_width=None, stretch_groups=False):
    """Wrap command rows using actual requested sizes, including DPI scaling."""
    children = frame.winfo_children()
    positions = {}
    for child in children:
        child.pack_forget()
        child.grid_forget()

    def layout(width, place=False):
        rows = []
        row, used, row_height = [], 0, 0
        for child in children:
            if getattr(child, 'layout_hidden', False):
                if place:
                    child.place_forget()
                    positions.pop(child, None)
                continue
            needed = child.winfo_reqwidth() + 4
            if used and used + needed > width:
                rows.append((row, row_height))
                row, used, row_height = [], 0, 0
            row.append((child, used+2))
            used += needed
            row_height = max(row_height, child.winfo_reqheight())
        if row:
            rows.append((row, row_height))
        natural_height = sum(height for _, height in rows)
        if place:
            extra = max(0, frame.winfo_height()-8-natural_height) if stretch_groups else 0
            y = 0
            for index, (row, height) in enumerate(rows):
                height += extra // len(rows) + (index < extra % len(rows))
                free_width = max(0, width-sum(child.winfo_reqwidth()+4 for child, _ in row))
                width_extra = min(32, free_width//len(row)) if stretch_groups else 0
                for column, (child, x) in enumerate(row):
                    x += column*width_extra
                    group_width = child.winfo_reqwidth()+width_extra if stretch_groups else None
                    position = (x, y, height if stretch_groups else None, group_width)
                    if positions.get(child) != position:
                        child.place(x=x, y=y, height=position[2], width=position[3])
                        positions[child] = position
                    if stretch_groups and hasattr(child, 'command_separator'):
                        child.command_separator.place(relx=1, x=-1, y=0, relheight=1)
                y += height
        return natural_height

    frame.wrapped_height = layout

    def arrange(event=None):
        inner_width = frame.winfo_width()-2*frame.winfo_pixels(frame.cget('padx'))
        height = layout(max(1, inner_width), place=True)
        if reserve_width is not None:
            height = max(height, layout(reserve_width))
        if frame.winfo_reqheight() != height:
            frame.configure(height=height)
    frame.bind('<Configure>', arrange)
    arrange()
    return arrange


class Ribbon:
    def __init__(self, parent, close=None):
        self.frame = tk.Frame(parent)
        self.frame.pack(fill='x', padx=8, pady=(4, 0))
        self.divider = tk.Frame(self.frame, height=1, bg='#777777')
        self.divider.pack(side='bottom', fill='x', pady=(4, 0))
        self.tabs = tk.Frame(self.frame)
        self.tabs.pack(fill='x')
        self.title_bar = TabTitleBar(parent._root(), self.tabs, close, appearance(parent)) if close else None
        if self.title_bar and self.title_bar.native:
            self.frame.pack_configure(padx=0, pady=0)
        self.toggle_button = tk.Button(self.tabs, text='Sbalit lištu ▴', command=self.toggle)
        if self.title_bar and self.title_bar.native:
            self.toggle_button.configure(font=('Segoe UI', 9), bg=appearance(parent).background,
                                         highlightthickness=0, padx=10, pady=4)
        self.toggle_button.pack(side='right')
        reserve_button_labels(self.toggle_button, 'Sbalit lištu ▴', 'Rozbalit lištu ▾')
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
        self.shade_surface(self.frame)
        self.resize()

    def shade_surface(self, widget):
        """Keep the entire ribbon surface distinct, including empty space."""
        if (widget is self.divider or getattr(widget, 'ribbon_separator', False)
                or getattr(widget, 'ribbon_chrome', False)):
            return
        theme = appearance(self.frame)
        kind = widget.winfo_class()
        if kind in ('Frame', 'Label', 'Checkbutton', 'Radiobutton'):
            widget.configure(background=theme.ribbon)
            if kind in ('Checkbutton', 'Radiobutton'):
                widget.configure(activebackground=theme.ribbon, highlightbackground=theme.ribbon)
        for child in widget.winfo_children():
            self.shade_surface(child)

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
        if self.title_bar and self.title_bar.native:
            button.configure(font=('Segoe UI', 10), highlightthickness=0, padx=12, pady=6)
        button.pack(side='left', padx=(0, 4))
        self.buttons[name] = button
        return panel

    def show(self, name):
        for panel in self.panels.values():
            panel.pack_forget()
        self.current = name
        self.panels[name].pack(fill='both', expand=True)
        if not self.expanded:
            self.content.pack(fill='x')
        self.expanded = True
        self.toggle_button.configure(text='Sbalit lištu ▴')
        for label, button in self.buttons.items():
            theme = appearance(self.frame)
            button.configure(relief='sunken' if label == name else 'flat',
                             background=theme.field if label == name else theme.ribbon,
                             highlightbackground=theme.foreground if label == name else theme.ribbon)
            if self.title_bar and self.title_bar.native:
                button.configure(relief='flat', background=theme.field if label == name else theme.background)

    def toggle(self):
        if self.expanded:
            self.content.pack_forget()
            self.expanded = False
            self.toggle_button.configure(text='Rozbalit lištu ▾')
            self.toggle_button.focus_set()
        else:
            self.show(self.current)
