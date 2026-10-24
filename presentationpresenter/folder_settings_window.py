"""Local file-dialog defaults; no changes to presentation contents."""
import tkinter as tk
from tkinter import filedialog, messagebox
from dataclasses import replace
from pathlib import Path
from .settings import FOLDER_LABELS, validate_directories, save_settings

class FolderSettingsWindow:
    def __init__(self, owner):
        self.owner = owner
        self.window = tk.Toplevel(owner.root)
        self.window.title('Výchozí složky')
        self.window.transient(owner.root)
        self.window.resizable(True, False)
        self.window.columnconfigure(1, weight=1)
        self.values = {}
        for row, (field, label) in enumerate(FOLDER_LABELS.items()):
            tk.Label(self.window, text=label, anchor='w').grid(row=row, column=0, sticky='w', padx=10, pady=6)
            value = tk.StringVar(value=getattr(owner.settings, field))
            self.values[field] = value
            tk.Entry(self.window, textvariable=value, width=40).grid(row=row, column=1, sticky='ew', pady=6)
            tk.Button(self.window, text='Vybrat…', command=lambda f=field: self.browse(f)).grid(row=row, column=2, padx=10, pady=6)
        tk.Label(self.window, text='Prázdné pole použije složku presentation vedle aplikace.', justify='left').grid(
            row=4, column=0, columnspan=3, sticky='w', padx=10, pady=8)
        actions = tk.Frame(self.window)
        actions.grid(row=5, column=0, columnspan=3, sticky='e', padx=10, pady=10)
        tk.Button(actions, text='Zrušit', command=self.window.destroy).pack(side='left', padx=6)
        self.save_button = tk.Button(actions, text='Uložit', command=self.save)
        self.save_button.pack(side='left')
        owner.appearance.apply(self.window)
        self.window.bind('<Escape>', lambda e: self.window.destroy())
        self.window.grab_set()

    def browse(self, field):
        current = self.values[field].get().strip()
        try:
            directory = Path(current) if current and Path(current).is_absolute() and Path(current).is_dir() else None
        except (OSError, ValueError):
            directory = None
        if directory is None:
            directory = self.owner.file_dialog_directory(field.removesuffix('_directory'))
        if directory is None:
            return
        selected = filedialog.askdirectory(parent=self.window, title=FOLDER_LABELS[field], initialdir=str(directory), mustexist=True)
        if selected:
            self.values[field].set(selected)

    def save(self):
        values = {field: var.get().strip() for field, var in self.values.items()}
        try:
            validate_directories(values, require_existing=True)
            updated = replace(self.owner.settings, **values)
            save_settings(updated)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Výchozí složky', str(exc), parent=self.window)
            return
        self.owner.settings = updated
        self.owner.status.set('Výchozí složky uloženy.')
        self.window.destroy()
