"""Native caption colors for this app's Windows, without custom window buttons."""
import logging
import sys
import tkinter as tk


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
