"""Preview updates must keep up with typing and retain unchanged thumbnails."""
import tkinter as tk
import unittest
from dataclasses import replace
from unittest.mock import patch

from presentationpresenter.domain import Aspect, Presentation, TextSection, TextBlock, TextRun
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow
from presentationpresenter.rendering import draw


class PreviewLatencyTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.window = MainWindow(self.root, AppSettings())
        self.root.update()
        self.window.rebuild()

    def tearDown(self):
        self.root.destroy()

    def document(self, count=12):
        return Presentation(black_start=False, sections=tuple(
            TextSection(str(i), (TextBlock((TextRun('Obsah '+str(i)),)),),
                        break_before=False, break_after=False)
            for i in range(count)))

    def edit_first(self):
        w = self.window
        section = w.document.sections[0]
        block = section.blocks[0]
        updated = replace(section, blocks=(replace(block, runs=(
            replace(block.runs[0], text=block.runs[0].text+'x'),)),))
        w.update_section(updated, ('text', section.id))

    def test_continuous_typing_does_not_postpone_pending_update(self):
        w = self.window
        w.commit(self.document())
        w.rebuild()
        with patch.object(self.root, 'after', wraps=self.root.after) as after:
            self.edit_first()
            pending = w.pending
            self.edit_first()
            self.assertEqual(w.pending, pending)
            preview_delays = [call.args[0] for call in after.call_args_list
                              if call.args[1] == w.rebuild]
            self.assertEqual(preview_delays, [40])
        w.rebuild()
        self.assertEqual(w.plan.source, w.document)

    def test_edit_reuses_widgets_and_redraws_only_changed_thumbnail(self):
        w = self.window
        w.commit(self.document())
        w.rebuild()
        before = tuple(w.thumbnails)
        self.edit_first()
        with patch('presentationpresenter.ui.draw', wraps=draw) as render:
            w.rebuild()
        self.assertEqual(tuple(w.thumbnails), before)
        thumbnails_drawn = [call.args[0] for call in render.call_args_list
                            if call.args[0] in before]
        self.assertEqual(thumbnails_drawn, [before[0]])
        self.assertEqual(w.plan.source, w.document)

    def test_slide_count_and_aspect_changes_recreate_strip(self):
        w = self.window
        w.commit(self.document(2))
        w.rebuild()
        before = tuple(w.thumbnails)
        w.commit(self.document(3))
        w.rebuild()
        self.assertEqual(len(w.thumbnails), len(w.plan.slides))
        self.assertFalse(any(canvas in before for canvas in w.thumbnails))
        for i, canvas in enumerate(w.thumbnails):
            self.assertIn(str(i), w.labels[i])
        before = tuple(w.thumbnails)
        aspect = Aspect.WIDE if w.document.hall.aspect != Aspect.WIDE else Aspect.STANDARD
        w.commit(replace(w.document, hall=replace(w.document.hall, aspect=aspect)))
        w.rebuild()
        self.assertFalse(any(canvas in before for canvas in w.thumbnails))


if __name__ == '__main__':
    unittest.main()
