"""Shared dark scrollbars matching the QR editor's sliders."""
from tkinter import ttk
from superpresenter.ui.mousewheel import scroll_widget


class Scrollbar(ttk.Scrollbar):
    def __init__(self, master, **kwargs):
        theme = ttk.Style(master)
        if theme.theme_use() != 'clam':
            theme.theme_use('clam')
        orient = str(kwargs.get('orient', 'vertical')).capitalize()
        name = f'App.{orient}.TScrollbar'
        theme.configure(name, background='#444444', troughcolor='#666666',
                        bordercolor='#555555', lightcolor='#666666',
                        darkcolor='#444444', borderwidth=0, arrowsize=14)
        theme.map(name, background=[('pressed', '#666666'), ('active', '#666666')])
        # Keep the track and draggable thumb, like the QR setting sliders.
        theme.layout(name, [(f'{orient}.Scrollbar.trough', {
            'sticky': 'nswe', 'children': [(f'{orient}.Scrollbar.thumb', {
                'expand': '1', 'sticky': 'nswe'})]})])
        kwargs['style'] = name
        super().__init__(master, **kwargs)
        target = getattr(kwargs.get('command'), '__self__', None)
        if target is not None and hasattr(target, 'yview_scroll'):
            self.bind('<MouseWheel>', lambda event: scroll_widget(
                target, event, horizontal=orient == 'Horizontal'))
