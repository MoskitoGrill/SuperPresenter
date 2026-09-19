"""Windows taskbar identity and relaunch target for the source-based application."""
import ctypes
import logging
import os
import sys
import subprocess
from pathlib import Path
import uuid

from superpresenter.paths import PROJECT_ROOT


def configure_window(window):
    if os.name != 'nt':
        return
    root = Path(PROJECT_ROOT)
    icon = root / 'images' / 'ikona.ico'
    if not icon.is_file():
        icon = root / 'images' / 'launcher-default.ico'
    try:
        if icon.is_file():
            window.iconbitmap(str(icon))
    except Exception:
        logging.getLogger(__name__).exception('Windows icon setup failed')
        icon = root / 'images' / 'launcher-default.ico'
    try:
        window.update_idletasks()
        _set_properties(window.winfo_id(), root, icon)
    except Exception:
        logging.getLogger(__name__).exception('Windows taskbar setup failed')


def _set_properties(tk_handle, root, icon):
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [('data', ctypes.c_ubyte * 16)]

        @classmethod
        def parse(cls, text):
            return cls.from_buffer_copy(uuid.UUID(text).bytes_le)

    class PROPERTYKEY(ctypes.Structure):
        _fields_ = [('fmtid', GUID), ('pid', wintypes.DWORD)]

    class Value(ctypes.Union):
        # PROPVARIANT's union contains a counted array (ULONG + pointer).
        _fields_ = [('text', ctypes.c_wchar_p),
                    ('storage', ctypes.c_ubyte * (16 if ctypes.sizeof(ctypes.c_void_p) == 8 else 8))]

    class PROPVARIANT(ctypes.Structure):
        _fields_ = [('vt', ctypes.c_ushort), ('reserved', ctypes.c_ushort * 3),
                    ('value', Value)]

    def checked(result):
        if result < 0:
            raise OSError('Windows Shell HRESULT 0x%08x' % (result & 0xffffffff))

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    handle = user32.GetAncestor(tk_handle, 2)  # Tk's outer top-level HWND.
    shell32 = ctypes.WinDLL('shell32')
    get_store = shell32.SHGetPropertyStoreForWindow
    get_store.argtypes = [wintypes.HWND, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    get_store.restype = ctypes.c_long
    store = ctypes.c_void_p()
    iid = GUID.parse('886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99')
    checked(get_store(handle, ctypes.byref(iid), ctypes.byref(store)))
    table = ctypes.cast(store, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    set_value = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                  ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT))(table[6])
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[2])
    fmtid = GUID.parse('9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3')
    try:
        # Set relaunch information before the explicit ID, as required by Shell.
        command = ([sys.executable] if getattr(sys, 'frozen', False) else
                   [sys.executable, str(root / 'super_presenter.py')])
        values = [(2, subprocess.list2cmdline(command)),
                  (4, 'SuperPresenter'), (3, str(icon) + ',0'),
                  (5, 'SuperPresenter.Desktop')]
        for pid, text in values:
            key = PROPERTYKEY(fmtid, pid)
            value = PROPVARIANT()
            value.vt = 31  # VT_LPWSTR; Python owns the string during SetValue.
            value.value.text = text
            checked(set_value(store, ctypes.byref(key), ctypes.byref(value)))
    finally:
        release(store)
