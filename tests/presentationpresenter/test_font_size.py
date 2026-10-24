"""Selected and future text sizes, field focus, source/layout and live safety."""
import tempfile
import tkinter as tk
import unittest
from dataclasses import replace
from pathlib import Path
from presentationpresenter.domain import Aspect, TextStyle, TextRun, TextBlock, TextSection
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings
from presentationpresenter.session import ProjectionSession
from presentationpresenter.editor import duplicate_section
from presentationpresenter.layout import paginate
from presentationpresenter import storage, persistence


class FontSizeTests(unittest.TestCase):
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
        self.assertFalse(self.errors)

    def size(self, value, key='<Return>'):
        w = self.w
        w.size_box.focus_force()
        self.root.update()
        w.font_size.set(str(value))
        w.size_box.event_generate(key)
        self.root.update()

    def text(self, value):
        self.w.text.insert('insert', value)
        self.w.finish_editing()

    def family(self, value, key='<Return>'):
        w = self.w
        w.family_box.focus_force()
        self.root.update()
        w.font_family.set(value)
        w.family_box.event_generate(key)
        self.root.update()

    def other_family(self):
        available = self.w.metrics.available_families
        return next((available[name] for name in ('arial', 'segoe ui', 'times new roman')
                     if name in available and name != self.w.metrics.fallback_family.casefold()),
                    next(name for name in available.values() if name.casefold() != self.w.metrics.fallback_family.casefold()))

    def test_default_calibri_and_legacy_fonts_are_preserved(self):
        w = self.w
        self.assertEqual(w.font_family.get(), 'Calibri')
        w.text.focus_force()
        self.root.update()
        w.text.event_generate('<KeyPress-a>')
        self.root.update()
        self.text('Nový text')
        self.assertEqual(w.section().blocks[0].runs[0].style.family, 'Calibri')
        legacy = replace(w.document, sections=(TextSection('Starý', (TextBlock((TextRun('Původní', TextStyle()),)),)),))
        loaded = persistence.loads(persistence.dumps(legacy))
        self.assertEqual(loaded.sections[0].blocks[0].runs[0].style.family, '')
        w.commit(loaded)
        w.rebuild()
        self.assertEqual(w.font_family.get(), w.metrics.fallback_family)
        self.assertEqual(w.section().blocks[0].runs[0].style.family, '')

    def test_font_suggestions_filter_keep_focus_and_enter_applies_selection(self):
        w = self.w
        self.text('ABCDE')
        w.text.tag_add('sel', '1.1', '1.4')
        before = w.document
        w.family_box.focus_force()
        self.root.update()
        w.family_box.delete(0, 'end')
        for key in 'cal':
            w.family_box.event_generate('<KeyPress-'+key+'>')
            w.family_box.event_generate('<KeyRelease-'+key+'>')
            self.root.update()
        self.root.update()
        menu = w.font_suggestions
        self.assertTrue(menu.visible())
        self.assertIs(self.root.focus_get(), w.family_box)
        names = menu.items.get(0, 'end')
        self.assertTrue(all('cal' in name.casefold() for name in names))
        self.assertIn('Calibri', names)
        self.assertEqual(w.document, before)
        w.family_box.event_generate('<Down>')
        self.root.update()
        chosen = menu.items.get(menu.items.curselection()[0])
        w.family_box.event_generate('<Return>')
        self.root.update()
        self.assertFalse(menu.visible())
        self.assertIs(self.root.focus_get(), w.text)
        runs = w.section().blocks[0].runs
        self.assertEqual(runs[1].style.family, chosen)
        self.assertEqual(runs[0].text, 'A')
        self.assertTrue(w.text.tag_ranges('sel'))

    def test_font_suggestions_mouse_escape_no_matches_and_collapse(self):
        w = self.w
        w.family_box.focus_force()
        self.root.update()
        before = w.document
        w.font_family.set('cal')
        w.family_box.event_generate('<KeyRelease-l>')
        self.root.update()
        menu = w.font_suggestions
        w.family_box.event_generate('<Escape>')
        self.root.update()
        self.assertFalse(menu.visible())
        self.assertIs(self.root.focus_get(), w.family_box)
        self.assertEqual(w.font_family.get(), 'cal')
        w.family_box.event_generate('<Escape>')
        self.root.update()
        self.assertEqual(w.document, before)
        self.assertEqual(w.font_family.get(), 'Calibri')
        w.family_box.focus_force()
        self.root.update()
        w.font_family.set('zz-no-matching-font-zz')
        w.family_box.event_generate('<KeyRelease-z>')
        self.root.update()
        self.assertFalse(menu.visible())
        w.font_family.set('cal')
        w.family_box.event_generate('<KeyRelease-l>')
        self.root.update()
        menu.items.event_generate('<ButtonPress-1>', x=10, y=5)
        menu.items.event_generate('<ButtonRelease-1>', x=10, y=5)
        self.root.update()
        self.assertFalse(menu.visible())
        self.assertIs(self.root.focus_get(), w.text)
        self.assertEqual(w.document, before)  # Future typing only.
        w.family_box.focus_force()
        self.root.update()
        w.font_family.set('cal')
        w.family_box.event_generate('<KeyRelease-l>')
        self.root.update()
        w.ribbon.toggle()
        self.root.update()
        self.assertFalse(menu.visible())

    def test_family_selection_preserves_size_and_other_style_and_live(self):
        w = self.w
        self.text('ABCDE')
        original_family = w.section().blocks[0].runs[0].style.family
        w.text.tag_add('sel', '1.1', '1.4')
        self.size(60)
        w.format_selection('bold')
        w.rebuild()
        w.session = ProjectionSession.confirm(w.draft_plan)
        live = w.session
        chosen = self.other_family()
        self.family(chosen)
        runs = w.section().blocks[0].runs
        self.assertEqual([(r.text, r.style.family) for r in runs], [('A', original_family), ('BCD', chosen), ('E', original_family)])
        self.assertTrue(runs[1].style.bold)
        self.assertEqual(runs[1].style.size, 60)
        self.assertTrue(w.text.tag_ranges('sel'))
        self.assertIs(w.session, live)
        self.assertEqual(w.metrics.font(runs[1].style, 60).actual('family').casefold(), chosen.casefold())
        w.undo()
        self.assertEqual(w.section().blocks[0].runs[1].style.family, original_family)
        w.redo()
        w.apply_live()
        self.assertEqual(w.session.plan.source, w.document)

    def test_future_family_mixed_selection_escape_and_validation(self):
        w = self.w
        self.text('Staré')
        before = w.document
        chosen = self.other_family()
        self.family(chosen)
        self.assertEqual(w.document, before)
        self.size(48)
        self.text('Nové')
        self.assertEqual(w.section().blocks[0].runs[-1].style.family, chosen)
        w.text.event_generate('<Return>')
        self.root.update()
        self.text('Další')
        self.assertEqual(w.section().blocks[1].runs[0].style.family, chosen)
        w.text.tag_add('sel', '1.0', 'end-1c')
        w.sync_font_size()
        self.assertEqual(w.font_family.get(), '')
        original = w.document
        self.family(w.metrics.fallback_family, '<Escape>')
        self.assertEqual(w.document, original)
        self.family('Neexistující QA Font 123')
        self.assertEqual(w.document, original)
        self.assertIn('nainstalovaný font', w.status.get())

    def test_missing_family_warns_without_rewriting_portable_data(self):
        w = self.w
        missing = 'Neexistující QA Font 123'
        style = TextStyle(family=missing, size=48)
        doc = replace(w.document, sections=(TextSection('QA', (TextBlock((TextRun('Text', style),)),)),))
        w.commit(doc)
        w.rebuild()
        self.assertIn(missing, w.display_status.get())
        self.assertIn(w.metrics.fallback_family, w.display_status.get())
        self.assertEqual(w.metrics.font(style, 48).actual('family').casefold(), w.metrics.fallback_family.casefold())
        self.assertEqual(w.font_family.get(), missing)
        path = Path(self.temp.name)/'missing.ppres'
        storage.save(path, doc)
        self.assertEqual(storage.load(path), doc)
        self.assertEqual(duplicate_section(doc.sections[0]).blocks[0].runs[0].style.family, missing)
        for invalid in (None, 25, ' Bad ', 'X\nY', 'X'*129):
            with self.assertRaises(ValueError):
                TextStyle(family=invalid)

    def test_mixed_families_share_baseline_and_preserve_all_text(self):
        w = self.w
        chosen = self.other_family()
        block = TextBlock((TextRun('Courier ', TextStyle(size=48)),
                           TextRun('Arial a pokračování ' * 100, TextStyle(family=chosen, size=32))))
        source = replace(w.document, sections=(TextSection('Hlavička', (block,)),))
        self.assertEqual(persistence.loads(persistence.dumps(source)), source)
        for hall in Aspect:
            for stream in Aspect:
                plan = paginate(replace(source, hall=replace(source.hall, aspect=hall),
                                        stream=replace(source.stream, aspect=stream)), w.metrics)
                first = next(s for s in plan.slides if not s.black)
                for output in ('hall', 'stream'):
                    pieces = [p for p in getattr(first, output).pieces if p.source and p.text]
                    baseline = pieces[0].box.y+w.metrics.ascent(pieces[0].style, pieces[0].font_size)
                    self.assertEqual(baseline, pieces[1].box.y+w.metrics.ascent(pieces[1].style, pieces[1].font_size))
                    for slide in plan.slides:
                        if slide.black:
                            continue
                        layout = getattr(slide, output)
                        for p in layout.pieces:
                            if p.source and p.text:
                                self.assertLessEqual(w.metrics.height(p.style, p.font_size), p.box.height)
                                if layout.exclusion:
                                    self.assertFalse(p.box.intersects(layout.exclusion))
                for run in block.runs:
                    self.assertEqual(''.join(run.text[r.start:r.end] for s in plan.slides for r in s.ranges if r.run_id == run.id), run.text)

    def test_selection_changes_only_selected_size_with_undo_and_live_isolation(self):
        w = self.w
        self.text('ABCDE')
        w.rebuild()
        w.session = ProjectionSession.confirm(w.draft_plan)
        live = w.session
        w.text.tag_add('sel', '1.1', '1.4')
        self.size(60)
        runs = w.section().blocks[0].runs
        self.assertEqual([(r.text, r.style.size) for r in runs], [('A', 36), ('BCD', 60), ('E', 36)])
        self.assertTrue(w.text.tag_ranges('sel'))
        self.assertIs(self.root.focus_get(), w.text)
        self.assertIs(w.session, live)
        w.undo()
        self.assertTrue(all(r.style.size == 36 for r in w.section().blocks[0].runs))
        w.redo()
        w.apply_live()
        self.assertEqual(w.session.plan.source, w.document)

    def test_future_typing_and_enter_inherit_size_without_changing_existing_text(self):
        w = self.w
        self.text('Staré')
        before = w.document
        self.size(72)
        self.assertEqual(w.document, before)
        self.text('Nové')
        self.assertEqual([(r.text, r.style.size) for r in w.section().blocks[0].runs], [('Staré', 36), ('Nové', 72)])
        w.text.focus_force()
        self.root.update()
        w.text.event_generate('<Return>')
        self.root.update()
        self.text('Další')
        self.assertEqual(w.section().blocks[1].runs[0].style.size, 72)
        w.text.mark_set('insert', '1.0')
        w.sync_font_size()
        self.assertEqual(w.font_size.get(), '36')
        w.text.mark_set('insert', '1.5')  # Boundary: inherit the left-hand size.
        w.sync_font_size()
        self.assertEqual(w.font_size.get(), '36')

    def test_mixed_selection_escape_validation_and_typing_after_empty_paragraph(self):
        w = self.w
        self.size(48)
        self.text('Velké')
        self.size(24)
        self.text('malé')
        w.text.tag_add('sel', '1.0', 'end-1c')
        w.sync_font_size()
        self.assertEqual(w.font_size.get(), '')
        original = w.document
        self.size(100, '<Escape>')
        self.assertEqual(w.document, original)
        self.size(999)
        self.assertEqual(w.document, original)
        self.assertIn('8 do 144', w.status.get())
        w.font_size.set('32')
        w.size_box.event_generate('<Return>')
        self.root.update()
        self.assertTrue(all(r.style.size == 32 for r in w.section().blocks[0].runs))

    def test_mixed_layout_roundtrip_and_copy_all_aspects(self):
        w = self.w
        block = TextBlock((TextRun('Velké ', TextStyle(bold=True, size=96)),
                           TextRun('menší text ' * 350, TextStyle(italic=True, size=24))))
        source = replace(w.document, sections=(TextSection('Hlavička', (block,)),))
        self.assertEqual(persistence.loads(persistence.dumps(source)), source)
        path = Path(self.temp.name)/'sizes.ppres'
        storage.save(path, source)
        self.assertEqual(storage.load(path), source)
        self.assertEqual([r.style.size for r in duplicate_section(source.sections[0]).blocks[0].runs], [96, 24])
        for hall in Aspect:
            for stream in Aspect:
                doc = replace(source, hall=replace(source.hall, aspect=hall), stream=replace(source.stream, aspect=stream))
                plan = paginate(doc, w.metrics)
                first = next(s for s in plan.slides if not s.black)
                for output in ('hall', 'stream'):
                    pieces = [p for p in getattr(first, output).pieces if p.source and p.text]
                    self.assertEqual(pieces[0].box.y+w.metrics.ascent(pieces[0].style, pieces[0].font_size),
                                     pieces[1].box.y+w.metrics.ascent(pieces[1].style, pieces[1].font_size))
                heights = set()
                for slide in plan.slides:
                    if slide.black:
                        continue
                    for output in ('hall', 'stream'):
                        layout = getattr(slide, output)
                        for piece in layout.pieces:
                            if piece.source:
                                self.assertEqual(piece.font_size, piece.style.size)
                                self.assertLessEqual(piece.box.y+piece.box.height, layout.height-32)
                                if piece.text and layout.exclusion:
                                    self.assertFalse(piece.box.intersects(layout.exclusion))
                                heights.add(piece.box.height)
                            else:
                                self.assertEqual(piece.font_size, 24)  # Heading unchanged.
                self.assertGreater(len(heights), 1)
                for run in block.runs:
                    reconstructed = ''.join(run.text[r.start:r.end] for s in plan.slides for r in s.ranges if r.run_id == run.id)
                    self.assertEqual(reconstructed, run.text)
        for invalid in (0, 145, True, 12.5):
            with self.assertRaises(ValueError):
                TextStyle(size=invalid)

    def test_future_size_survives_list_commands_and_unconfirmed_field_edit_is_discarded(self):
        w = self.w
        self.size(72)
        w.toggle_bullets()
        w.text.focus_force()
        self.root.update()
        w.text.event_generate('<Tab>')
        self.root.update()
        self.text('Položka')
        self.assertEqual(w.section().blocks[0].runs[0].style.size, 72)
        w.text.event_generate('<Return>')
        self.root.update()
        self.text('Další')
        self.assertEqual(w.section().blocks[1].runs[0].style.size, 72)
        w.size_box.focus_force()
        self.root.update()
        w.font_size.set('96')
        w.text.focus_force()
        self.root.update()
        self.assertEqual(w.font_size.get(), '72')
        self.text('!')
        self.assertTrue(all(r.style.size == 72 for r in w.section().blocks[1].runs))


if __name__ == '__main__':
    unittest.main()
