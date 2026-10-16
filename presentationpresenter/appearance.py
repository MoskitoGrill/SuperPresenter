"""PresentationPresenter's own UI palette, independent of SuperPresenter files.

Projection canvases and content typography are deliberately outside this theme.
"""
import tkinter as tk
from tkinter import ttk, font as tkfont
from .window_chrome import install_title_bars


class Appearance:
    ribbon = '#383838'
    field = '#666666'
    hover = '#666666'
    selected = '#404040'
    muted = '#dddddd'
    disabled = '#aaaaaa'
    warning = '#ffe2ad'
    error = '#ffb6b0'
    focus = '#ffffff'
    preview = '#303030'
    run = '#004400'
    stop = '#440000'

    def __init__(self, root, settings=None):
        self.root = root
        self.background = getattr(settings, 'background', '#555555')
        self.panel = getattr(settings, 'panel', '#444444')
        self.foreground = getattr(settings, 'foreground', '#ffffff')
        family = getattr(settings, 'font_family', 'Courier New')
        self.text = tkfont.Font(root=root, family=family, size=10)
        self.button = tkfont.Font(root=root, family=family, size=10, weight='bold')
        self.small = tkfont.Font(root=root, family=family, size=9)
        self.defaults = {
            'Frame': dict(background=self.background),
            'Toplevel': dict(background=self.background),
            'Panedwindow': dict(background=self.background, sashrelief='flat'),
            'Label': dict(background=self.background, foreground=self.foreground, font=self.text),
            'Button': dict(background=self.panel, foreground=self.foreground, font=self.button,
                           activebackground=self.hover, activeforeground=self.foreground,
                           disabledforeground=self.disabled, relief='flat', borderwidth=0,
                           highlightthickness=1, highlightbackground=self.panel,
                           highlightcolor=self.focus, padx=6, pady=3),
            'Entry': dict(background=self.field, foreground=self.foreground, font=self.text,
                          insertbackground=self.foreground, selectbackground=self.panel,
                          selectforeground=self.foreground, disabledbackground=self.background,
                          disabledforeground=self.disabled, relief='flat', borderwidth=0,
                          highlightthickness=1, highlightbackground='#888888', highlightcolor=self.focus),
            'Text': dict(background=self.field, foreground=self.foreground,
                         insertbackground=self.foreground, selectbackground=self.panel,
                         selectforeground=self.foreground, relief='flat', borderwidth=0,
                         highlightthickness=1, highlightbackground=self.field, highlightcolor=self.focus),
            'Listbox': dict(background=self.field, foreground=self.foreground, font=self.text,
                            selectbackground=self.panel, selectforeground=self.foreground,
                            relief='flat', borderwidth=0, highlightthickness=1,
                            highlightbackground=self.field, highlightcolor=self.focus),
            'Scrollbar': dict(background=self.panel, activebackground='#777777',
                              troughcolor=self.background, relief='flat', borderwidth=0),
            'Canvas': dict(background=self.background),
        }
        for kind in ('Checkbutton', 'Radiobutton'):
            self.defaults[kind] = dict(background=self.background, foreground=self.foreground,
                                       font=self.text, selectcolor=self.selected,
                                       activebackground=self.background, activeforeground=self.foreground,
                                       disabledforeground=self.disabled, highlightthickness=1,
                                       highlightbackground=self.background, highlightcolor=self.focus,
                                       borderwidth=0)
        resources = {
            'activebackground': 'activeBackground', 'activeforeground': 'activeForeground',
            'disabledforeground': 'disabledForeground', 'disabledbackground': 'disabledBackground',
            'highlightthickness': 'highlightThickness', 'highlightbackground': 'highlightBackground',
            'highlightcolor': 'highlightColor', 'borderwidth': 'borderWidth',
            'insertbackground': 'insertBackground', 'selectbackground': 'selectBackground',
            'selectforeground': 'selectForeground', 'selectcolor': 'selectColor',
            'troughcolor': 'troughColor', 'sashrelief': 'sashRelief',
        }
        for kind, options in self.defaults.items():
            for option, value in options.items():
                root.option_add(f'*{kind}.{resources.get(option, option)}', value, 60)
        # The interpreter belongs to this app. Neither global Tk fonts nor the
        # SuperPresenter theme/catalog are read or modified.
        style = ttk.Style(root)
        if 'PresentationPresenter' not in style.theme_names():
            style.theme_create('PresentationPresenter', parent='clam')
        style.theme_use('PresentationPresenter')
        for kind in ('TFrame', 'TLabelframe', 'TLabelframe.Label', 'TLabel',
                     'TButton', 'TCheckbutton', 'TRadiobutton', 'TEntry', 'TCombobox',
                     'Horizontal.TScrollbar', 'Vertical.TScrollbar'):
            name = 'PP.'+kind
            style.configure(name, background=self.background, foreground=self.foreground,
                            font=self.text, bordercolor='#888888', lightcolor=self.background,
                            darkcolor=self.background, fieldbackground='#eeeeee', padding=3)
            style.map(name, foreground=[('disabled', self.disabled)],
                      background=[('active', self.hover)])
        style.configure('PP.TButton', background=self.panel, font=self.button, relief='flat',
                        borderwidth=1, padding=(6, 4))
        style.map('PP.TButton', background=[('pressed', self.selected), ('active', self.hover)],
                  bordercolor=[('focus', self.focus), ('!focus', self.panel)])
        for kind in ('TEntry', 'TCombobox'):
            style.configure('PP.'+kind, foreground='black', insertcolor='black')
            style.map('PP.'+kind, fieldbackground=[('disabled', '#555555'), ('readonly', '#eeeeee')],
                      foreground=[('disabled', self.disabled), ('!disabled', 'black')],
                      selectbackground=[('!disabled', '#444444')],
                      selectforeground=[('!disabled', 'white')])
        for orientation in ('Horizontal', 'Vertical'):
            style.configure(f'PP.{orientation}.TScrollbar', background=self.panel,
                            troughcolor=self.background, arrowsize=14, borderwidth=0)
        root.configure(background=self.background)
        root._pp_appearance = self
        install_title_bars(root)

    def apply(self, widget):
        """Style a newly built owned dialog, preserving content-canvas colors."""
        kind = widget.winfo_class()
        if isinstance(widget, ttk.Widget):
            if kind == 'TScrollbar':
                kind = ('Horizontal' if str(widget.cget('orient')) == 'horizontal' else 'Vertical')+'.TScrollbar'
            widget.configure(style='PP.'+kind)
            if kind in ('TEntry', 'TCombobox'):
                widget.configure(font=self.text)
        elif kind in self.defaults and kind != 'Canvas':
            options = self.defaults[kind].copy()
            if kind == 'Button' and widget.cget('image'):
                options.pop('font', None)
            widget.configure(**options)
        for child in widget.winfo_children():
            # Projection windows must keep their renderer-owned appearance.
            if not isinstance(child, tk.Toplevel):
                self.apply(child)


def appearance(widget, settings=None):
    root = widget._root()
    return getattr(root, '_pp_appearance', None) or Appearance(root, settings)


def scrollbar(parent, **options):
    """The Windows classic scrollbar ignores most palette options."""
    orientation = 'Horizontal' if options.get('orient') == 'horizontal' else 'Vertical'
    return ttk.Scrollbar(parent, style=f'PP.{orientation}.TScrollbar', **options)
