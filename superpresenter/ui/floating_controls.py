"""Optional always-on-top presentation remote; reads the running snapshot."""
import tkinter as tk

from superpresenter.services.stationary_navigation import CueNavigation, style_mode
from superpresenter.windows_shell import style_title_bar


def next_position(nav, direction, stream):
    """Find the next visible page without changing the live navigation."""
    target = CueNavigation(nav.plans)
    target.select(nav.song, nav.step)
    page = nav.cue.hall_page if nav.cue else None
    target.move(direction)
    if not stream and page is not None:
        while target.cue and target.cue.hall_page is page and target.song == nav.song:
            before = (target.song, target.step)
            target.move(direction)
            if before == (target.song, target.step):
                break
    if not stream and target.cue:
        # Land on the first cue of a hall page, also when moving backwards.
        page = target.cue.hall_page
        while target.step > 1 and target.plans[target.song].cues[target.step - 2].hall_page is page:
            target.step -= 1
    return target


class FloatingControls:
    def __init__(self, gui):
        self.gui = gui
        self.timer = None
        self.win = tk.Toplevel(gui.win)
        self.win.bind('<Destroy>', self._destroyed, add='+')
        self.win.title('Plovoucí ovládání')
        # Do not use transient(): the remote must survive minimising the owner.
        self.win.attributes('-topmost', True)
        self.win.protocol('WM_DELETE_WINDOW', self.close)
        background = gui.win.cget('background')
        self.win.configure(background=background)
        row = tk.Frame(self.win, background=background)
        row.pack(anchor='w', padx=4, pady=(4, 2))
        # Copy the actual screen selector button, including pixel padding.
        button_style = {key: gui.prevProj.cget(key) for key in (
            'width', 'height', 'font', 'padx', 'pady', 'borderwidth',
            'highlightthickness', 'relief', 'background', 'foreground',
            'activebackground', 'activeforeground', 'disabledforeground')}
        self.buttons = []
        for column, (label, command) in enumerate((
                ('<<', lambda: self.boundary(False)),
                ('<', lambda: self.move(-1)),
                ('▶', self.toggle),
                ('>', lambda: self.move(1)),
                ('>>', lambda: self.boundary(True)))):
            button = tk.Button(row, text=label, command=command, **button_style)
            button.grid(row=0, column=column, padx=2)
            if column == 2:
                self.run = button
            else:
                self.buttons.append(button)
        row.update_idletasks()
        width = row.winfo_reqwidth() + 8
        preview_style = dict(background=background,
                             foreground=gui.stepsList.cget('foreground'),
                             font=gui.stepsList.cget('font'),
                             anchor='w', justify='left', wraplength=width - 16)
        self.current = tk.Label(self.win, **preview_style)
        self.current.pack(fill='x', padx=8, pady=4)
        self.separator = tk.Frame(self.win, background='#bbbbbb', height=1)
        self.separator.pack(fill='x', padx=8)
        self.following = tk.Label(self.win, **preview_style)
        self.following.pack(fill='x', padx=8, pady=4)
        self.win.minsize(width, 1)
        self.win.bind('<Configure>', self.resize)
        self.refresh()
        style_title_bar(self.win)

    def resize(self, event):
        if event.widget is self.win:
            for label in (self.current, self.following):
                label.configure(wraplength=max(1, event.width - 16))

    def stream(self):
        return any(style_mode(self.gui.projStyles[p.style]) == 'stationary_stream'
                   for p in self.gui.projectors)

    def ready(self):
        return self.gui.runState and bool(self.gui.onlineSources)

    def move(self, direction):
        if not self.ready():
            return
        nav = getattr(self.gui, 'stationary_navigation', None)
        if nav is not None:
            target = next_position(nav, direction, self.stream())
            nav.select(target.song, target.step)
            self.gui._sync_stationary_navigation()
        else:
            (self.gui.nextStep if direction > 0 else self.gui.prevStep)()
        self.refresh()

    def boundary(self, end):
        if not self.ready():
            return
        gui = self.gui
        nav = getattr(gui, 'stationary_navigation', None)
        if nav is not None:
            nav.select(nav.song, nav.last_step if end else 0)
            gui._sync_stationary_navigation()
        else:
            gui.currentStep = gui.noOfSteps if end else 0
            gui.stepsList.selection_clear(0, 'end')
            gui.stepsList.selection_set(gui.currentStep)
            gui.stepUpdate()
            gui.stepGoTo(0)
        self.refresh()

    def toggle(self):
        self.gui.runButtFun()
        self.refresh()

    def refresh(self):
        if self.timer is not None:
            self.win.after_cancel(self.timer)
        gui = self.gui
        active = self.ready()
        for button in self.buttons:
            button.configure(state='normal' if active else 'disabled')
        self.run.configure(text='■' if gui.runState else '▶')
        current, following = '', ''
        if active:
            nav = getattr(gui, 'stationary_navigation', None)
            if nav is not None:
                stream = self.stream()
                target = next_position(nav, 1, stream)
                page = (nav.cue.stream_page if stream else nav.cue.hall_page) if nav.cue else None
                upcoming = (target.cue.stream_page if stream else target.cue.hall_page) if target.cue else None
                current = page.lines[-1].text if page and page.lines else ''
                following = upcoming.lines[0].text if upcoming and upcoming.lines else ''
                if target.song == nav.song and target.step == nav.step:
                    following = ''
        self.current.configure(text=current)
        self.following.configure(text=following)
        self.timer = self.win.after(150, self.refresh)

    def close(self):
        self.win.destroy()

    def _destroyed(self, event):
        if event.widget is not self.win:
            return
        if self.timer is not None:
            self.win.after_cancel(self.timer)
            self.timer = None
        self.gui.floating_controls = None
