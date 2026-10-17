"""Numbered lists: source fidelity, continuation markers and editor actions."""
import tempfile
import tkinter as tk
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from presentationpresenter.domain import Aspect, BlockKind, TextBlock, TextRun, TextSection
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings
from presentationpresenter.layout import paginate
from presentationpresenter.session import ProjectionSession
from presentationpresenter.editor import duplicate_section
from presentationpresenter import persistence, storage


class NumberedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.w = MainWindow(self.root, AppSettings(), recovery_dir=Path(self.temp.name)/'recovery')
        self.root.after_cancel(self.w.autosave_job)
        self.w.autosave_job = None
        self.root.update()
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)

    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()
        self.assertEqual(self.errors, [])

    def enter(self):
        self.w.text.focus_force()
        self.root.update()
        self.w.text.event_generate('<Return>')
        self.root.update()

    def key(self, sequence):
        self.w.text.focus_force()
        self.root.update()
        self.w.text.event_generate(sequence)
        self.root.update()

    def test_tab_shift_tab_selection_limits_and_live_isolation(self):
        w = self.w
        w.text.insert('1.0', 'První\nDruhá\nTřetí')
        w.finish_editing()
        w.text.tag_add('sel', '1.0', 'end')
        w.toggle_bullets()
        w.rebuild()
        w.session = ProjectionSession.confirm(w.draft_plan)
        live = w.session
        w.text.tag_add('sel', '2.0', 'end-1c')
        text = w.text.get('1.0', 'end-1c')
        self.key('<Tab>')
        self.assertEqual([b.level for b in w.section().blocks], [0, 1, 1])
        self.assertTrue(w.text.tag_ranges('sel'))
        self.key('<Tab>')
        self.key('<Tab>')
        self.assertEqual([b.level for b in w.section().blocks], [0, 2, 2])
        self.key('<Shift-Tab>')
        self.assertEqual([b.level for b in w.section().blocks], [0, 1, 1])
        self.assertEqual(w.text.get('1.0', 'end-1c'), text)
        self.assertIs(w.session, live)
        w.undo()
        self.assertEqual([b.level for b in w.section().blocks], [0, 2, 2])
        w.redo()
        self.assertEqual([b.level for b in w.section().blocks], [0, 1, 1])

    def test_nested_enter_paste_and_exit(self):
        w = self.w
        w.toggle_bullets()
        self.key('<Tab>')
        w.text.insert('insert', 'Vnořená')
        w.finish_editing()
        self.assertEqual(w.section().blocks[0].level, 1)
        self.enter()
        self.assertEqual(w.section().blocks[-1].level, 1)
        self.assertEqual(w.section().blocks[-1].kind, BlockKind.BULLET)
        with patch.object(self.root, 'clipboard_get', return_value='Druhá\nTřetí'):
            w.paste_text()
        w.finish_editing()
        self.assertEqual([b.level for b in w.section().blocks], [1, 1, 1])
        w.text.mark_set('insert', 'end-1c')
        self.enter()
        self.enter()
        self.assertEqual(w.section().blocks[-1].level, 0)
        self.assertEqual(w.section().blocks[-1].kind, BlockKind.BULLET)
        self.enter()
        self.assertEqual(w.section().blocks[-1].kind, BlockKind.PARAGRAPH)
        before = w.text.get('1.0', 'end-1c')
        self.key('<Tab>')
        self.assertEqual(w.text.get('1.0', 'end-1c'), before+'\t')

    def test_nested_numbering_pagination_portability_and_copy(self):
        w = self.w
        depths = (0, 1, 2, 1, 0)
        blocks = tuple(TextBlock((TextRun('Text ' * (450 if i == 2 else 2)),),
                                 BlockKind.NUMBERED, level=depth) for i, depth in enumerate(depths))
        section = TextSection('Vnoření', blocks)
        document = replace(w.document, sections=(section,))
        self.assertEqual(persistence.loads(persistence.dumps(document)), document)
        self.assertEqual([b.level for b in duplicate_section(section).blocks], list(depths))
        path = Path(self.temp.name)/'nested.ppres'
        storage.save(path, document)
        self.assertEqual(storage.load(path), document)
        for hall in Aspect:
            for stream in Aspect:
                plan = paginate(replace(document, hall=replace(document.hall, aspect=hall),
                                        stream=replace(document.stream, aspect=stream)), w.metrics)
                for output in ('hall', 'stream'):
                    markers = [p.text for s in plan.slides if not s.black
                               for p in getattr(s, output).pieces if p.source is None and p.text != 'Vnoření']
                    for marker in ('1.', '1.1.', '1.1.1.', '1.2.', '2.'):
                        self.assertIn(marker, markers)
                    self.assertIn('1.1.1. ↳', markers)
                for block in blocks:
                    text = ''.join(run.text[r.start:r.end] for s in plan.slides for r in s.ranges
                                   for run in block.runs if r.run_id == run.id)
                    self.assertEqual(text, ''.join(run.text for run in block.runs))
        for invalid in (-1, 3, True, 1.5):
            with self.assertRaises(ValueError):
                TextBlock((), BlockKind.BULLET, level=invalid)
    def test_button_toggle_enter_typing_and_undo(self):
        w = self.w
        w.text.insert('1.0', 'První')
        w.finish_editing()
        w.numbered_button.invoke()
        self.assertEqual(w.section().blocks[0].kind, BlockKind.NUMBERED)
        w.text.mark_set('insert', 'end-1c')
        self.enter()
        self.assertEqual([b.kind for b in w.section().blocks], [BlockKind.NUMBERED]*2)
        w.text.insert('insert', 'Druhá')
        w.finish_editing()
        self.assertEqual(w.section().blocks[1].kind, BlockKind.NUMBERED)
        self.enter()
        self.enter()
        self.assertEqual(w.section().blocks[-1].kind, BlockKind.PARAGRAPH)
        w.undo()
        self.assertEqual(w.section().blocks[-1].kind, BlockKind.NUMBERED)
        w.text.tag_add('sel', '1.0', 'end')
        w.numbered_button.invoke()
        self.assertTrue(all(b.kind == BlockKind.PARAGRAPH for b in w.section().blocks))
        w.undo()
        self.assertTrue(all(b.kind == BlockKind.NUMBERED for b in w.section().blocks))

    def test_common_pagination_number_restart_and_wide_markers(self):
        w = self.w
        blocks = [TextBlock((TextRun('Položka '+str(i)),), BlockKind.NUMBERED) for i in range(1, 13)]
        blocks += [TextBlock((TextRun('Oddělení'),)), TextBlock((TextRun('Dlouhá ' * 850),), BlockKind.NUMBERED)]
        section = TextSection('Seznam', tuple(blocks))
        document = replace(w.document, sections=(section,))
        plan = paginate(document, w.metrics)
        for output in ('hall', 'stream'):
            markers = [p for s in plan.slides if not s.black for p in getattr(s, output).pieces if p.source is None and p.text != 'Seznam']
            texts = [p.text for p in markers]
            self.assertIn('12.', texts)
            self.assertEqual(texts.count('1.'), 2)
            self.assertIn('1. ↳', texts)
            for slide in plan.slides:
                if slide.black:
                    continue
                for p in getattr(slide, output).pieces:
                    if p.source:
                        preceding = [m for m in getattr(slide, output).pieces if m.source is None and m.box.y == p.box.y]
                        for m in preceding:
                            self.assertLessEqual(m.box.x+m.box.width, p.box.x)
        for block in blocks:
            reconstructed = ''.join(run.text[r.start:r.end] for s in plan.slides for r in s.ranges
                                    for run in block.runs if r.run_id == run.id)
            self.assertEqual(reconstructed, ''.join(r.text for r in block.runs))

    def test_roundtrip_copy_and_live_isolation(self):
        w = self.w
        w.text.insert('1.0', 'Jedna\nDvě')
        w.finish_editing()
        w.text.tag_add('sel', '1.0', 'end-1c')
        w.numbered_button.invoke()
        w.rebuild()
        self.assertEqual(persistence.loads(persistence.dumps(w.document)), w.document)
        path = Path(self.temp.name)/'list.ppres'
        storage.save(path, w.document)
        self.assertEqual(storage.load(path), w.document)
        copy = duplicate_section(w.section())
        self.assertTrue(all(b.kind == BlockKind.NUMBERED for b in copy.blocks))
        self.assertNotEqual(copy.blocks[0].id, w.section().blocks[0].id)
        w.session = ProjectionSession.confirm(w.draft_plan)
        live = w.session
        w.text.tag_add('sel', '1.0', 'end')
        w.toggle_bullets()
        self.assertIs(w.session, live)
        w.apply_live()
        self.assertTrue(all(b.kind == BlockKind.BULLET for b in w.session.plan.source.sections[0].blocks))

    def test_paste_in_empty_numbered_item_keeps_list(self):
        w = self.w
        w.numbered_button.invoke()
        with patch.object(self.root, 'clipboard_get', return_value='První\nDruhá\nTřetí'):
            w.paste_text()
        w.finish_editing()
        self.assertEqual(len(w.section().blocks), 3)
        self.assertTrue(all(b.kind == BlockKind.NUMBERED for b in w.section().blocks))
        w.rebuild()
        slide = next(s for s in w.plan.slides if not s.black)
        self.assertEqual([p.text for p in slide.hall.pieces if p.source is None], ['1.', '2.', '3.'])


if __name__ == '__main__':
    unittest.main()
