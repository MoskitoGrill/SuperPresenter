"""Launch companion tools in source and standalone distributions."""
from pathlib import Path
import sys

from superpresenter.paths import PROJECT_ROOT


def tool_command(script):
    flags = {'presentation_presenter.py': '--presentation-editor',
             'presentation_presenter_v2.py': '--presentation-editor',
             'presentation_bible.py': '--bible',
             'oprava_xml_tagu.py': '--repair-xml'}
    if script not in flags:
        raise ValueError('Unknown companion tool: ' + script)
    if getattr(sys, 'frozen', False):
        return [sys.executable, flags[script]]
    return [sys.executable, str(Path(PROJECT_ROOT) / script)]


def _process_family(pid):
    """Include interpreter/EXE launcher children without searching unrelated apps."""
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t),
                    ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG),
                    ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ('Process32FirstW', 'Process32NextW'):
        function = getattr(kernel, name)
        function.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
        function.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS
    family = {pid}
    if snapshot == ctypes.c_void_p(-1).value:
        return family
    parents = {}
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            parents[entry.th32ProcessID] = entry.th32ParentProcessID
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    while True:
        children = {child for child, parent in parents.items() if parent in family} - family
        if not children:
            return family
        family.update(children)


def request_tool_close(process, title_prefix):
    """Ask this child's main window to close, preserving its save/cancel flow."""
    if process.poll() is not None:
        return True
    import os
    if os.name != 'nt':
        return False
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    family = _process_family(process.pid)
    windows = []

    @callback_type
    def visit(hwnd, unused):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in family:
            title = ctypes.create_unicode_buffer(1024)
            user32.GetWindowTextW(hwnd, title, len(title))
            if title.value.startswith(title_prefix):
                windows.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    if process.poll() is not None:
        return True
    return bool(windows and user32.PostMessageW(windows[0], 0x0010, 0, 0))
