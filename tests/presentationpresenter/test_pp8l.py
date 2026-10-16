"""Layout regressions for the agreed ribbon and draft/live controls."""
import tempfile
import tkinter as tk
import unittest
from dataclasses import replace
from unittest.mock import patch

from presentationpresenter.domain import TextSection, TextBlock, TextRun
from presentationpresenter.settings import AppSettings
from presentationpresenter.projection import Monitor, configure_dpi
from presentationpresenter.ui import MainWindow

configure_dpi()


class RibbonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.discovery = patch('presentationpresenter.ui.monitors', return_value=[Monitor('QA', 0, 0, 1024, 768)])
        self.discovery.start()
        self.root = tk.Tk()
        self.w = MainWindow(self.root, AppSettings(), recovery_dir=self.temp.name)
        self.root.after_cancel(self.w.autosave_job)
        self.w.autosave_job = None
        self.root.geometry('1024x768+20+20')
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.discovery.stop()
        self.temp.cleanup()

    def visible(self, widget):
        self.assertTrue(widget.winfo_viewable())
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        self.assertGreaterEqual(x, self.root.winfo_rootx())
        self.assertGreaterEqual(y, self.root.winfo_rooty())
        self.assertLessEqual(x+widget.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
        self.assertLessEqual(y+widget.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())

    def test_collapse_tabs_scroll_and_section_actions(self):
        w = self.w
        self.assertEqual(w.ribbon.current, 'Domů')
        document = w.document
        w.ribbon.toggle()
        self.root.update()
        self.assertFalse(w.ribbon.content.winfo_viewable())
        self.assertIs(w.document, document)
        self.visible(w.ribbon.toggle_button)
        w.ribbon.show('Úseky')
        sections = tuple(TextSection(title=f'Úsek {i}', blocks=(TextBlock(runs=(TextRun(str(i)),)),)) for i in range(25))
        w.commit(replace(w.document, sections=sections))
        w.rebuild()
        self.root.update()
        self.visible(w.section_scrollbar)
        for button in w.source_buttons:
            self.visible(button)
        w.sections.yview_moveto(1)
        self.root.update()
        self.assertGreater(w.sections.yview()[0], 0)
        w.sections.selection_clear(0, 'end')
        w.sections.selection_set(24)
        w.sections.event_generate('<<ListboxSelect>>')
        self.root.update()
        self.assertEqual(w.selected_id, sections[-1].id)
        w.copy_section()
        self.assertEqual(len(w.document.sections), 26)
        w.undo()
        self.assertEqual(len(w.document.sections), 25)

    def test_checkbox_output_and_aspect_preserve_live_session(self):
        w = self.w
        self.assertEqual(w.output.get(), 'hall')
        self.assertEqual(w.view_version.get(), 'draft')
        self.assertEqual(str(w.draft_checkbox['state']), 'disabled')
        w.output_button.invoke()
        self.assertEqual((w.output.get(), w.output_button['text']), ('stream', 'Sál'))
        w.output_button.invoke()
        self.assertEqual((w.output.get(), w.output_button['text']), ('hall', 'Stream'))
        w.projection_controls.fullscreen['hall'] = False
        self.assertTrue(w.start_projection(('hall',)))
        snapshot = w.session
        w.title.set('Oprava během projekce')
        w.rebuild()
        w.draft_checkbox.invoke()
        self.assertEqual(w.view_version.get(), 'draft')
        self.assertIs(w.session, snapshot)
        c = w.projection_controls
        c.aspect_value.set('16:9')
        c.aspect.event_generate('<<ComboboxSelected>>')
        self.root.update()
        self.assertEqual(w.document.hall.aspect.value, '16:9')
        self.assertEqual(w.session.plan.source.hall.aspect.value, '4:3')
        w.draft_checkbox.invoke()
        self.assertEqual(w.view_version.get(), 'live')
        self.assertIs(w.session, snapshot)
        w.stop_projection()
        self.assertEqual(w.view_version.get(), 'draft')

    def test_small_window_actions_and_formatting_selection(self):
        w = self.w
        for tab in w.ribbon.panels:
            w.ribbon.show(tab)
            self.root.update()
            for button in w.ribbon.buttons.values():
                self.visible(button)
            self.visible(w.projection_controls.edit_button)
            self.visible(w.projection_controls.aspect)
            self.visible(w.apply_button)
        w.ribbon.show('Domů')
        self.root.update()
        w.text.insert('1.0', 'Zvýraznit text')
        w.text.tag_add('sel', '1.0', '1.9')
        w.text.focus_force()
        w.ribbon.buttons['Soubor'].invoke()
        w.ribbon.buttons['Domů'].invoke()
        self.root.update()
        w.format_selection('bold')
        self.assertTrue(w.document.sections[0].blocks[0].runs[0].style.bold)
        self.assertEqual(w.root.focus_get(), w.text)


if __name__ == '__main__':
    unittest.main()
