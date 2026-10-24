"""Native caption colors for this app's Windows, without custom window buttons."""
import logging
import sys
import tkinter as tk


class TabTitleBar:
    """Tk commands in the caption row; retain Windows' normal resizable frame.

    Unlike overrideredirect, removing only WS_CAPTION retains taskbar presence,
    native resize borders, minimize/maximize and system close handling.
    """
    def __init__(self, root, frame, close, theme):
        self.root, self.frame = root, frame
        self.native = sys.platform == 'win32'
        if not self.native:
            return
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        for name, args, result in (
            ('GetAncestor', [wintypes.HWND, wintypes.UINT], wintypes.HWND),
            ('GetWindowLongW', [wintypes.HWND, ctypes.c_int], wintypes.LONG),
            ('SetWindowLongW', [wintypes.HWND, ctypes.c_int, wintypes.LONG], wintypes.LONG),
            ('SetWindowPos', [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, wintypes.UINT], wintypes.BOOL),
            ('PostMessageW', [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
        ):
            function = getattr(self.user, name)
            function.argtypes, function.restype = args, result
        frame.ribbon_chrome = True
        frame.configure(background=theme.background)
        self.buttons = []
        for label, command in (('×', close), ('□', self.toggle_maximize), ('−', root.iconify)):
            button = tk.Button(frame, text=label, command=command, font=('Segoe UI', 12),
                               bg=theme.background, fg='white', activeforeground='white',
                               activebackground='#c42b1c' if label == '×' else '#707070',
                               relief='flat', borderwidth=0, highlightthickness=0,
                               padx=12, pady=3, takefocus=False, width=2)
            button.pack(side='right', fill='y')
            button.bind('<Enter>', lambda e, b=button: b.configure(bg=b.cget('activebackground')))
            button.bind('<Leave>', lambda e, b=button: b.configure(bg=theme.background))
            self.buttons.append(button)
        self.maximize_button = self.buttons[1]
        self.frame_bounds = []
        frame.bind('<ButtonPress-1>', self.drag)
        frame.bind('<Double-Button-1>', lambda e: self.toggle_maximize())
        root.bind('<Map>', self.realize, add='+')
        root.bind('<Configure>', self.update_state, add='+')

    def hwnd(self):
        return self.user.GetAncestor(self.root.winfo_id(), 2)

    def realize(self, event):
        if event.widget is not self.root:
            return
        hwnd = self.hwnd()
        if not self.frame_bounds or self.frame_bounds[-1].hwnd != hwnd:
            self.frame_bounds.append(WorkAreaBounds(hwnd))
        style = self.user.GetWindowLongW(hwnd, -16)
        if style & 0x00c00000 == 0x00c00000:  # WS_CAPTION = WS_BORDER | WS_DLGFRAME.
            geometry = self.root.geometry()
            # Retain WS_BORDER too: Tk includes it in client-size accounting.
            self.user.SetWindowLongW(hwnd, -16, style & ~0x00400000)
            self.user.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
            self.root.geometry(geometry)

    def update_state(self, event):
        if event.widget is self.root:
            label = '❐' if self.root.state() == 'zoomed' else '□'
            if self.maximize_button.cget('text') != label:
                self.maximize_button.configure(text=label)

    def toggle_maximize(self):
        self.root.state('normal' if self.root.state() == 'zoomed' else 'zoomed')

    def drag(self, event):
        self.user.ReleaseCapture()
        # Do not synchronously enter Tk's native move loop from a Python/Tcl
        # binding: that re-enters Tcl through ctypes while its callback runs.
        self.user.PostMessageW(self.hwnd(), 0x00a1, 2, 0)  # WM_NCLBUTTONDOWN / HTCAPTION.
        return 'break'


class WorkAreaBounds:
    """Constrain captionless maximize to the current monitor's work area.

    The native callback uses only Win32 calls and memory, never Tk/Tcl.
    Keep it alive until the HWND has received WM_NCDESTROY.
    """
    def __init__(self, hwnd):
        import ctypes
        from ctypes import wintypes
        self.hwnd = hwnd
        user = ctypes.WinDLL('user32', use_last_error=True)
        pointer_api = 'WindowLongPtrW' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'WindowLongW'
        setter = getattr(user, 'Set'+pointer_api)
        setter.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        setter.restype = ctypes.c_void_p
        caller = user.CallWindowProcW
        caller.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        caller.restype = ctypes.c_ssize_t
        user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user.MonitorFromWindow.restype = wintypes.HANDLE
        user.IsZoomed.argtypes = [wintypes.HWND]
        user.IsZoomed.restype = wintypes.BOOL

        class MonitorInfo(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                        ('work', wintypes.RECT), ('flags', wintypes.DWORD)]

        class MinMaxInfo(ctypes.Structure):
            _fields_ = [(name, wintypes.POINT) for name in
                        ('reserved', 'max_size', 'max_position', 'min_track', 'max_track')]

        user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
        user.GetMonitorInfoW.restype = wintypes.BOOL
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                                          wintypes.WPARAM, wintypes.LPARAM)

        def procedure(handle, message, wparam, lparam):
            if user.IsZoomed(handle):
                if message == 0x0085:  # WM_NCPAINT: no non-client frame in maximized mode.
                    return 0
                if message == 0x0086:  # WM_NCACTIVATE: retain activation, suppress frame paint.
                    return caller(self.original, handle, message, wparam, -1)
            # Retain the proposed outer rectangle before Tk subtracts the
            # resize frame. In maximized mode that frame must not sit inside
            # the work area as an unpainted black gutter.
            maximized_client = None
            if message == 0x0083 and lparam and user.IsZoomed(handle):  # WM_NCCALCSIZE
                area = ctypes.cast(lparam, ctypes.POINTER(wintypes.RECT)).contents
                maximized_client = (area.left, area.top, area.right, area.bottom)
            if message == 0x0082:  # WM_NCDESTROY: restore before Tk retires HWND.
                setter(handle, -4, self.original)
            result = caller(self.original, handle, message, wparam, lparam)
            if maximized_client is not None:
                area = ctypes.cast(lparam, ctypes.POINTER(wintypes.RECT)).contents
                area.left, area.top, area.right, area.bottom = maximized_client
                return 0
            if message == 0x0024 and lparam:  # WM_GETMINMAXINFO
                info = MonitorInfo()
                info.size = ctypes.sizeof(info)
                monitor = user.MonitorFromWindow(handle, 2)
                if user.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    bounds = ctypes.cast(lparam, ctypes.POINTER(MinMaxInfo)).contents
                    bounds.max_position.x = info.work.left-info.monitor.left
                    bounds.max_position.y = info.work.top-info.monitor.top
                    bounds.max_size.x = info.work.right-info.work.left
                    bounds.max_size.y = info.work.bottom-info.work.top
            return result

        self.callback = callback_type(procedure)
        ctypes.set_last_error(0)
        self.original = setter(hwnd, -4, ctypes.cast(self.callback, ctypes.c_void_p))
        error = ctypes.get_last_error()
        if error:
            raise ctypes.WinError(error)


def style_title_bar(window):
    if sys.platform != 'win32' or window.overrideredirect():
        return
    try:
        import ctypes
        from ctypes import wintypes

        user = ctypes.WinDLL('user32', use_last_error=True)
        user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user.GetAncestor.restype = wintypes.HWND
        hwnd = user.GetAncestor(window.winfo_id(), 2)  # GA_ROOT: Tk's native wrapper.
        if not hwnd:
            return
        dwm = ctypes.WinDLL('dwmapi')
        setter = dwm.DwmSetWindowAttribute
        setter.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        setter.restype = ctypes.c_long
        red, green, blue = (value // 257 for value in window.winfo_rgb(window.cget('background')))
        dark = .2126*red + .7152*green + .0722*blue < 128
        caption = red | (green << 8) | (blue << 16)
        for attribute, value in ((20, int(dark)), (35, caption), (36, 0xffffff if dark else 0x202020)):
            color = wintypes.DWORD(value)
            result = setter(hwnd, attribute, ctypes.byref(color), ctypes.sizeof(color))
            if result < 0:
                # Older Windows may support dark mode but not explicit colors.
                logging.getLogger(__name__).debug('DWM caption attribute %s unavailable: 0x%08x',
                                                   attribute, result & 0xffffffff)
    except (OSError, tk.TclError):
        logging.getLogger(__name__).exception('PresentationPresenter caption styling failed')


def install_title_bars(root):
    """Map runs after native realization; also covers new dialogs and restores.

    Bindings live only in this app's Tcl interpreter. Borderless suggestions
    and fullscreen projection windows keep their original behavior.
    """
    if sys.platform != 'win32':
        return

    def mapped(event):
        if event.widget is root or isinstance(event.widget, tk.Toplevel):
            style_title_bar(event.widget)

    root.bind('<Map>', mapped, add='+')
    root.bind_class('Toplevel', '<Map>', mapped, add='+')
    if root.winfo_ismapped():
        style_title_bar(root)
