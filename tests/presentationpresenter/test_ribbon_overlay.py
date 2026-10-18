"""Collapsed ribbon can open temporarily without moving the workspace."""
import tkinter as tk
import unittest
from types import SimpleNamespace

from presentationpresenter.ribbon import Ribbon, command_group, wrap_row


class RibbonOverlayTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry('900x600')
        chrome = tk.Frame(self.root)
        chrome.pack(fill='x')
        self.ribbon = Ribbon(chrome, temporary_tabs=True)
        for name in ('Home', 'Settings'):
            tk.Button(self.ribbon.add(name), text='Command').pack()
        self.ribbon.content.configure(height=90)
        self.body = tk.Frame(self.root)
        self.body.pack(fill='both', expand=True)
        self.ribbon.show('Home')
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_overlay_switch_dismiss_and_pin(self):
        r = self.ribbon
        r.toggle()
        self.root.update()
        y = self.body.winfo_y()
        r.buttons['Settings'].invoke()
        self.root.update()
        self.assertTrue(r.temporary_open)
        self.assertFalse(r.expanded)
        self.assertEqual(r.content.winfo_manager(), 'place')
        self.assertEqual(self.body.winfo_y(), y)
        r.outside_click(SimpleNamespace(widget=r.panels['Settings']))
        self.assertTrue(r.temporary_open)
        r.buttons['Home'].invoke()
        self.assertEqual(r.current, 'Home')
        r.outside_click(SimpleNamespace(widget=self.body))
        self.assertFalse(r.temporary_open)
        r.show('Settings')
        r.toggle()
        self.root.update()
        self.assertTrue(r.expanded)
        self.assertFalse(r.temporary_open)
        self.assertEqual(r.content.winfo_manager(), 'pack')

    def test_legacy_mode_and_escape(self):
        r = self.ribbon
        r.toggle()
        r.show('Home')
        self.root.focus_force()
        self.root.update()
        self.root.event_generate('<Escape>')
        self.root.update()
        self.assertFalse(r.temporary_open)
        r.set_temporary_tabs(False)
        r.show('Settings')
        self.assertTrue(r.expanded)
        self.assertEqual(r.content.winfo_manager(), 'pack')

    def test_groups_scroll_in_one_row_and_focus_reveals_command(self):
        r = self.ribbon
        panel = r.add('Wide')
        buttons = []
        for index in range(8):
            group = command_group(panel, f'Group {index}')
            button = tk.Button(group, text='Long command '+str(index))
            button.pack()
            buttons.append(button)
        wrap_row(panel, stretch_groups=True)
        r.reserve_height([lambda width: panel.wrapped_height(width)+8])
        r.show('Wide')
        self.root.update()
        height = r.content.winfo_height()
        self.assertTrue(r.scrollbar.winfo_ismapped())
        self.assertEqual(len({child.winfo_y() for child in panel.winfo_children()}), 1)
        self.root.geometry('500x600')
        self.root.update()
        self.assertEqual(r.content.winfo_height(), height)
        buttons[-1].focus_force()
        self.root.update()
        self.assertGreater(r.viewport.xview()[0], 0)
        self.assertLessEqual(buttons[-1].winfo_rootx()+buttons[-1].winfo_width(),
                             r.viewport.winfo_rootx()+r.viewport.winfo_width()+2)
        self.root.geometry('1800x600')
        self.root.update()
        self.assertFalse(r.scrollbar.winfo_ismapped())
