"""Invalidate only our workspace and native children after geometry changes."""
import sys

if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    _redraw = ctypes.WinDLL('user32', use_last_error=True).RedrawWindow
    _redraw.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    _redraw.restype = wintypes.BOOL


def repaint_workspace(widget):
    if sys.platform != 'win32':
        return
    # RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW.
    # Real WM_PAINT invalidation also clears the space vacated by moved children;
    # a synthetic Expose on the child alone cannot invalidate that old area.
    _redraw(widget.winfo_id(), None, None, 0x0001 | 0x0004 | 0x0080 | 0x0100)
