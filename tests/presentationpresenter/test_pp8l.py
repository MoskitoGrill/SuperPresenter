"""Layout regressions for the agreed ribbon and draft/live controls."""
import tempfile
import tkinter as tk
import unittest
import time
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
        if self.root is not None:
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
        self.assertEqual(str(w.draft_button['state']), 'disabled')
        w.output_button.invoke()
        self.assertEqual((w.output.get(), w.output_button['text']), ('stream', 'Sál'))
        w.output_button.invoke()
        self.assertEqual((w.output.get(), w.output_button['text']), ('hall', 'Stream'))
        w.projection_controls.fullscreen['hall'] = False
        self.assertTrue(w.start_projection(('hall',)))
        snapshot = w.session
        w.title.set('Oprava během projekce')
        w.rebuild()
        self.assertEqual(w.unapplied_changes.get(), 'Nepoužité změny')
        w.draft_button.invoke()
        self.assertEqual(w.view_version.get(), 'draft')
        self.assertIs(w.session, snapshot)
        c = w.projection_controls
        c.aspect_value.set('16:9')
        c.aspect.event_generate('<<ComboboxSelected>>')
        self.root.update()
        self.assertEqual(w.document.hall.aspect.value, '16:9')
        self.assertEqual(w.session.plan.source.hall.aspect.value, '4:3')
        w.draft_button.invoke()
        self.assertEqual(w.view_version.get(), 'live')
        self.assertIs(w.session, snapshot)
        self.assertTrue(w.apply_live())
        self.assertEqual(w.unapplied_changes.get(), '')
        w.stop_projection()
        self.assertEqual(w.view_version.get(), 'draft')

    def test_small_window_actions_and_formatting_selection(self):
        w = self.w
        heights = []
        for tab in w.ribbon.panels:
            w.ribbon.show(tab)
            self.root.update()
            for button in w.ribbon.buttons.values():
                self.visible(button)
            if tab == 'Zobrazení':
                self.visible(w.projection_controls.edit_button)
                self.visible(w.projection_controls.aspect)
            else:
                self.assertFalse(w.projection_controls.frame.winfo_viewable())
            self.visible(w.projection_controls.play)
            self.visible(w.apply_button)
            heights.append(w.ribbon.content.winfo_height())
        self.assertEqual(len(set(heights)), 1, heights)
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

    def test_navigation_buttons_use_section_and_slide_controls(self):
        w = self.w
        w.add_section()
        w.rebuild()
        self.root.update()
        first = w.document.sections[0].id
        second = w.document.sections[1].id
        w.previous_section_button.invoke()
        self.assertEqual(w.plan.slides[w.current].section_id, first)
        w.next_section_button.invoke()
        self.assertEqual(w.plan.slides[w.current].section_id, second)
        self.assertTrue(w.plan.slides[w.current].black)
        current = w.current
        w.next_slide_button.invoke()
        self.assertEqual(w.current, current+1)
        w.previous_slide_button.invoke()
        self.assertEqual(w.current, current)

    def test_strip_drag_and_wheel_preserve_preview_and_editor_focus(self):
        w = self.w
        sections = tuple(TextSection(title=f'Úsek {i}', blocks=(TextBlock(runs=(TextRun(str(i)),)),)) for i in range(20))
        w.commit(replace(w.document, sections=sections))
        w.rebuild()
        self.root.update()
        canvases = tuple(w.thumbnails)
        plan, position = w.plan, w.current
        old_height, old_width = w.strip.winfo_height(), w.thumbnail_width
        x, y = w.workspace.sash_coord(0)
        w.workspace.event_generate('<ButtonPress-1>', x=50, y=y+2)
        w.workspace.event_generate('<B1-Motion>', x=50, y=y-38)
        w.workspace.event_generate('<ButtonRelease-1>', x=50, y=y-38)
        self.root.update()
        self.assertGreater(w.strip.winfo_height(), old_height)
        self.assertGreater(w.thumbnail_width, old_width)
        self.assertEqual(tuple(w.thumbnails), canvases)
        self.assertIs(w.plan, plan)
        self.assertEqual(w.current, position)
        w.text.focus_force()
        w.strip.xview_moveto(0)
        self.root.update()
        w.thumbnails[0].event_generate('<MouseWheel>', delta=-120)
        self.root.update()
        self.assertGreater(w.strip.xview()[0], 0)
        self.assertEqual(w.current, position)
        self.assertIs(self.root.focus_get(), w.text)
        offset = w.strip.xview()
        w.text.event_generate('<MouseWheel>', delta=-120)
        self.root.update()
        self.assertEqual(w.strip.xview(), offset)

    def test_resize_updates_are_coalesced_and_cancelled_on_destroy(self):
        w = self.w
        self.root.update()
        for _ in range(25):
            w.queue_workspace_resize()
        job = w.resize_job
        self.assertIsNotNone(job)
        w.queue_workspace_resize()
        self.assertEqual(w.resize_job, job)
        w.finish_workspace_resize()
        self.root.update()
        self.assertIsNone(w.resize_job)
        self.assertFalse(w.resizing_workspace)
        w.queue_workspace_resize()
        job = w.resize_job
        self.root.destroy()
        pending = self.root.tk.call('after', 'info')
        self.assertNotIn(job, pending)
        self.root = None

    def test_continuous_motion_does_not_starve_control_painting(self):
        w = self.w
        w.finish_workspace_resize()
        self.root.update()
        done = tk.BooleanVar(self.root, value=False)
        _, y = w.workspace.sash_coord(0)
        w.workspace.event_generate('<ButtonPress-1>', x=50, y=y+2)
        started = time.monotonic()
        counts = []
        with patch.object(w, 'redraw_resize_controls', wraps=w.redraw_resize_controls) as redraw:
            def move():
                elapsed = time.monotonic()-started
                if elapsed >= .3:
                    counts.append(redraw.call_count)
                    w.workspace.event_generate('<ButtonRelease-1>', x=50, y=y+2)
                    done.set(True)
                    return
                offset = 25 if int(elapsed*60) % 2 else -25
                w.workspace.event_generate('<B1-Motion>', x=50, y=y+2+offset)
                # Keep regular events arriving: no explicit update()/idle flush.
                self.root.after(0, move)
            self.root.after(0, move)
            self.root.wait_variable(done)
        self.root.update()
        self.assertGreaterEqual(counts[0], 2)


if __name__ == '__main__':
    unittest.main()
