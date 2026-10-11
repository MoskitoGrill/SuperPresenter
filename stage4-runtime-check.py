"""Bounded source soak with isolated fixture data and Windows working set."""
import ctypes
from ctypes import wintypes
import gc
import sys
import time
import unittest

sys.path.insert(0, 'tests')
from test_window_lifecycle import LifecycleTests


class MemoryCounters(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
        (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
        'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
        'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]


def rss():
    counters = MemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.WorkingSetSize


class RuntimeCheck(LifecycleTests):
    def test_bounded_runtime(self):
        self.watch_errors()
        samples = []
        started = time.monotonic()
        for cycle in range(40):
            self.configure_outputs(([0, 1], [2], [3], [4], [5])[cycle % 5])
            self.gui.runButtFun()
            self.assertTrue(self.gui.runState)
            for _ in range(4):
                self.gui.nextStep()
                self.gui.prevStep()
                self.gui.win.update()
            self.gui.runButtFun()
            self.gui.sortSources()
            self.gui.sorter.win.destroy()
            del self.gui.sorter
            self.drain()
            gc.collect()
            self.assertFalse(self.gui.onlineSources)
            self.assertTrue(all(not hasattr(p, 'win') for p in self.gui.projectors))
            self.assertIsNone(getattr(self.gui, '_animation_timer', None))
            samples.append(rss())
            print(f'cycle={cycle + 1} rss_mib={samples[-1] / 1048576:.3f}', flush=True)
        self.assertEqual(self.errors, [])
        self.error.assert_not_called()
        print(f'elapsed_s={time.monotonic() - started:.3f} '
              f'last10_range_mib={(max(samples[-10:]) - min(samples[-10:])) / 1048576:.3f}', flush=True)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([RuntimeCheck('test_bounded_runtime')]))
    sys.exit(not result.wasSuccessful())
