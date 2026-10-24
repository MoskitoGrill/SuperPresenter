"""Explicit choice when companion tools outlive the main application."""
import tkinter as tk
from tkinter.simpledialog import Dialog


class CloseScopeDialog(Dialog):
    def __init__(self, parent, tools):
        self.tools = tools
        super().__init__(parent, title='Zavřít SuperPresenter')

    def body(self, master):
        tk.Label(master, text='Stále běží: ' + ', '.join(self.tools) + '.\n'
                 'Chcete zavřít vše, nebo jen SuperPresenter?',
                 justify='left', wraplength=430).pack(padx=12, pady=12)

    def buttonbox(self):
        row = tk.Frame(self)
        row.pack(padx=12, pady=(0, 12))
        for label, choice in (('Zavřít vše', 'all'), ('Jen SuperPresenter', 'main'), ('Zrušit', None)):
            button = tk.Button(row, text=label, command=lambda c=choice: self.finish(c))
            button.pack(side='left', padx=4, ipadx=6, ipady=4)
        self.bind('<Escape>', self.cancel)
        self.bind('<Return>', lambda e: self.finish('main'))

    def finish(self, choice):
        self.result = choice
        self.cancel()


def ask_close_scope(parent, tools):
    return CloseScopeDialog(parent, tools).result
