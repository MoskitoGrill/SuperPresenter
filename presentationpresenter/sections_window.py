"""Non-modal source overview; a completed drag is one draft history action."""
import tkinter as tk
from .appearance import scrollbar


def section_label(section):
    return section.title.strip() or section.reference.strip() or 'Bez názvu'


class SectionsWindow:
    def __init__(self, owner):
        self.owner = owner
        self.window = tk.Toplevel(owner.root)
        self.window.title('Zdrojové úseky')
        self.window.geometry('460x540')
        self.window.minsize(320, 280)
        self.window.transient(owner.root)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.drag = None
        self.timer = None
        tk.Label(self.window, text='Vyberte úsek nebo jej přetáhněte na nové místo.',
                 wraplength=400, justify='left').pack(fill='x', padx=12, pady=10)
        frame = tk.Frame(self.window)
        frame.pack(fill='both', expand=True, padx=12)
        self.listbox = tk.Listbox(frame, exportselection=False, activestyle='none')
        scroll = scrollbar(frame, command=self.listbox.yview)
        scroll.pack(side='right', fill='y')
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(fill='both', expand=True)
        self.marker = tk.Frame(self.listbox, bg='#aaaaaa', height=3)
        self.message = tk.StringVar(self.window, value='')
        tk.Label(self.window, textvariable=self.message, anchor='w').pack(fill='x', padx=12, pady=8)
        self.listbox.bind('<ButtonPress-1>', self.press)
        self.listbox.bind('<B1-Motion>', self.motion)
        self.listbox.bind('<ButtonRelease-1>', self.release)
        self.listbox.bind('<KeyRelease-Up>', self.choose)
        self.listbox.bind('<KeyRelease-Down>', self.choose)
        self.listbox.bind('<Return>', self.choose)
        self.window.bind('<Escape>', lambda e: self.cancel())
        self.window.bind('<Destroy>', self.destroyed, add='+')
        owner.appearance.apply(self.window)
        self.marker.configure(bg='#dddddd')
        self.refresh()

    def alive(self):
        try:
            return bool(self.window.winfo_exists())
        except tk.TclError:
            return False

    def cancel(self):
        if self.timer is not None:
            self.window.after_cancel(self.timer)
            self.timer = None
        self.drag = None
        self.message.set(f'Počet úseků: {len(getattr(self, "ids", ()))}')
        try:
            self.marker.place_forget()
        except tk.TclError:
            pass  # Parent destruction may already have destroyed the marker.
        return 'break'

    def destroyed(self, event):
        if event.widget is self.window:
            self.cancel()

    def close(self):
        self.cancel()
        self.window.destroy()

    def refresh(self):
        signature = (tuple((s.id, section_label(s)) for s in self.owner.document.sections), self.owner.selected_id)
        if getattr(self, '_signature', None) == signature:
            return
        self._signature = signature
        self.cancel()
        top = self.listbox.yview()[0]
        self.ids = tuple(s.id for s in self.owner.document.sections)
        self.listbox.delete(0, 'end')
        for i, section in enumerate(self.owner.document.sections):
            self.listbox.insert('end', f'{i+1}. {section_label(section)}')
            if section.id == self.owner.selected_id:
                self.listbox.selection_set(i)
                self.listbox.activate(i)
        self.listbox.yview_moveto(top)
        self.message.set(f'Počet úseků: {len(self.ids)}')

    def press(self, event):
        self.cancel()
        self.owner.finish_editing()
        index = self.listbox.nearest(event.y)
        box = self.listbox.bbox(index)
        if box and box[1] <= event.y < box[1] + box[3]:
            self.listbox.selection_clear(0, 'end')
            self.listbox.selection_set(index)
            self.drag = {'id': self.ids[index], 'ids': self.ids, 'start': event.y,
                         'y': event.y, 'x': event.x, 'moving': False, 'slot': index}
        return 'break'

    def motion(self, event):
        if self.drag:
            self.drag.update(y=event.y, x=event.x)
            if abs(event.y - self.drag['start']) >= 5:
                self.drag['moving'] = True
            self.indicate()
        return 'break'

    def indicate(self):
        if not self.drag or not self.drag['moving']:
            return
        if self.timer is not None:
            self.window.after_cancel(self.timer)
            self.timer = None
        y = self.drag['y']
        height = self.listbox.winfo_height()
        direction = -1 if y < 18 else 1 if y > height - 18 else 0
        if direction:
            self.listbox.yview_scroll(direction, 'units')
            self.timer = self.window.after(90, self.indicate)
        index = self.listbox.nearest(y)
        box = self.listbox.bbox(index)
        if box:
            after = y >= box[1] + box[3]/2
            self.drag['slot'] = index + int(after)
            self.marker.place(x=0, y=box[1] + (box[3] if after else 0), relwidth=1)
            self.message.set(f'Přesunout na pozici {self.drag["slot"] + 1} • pusťte myš')

    def choose(self, event=None):
        chosen = self.listbox.curselection()
        if chosen:
            self.owner.choose_source_section(self.ids[chosen[0]])
        return 'break'

    def release(self, event):
        drag = self.drag
        self.cancel()
        if drag and drag['ids'] == tuple(s.id for s in self.owner.document.sections):
            if drag['moving']:
                if 0 <= event.x < self.listbox.winfo_width() and 0 <= event.y < self.listbox.winfo_height():
                    self.owner.reorder_source_section(drag['id'], drag['slot'])
            else:
                self.owner.choose_source_section(drag['id'])
        self.refresh()
        return 'break'
