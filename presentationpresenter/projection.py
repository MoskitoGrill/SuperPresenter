"""Monitor discovery and independent windows for a shared confirmed session."""
import sys
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import tkinter as tk
from .layout import geometry
from .rendering import draw


def configure_dpi():
    """Call before creating Tk: use physical pixels on every Windows monitor."""
    if sys.platform != 'win32':
        return
    user = ctypes.windll.user32
    try:
        setter = user.SetProcessDpiAwarenessContext
        setter.argtypes = [ctypes.c_void_p]
        setter.restype = wintypes.BOOL
        if setter(ctypes.c_void_p(-4)):
            return
        # An executable manifest may already have selected DPI awareness.
        if user.GetThreadDpiAwarenessContext:
            get_context = user.GetThreadDpiAwarenessContext
            get_context.restype = ctypes.c_void_p
            get_awareness = user.GetAwarenessFromDpiAwarenessContext
            get_awareness.argtypes = [ctypes.c_void_p]
            if get_awareness(get_context()) == 2:
                return
        raise RuntimeError('Nelze zapnout DPI režim pro každý monitor. Spusťte aplikaci v novém procesu před vytvořením oken.')
    except AttributeError:
        # Windows 8.1 fallback; Windows 10+ uses Per Monitor V2 above.
        setter = ctypes.windll.shcore.SetProcessDpiAwareness
        setter.argtypes = [ctypes.c_int]
        if setter(2) != 0:
            raise RuntimeError('Nelze zapnout DPI režim projekce.')


@dataclass(frozen=True)
class Monitor:
    id: str
    x: int
    y: int
    width: int
    height: int
    is_primary: bool = False

    @property
    def label(self):
        return monitor_labels([self])[0]


def monitor_labels(inventory):
    """Same coordinate-based naming rules as SuperPresenter, without UI imports."""
    if not inventory:
        return []
    primary = next((i for i, m in enumerate(inventory) if m.is_primary),
                   next((i for i, m in enumerate(inventory) if (m.x, m.y) == (0, 0)), 0))
    origin = inventory[primary]
    groups, directions = {}, []
    for i, monitor in enumerate(inventory):
        if i == primary:
            direction = 'Hlavní'
        else:
            horizontal = 'Vlevo' if monitor.x < origin.x else 'Vpravo' if monitor.x > origin.x else ''
            vertical = 'nahoře' if monitor.y < origin.y else 'dole' if monitor.y > origin.y else ''
            direction = ' '.join(p for p in (horizontal, vertical) if p).capitalize() or 'Stejná pozice'
        directions.append(direction)
        groups.setdefault(direction, []).append(i)
    labels = []
    for i, monitor in enumerate(inventory):
        direction = directions[i]
        group = sorted(groups[direction], key=lambda idx: (inventory[idx].x, inventory[idx].y, idx))
        suffix = ''
        if len(group) > 1:
            axis = 'zleva' if direction.startswith(('Vlevo', 'Vpravo')) else 'shora'
            suffix = f' – {group.index(i)+1}. {axis}'
        labels.append(f'{direction}{suffix} ({monitor.x}, {monitor.y})')
    return labels


def monitors(root):
    if sys.platform != 'win32':
        return [Monitor('primary', 0, 0, root.winfo_screenwidth(), root.winfo_screenheight())]
    class Info(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('rect', wintypes.RECT),
                    ('work', wintypes.RECT), ('flags', wintypes.DWORD),
                    ('device', wintypes.WCHAR * 32)]
    result = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
                                      ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    user = ctypes.windll.user32
    user.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), callback_type, wintypes.LPARAM]
    user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Info)]
    def collect(handle, dc, rect, data):
        info = Info()
        info.size = ctypes.sizeof(info)
        if user.GetMonitorInfoW(handle, ctypes.byref(info)):
            r = info.rect
            result.append(Monitor(info.device, r.left, r.top, r.right-r.left, r.bottom-r.top, bool(info.flags & 1)))
        return True
    if not user.EnumDisplayMonitors(None, None, callback_type(collect), 0) or not result:
        raise RuntimeError('Monitory se nepodařilo načíst.')
    return result


class ProjectionWindow:
    def __init__(self, owner, output, monitor, fullscreen=True):
        self.owner, self.output, self.monitor = owner, output, monitor
        self.fullscreen = fullscreen
        self.window = tk.Toplevel(owner.root)
        self.window.withdraw()
        self.window.title('PresentationPresenter — '+('Sál' if output == 'hall' else 'Stream'))
        self.window.overrideredirect(fullscreen)
        self.canvas = tk.Canvas(self.window, bg='black', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        # Tk negative offsets mean distance from the right/bottom, not virtual coordinates.
        # MoveWindow uses signed virtual desktop coordinates directly.
        width, height, x, y = monitor.width, monitor.height, monitor.x, monitor.y
        if not fullscreen:
            width, height = min(800, max(1, int(width*.65))), min(600, max(1, int(height*.65)))
            offset = 24 if output == 'hall' else 64
            x += min(offset, max(0, monitor.width-width))
            y += min(offset, max(0, monitor.height-height))
        self.window.geometry(f'{width}x{height}+0+0')
        # Realize Tk's wrapper before native placement. Mapping a withdrawn
        # window afterwards can restore Tk's cached +0+0 geometry over MoveWindow.
        self.window.deiconify()
        self.window.update_idletasks()
        if sys.platform == 'win32':
            user = ctypes.windll.user32
            user.GetParent.argtypes = [wintypes.HWND]
            user.GetParent.restype = wintypes.HWND
            user.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, wintypes.BOOL]
            hwnd = user.GetParent(self.window.winfo_id()) or self.window.winfo_id()
            if not user.MoveWindow(hwnd, x, y, width, height, True):
                self.window.destroy()
                raise RuntimeError('Projekční okno se nepodařilo umístit.')
        else:
            self.window.geometry(f'{width}x{height}{x:+d}{y:+d}')
        self.window.protocol('WM_DELETE_WINDOW', lambda: owner.stop_projection(output))
        self.window.bind('<Escape>', lambda e: owner.stop_projection(output))
        self.window.bind('<KeyPress-b>', owner.blackout_key)
        self.window.bind('<KeyPress-B>', owner.blackout_key)
        self.window.bind('<Destroy>', self.destroyed)
        self.canvas.bind('<Configure>', lambda e: self.render())
        self.window.update_idletasks()
        self.render()

    def destroyed(self, event):
        if event.widget is self.window:
            self.owner.projection_destroyed(self.output, self)

    def render(self):
        session = self.owner.session
        self.canvas.delete('all')
        if not session or session.blackout or session.current_slide_id is None:
            return
        slide = next(s for s in session.plan.slides if s.id == session.current_slide_id)
        width, height, _, _ = geometry(getattr(session.plan.source, self.output))
        scale = min(max(1, self.canvas.winfo_width())/width,
                    max(1, self.canvas.winfo_height())/height)
        draw(self.canvas, slide, self.output, self.owner.metrics, self.owner.typography,
             show_camera=False, scale=scale, resize_canvas=False)
        self.canvas.move('all', (self.canvas.winfo_width()-width*scale)/2,
                         (self.canvas.winfo_height()-height*scale)/2)
