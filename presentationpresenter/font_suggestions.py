"""Font name suggestions that keep keyboard focus in the editable combobox."""
import tkinter as tk


class FontSuggestions:
    def __init__(self, root, field, variable, names, apply, cancel, theme):
        self.root, self.field, self.variable = root, field, variable
        self.names = tuple(sorted(names, key=str.casefold))
        self.apply, self.cancel = apply, cancel
        self.popup = tk.Toplevel(root)
        self.popup.withdraw()
        self.popup.overrideredirect(True)
        self.popup.transient(root)
        self.items = tk.Listbox(self.popup, exportselection=False, takefocus=False,
            font=theme.text, bg=theme.field, fg=theme.foreground,
            selectbackground=theme.selected, selectforeground=theme.foreground,
            relief='solid', borderwidth=1, highlightthickness=0)
        scroll = tk.Scrollbar(self.popup, command=self.items.yview, takefocus=False)
        self.items.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.items.pack(fill='both', expand=True)
        self.items.bind('<ButtonPress-1>', self.press)
        self.items.bind('<ButtonRelease-1>', lambda e: self.choose())
        field.bind('<KeyRelease>', self.changed, add='+')
        field.bind('<Down>', lambda e: self.move(1))
        field.bind('<Up>', lambda e: self.move(-1))
        field.bind('<Return>', self.enter)
        field.bind('<Escape>', self.escape)
        field.bind('<FocusOut>', lambda e: self.hide(), add='+')
        field.bind('<Unmap>', lambda e: self.hide(), add='+')
        field.bind('<Configure>', lambda e: self.position() if self.visible() else None, add='+')
        field.bind('<ButtonPress-1>', self.field_press, add='+')
        root.bind('<ButtonPress-1>', self.dismiss, add='+')
        root.bind('<Configure>', self.reposition, add='+')
        root.bind('<Unmap>', lambda e: self.hide() if e.widget is root else None, add='+')

    def visible(self):
        return bool(self.popup.winfo_ismapped())

    def hide(self):
        self.popup.withdraw()

    def changed(self, event):
        if event.state & (0x4 | 0x8 | 0x20000) or event.keysym in ('Up', 'Down', 'Return', 'Escape', 'Tab', 'Shift_L', 'Shift_R'):
            return
        query = self.variable.get().strip().casefold()
        matches = [n for n in self.names if n.casefold().startswith(query)] if query else []
        matches += [n for n in self.names if query and query in n.casefold() and not n.casefold().startswith(query)]
        self.items.delete(0, 'end')
        for name in matches:
            self.items.insert('end', name)
        if not matches:
            self.hide()
            return
        self.select(0)
        self.position()
        self.popup.deiconify()
        self.popup.lift()

    def position(self):
        height = min(6, self.items.size()) * int(self.items.tk.call('font', 'metrics', self.items.cget('font'), '-linespace'))+4
        width = max(240, self.field.winfo_width())
        x = self.field.winfo_rootx()
        y = self.field.winfo_rooty()+self.field.winfo_height()
        if y+height > self.root.winfo_screenheight():
            y = self.field.winfo_rooty()-height
        self.popup.geometry(f'{width}x{height}{x:+d}{y:+d}')

    def reposition(self, event):
        if event.widget is self.root and self.visible():
            if self.field.winfo_viewable():
                self.position()
            else:
                self.hide()

    def select(self, index):
        self.items.selection_clear(0, 'end')
        self.items.selection_set(index)
        self.items.activate(index)
        self.items.see(index)

    def move(self, direction):
        if not self.visible():
            return  # Retain the native full combobox menu when no suggestions.
        selection = self.items.curselection()
        self.select(max(0, min(self.items.size()-1, (selection[0] if selection else 0)+direction)))
        return 'break'

    def choose(self):
        selection = self.items.curselection()
        if selection:
            self.variable.set(self.items.get(selection[0]))
            self.hide()
            self.apply()
        return 'break'

    def enter(self, event=None):
        if self.visible():
            return self.choose()
        return self.apply(event)

    def escape(self, event=None):
        if self.visible():
            self.hide()
            return 'break'
        return self.cancel(event)

    def press(self, event):
        if self.items.size():
            self.select(self.items.nearest(event.y))
        return 'break'  # Do not let Listbox's class binding take the field focus.

    def field_press(self, event):
        if 'arrow' in self.field.identify(event.x, event.y):
            self.hide()

    def dismiss(self, event):
        if event.widget is not self.field:
            self.hide()
