"""Capture owned calibration windows only, after Windows mapping animation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import ImageGrab
from presentationpresenter.projection import configure_dpi
from presentationpresenter.camera_settings_window import CameraSettingsWindow
from tests.presentationpresenter.test_camera_settings import CameraSettingsTests

def main():
    configure_dpi()
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    test = CameraSettingsTests()
    test.setUp()
    try:
        dialog = CameraSettingsWindow(test.w)
        def capture(window, name):
            window.attributes('-topmost', True)
            window.lift()
            window.update()
            window.after(600, window.quit)
            window.mainloop()
            import ctypes
            from ctypes import wintypes
            class Point(ctypes.Structure):
                _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]
            user = ctypes.windll.user32
            user.WindowFromPoint.argtypes = [Point]
            user.WindowFromPoint.restype = wintypes.HWND
            user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
            user.GetAncestor.restype = wintypes.HWND
            expected = user.GetAncestor(window.winfo_id(), 2)
            actual = user.GetAncestor(user.WindowFromPoint(Point(window.winfo_rootx()+10, window.winfo_rooty()+10)), 2)
            assert actual == expected, 'QA window is occluded'
            ImageGrab.grab(bbox=(window.winfo_rootx(), window.winfo_rooty(),
                                window.winfo_rootx()+window.winfo_width(), window.winfo_rooty()+window.winfo_height())).save(output/name)
            window.attributes('-topmost', False)
            print(name, window.winfo_width(), window.winfo_height())
        dialog.window.geometry('900x760+30+30')
        capture(dialog.window, 'camera-settings.png')
        dialog.window.geometry('720x630+30+30')
        capture(dialog.window, 'camera-settings-small.png')
        assert dialog.canvas.winfo_height() > 50
        dialog.fullscreen.set(False)
        dialog.toggle_test()
        assert dialog.test is not None
        capture(dialog.test.window, 'camera-test-output.png')
        dialog.close()
    finally:
        test.tearDown()

if __name__ == '__main__':
    main()
