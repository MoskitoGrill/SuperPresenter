"""Live publication, exact anchors and isolation regressions."""
import tkinter as tk
import unittest
from dataclasses import replace
from unittest.mock import patch
from presentationpresenter import anchors
from presentationpresenter.domain import *
from presentationpresenter.layout import paginate, Typography
from presentationpresenter.rendering import TkMetrics
from presentationpresenter.ui import MainWindow
from presentationpresenter.projection import Monitor
from presentationpresenter.settings import AppSettings


def section(value):
    return TextSection('Test', (TextBlock((TextRun(value),)),), break_after=False, break_before=True)


class AnchorTests(unittest.TestCase):
    def test_exact_operations_repeated_sentences_and_fallbacks(self):
        value = 'Stejná věta. Stejná věta. Poslední.'
        a = anchors.Anchor('section', 'block', 13)
        self.assertEqual(anchors.edit(a, value, 0, 0, 'Stejná věta. ').offset, 26)
        self.assertEqual(anchors.edit(a, value, 0, 13, '').offset, 0)
        self.assertEqual(anchors.edit(a, value, 13, 26, '').offset, 13)
        self.assertEqual(anchors.edit(a, value, 13, len(value), '').offset, 0)
        # An edit within the sentence, with an anchor halfway through it.
        self.assertEqual(anchors.edit(replace(a, offset=18), value, 15, 17, 'XX').offset, 13)

    def test_section_and_block_removal_use_original_successors(self):
        s1, s2, s3 = section('A.'), section('B.'), section('C.')
        old = Presentation(sections=(s1, s2, s3))
        a = anchors.Anchor(s2.id, s2.blocks[0].id)
        new = replace(old, sections=(s3, s1))
        self.assertEqual(anchors.relocate(a, old, new).section_id, s3.id)
        self.assertEqual(anchors.relocate(a, old, replace(old, sections=(s1,))).section_id, s1.id)
        blocks = (TextBlock((TextRun('A.'),)), TextBlock((TextRun('B.'),)), TextBlock((TextRun('C.'),)))
        s = replace(s1, blocks=blocks)
        old = replace(old, sections=(s,))
        a = anchors.Anchor(s.id, blocks[1].id)
        new = replace(old, sections=(replace(s, blocks=(blocks[0], blocks[2])),))
        self.assertEqual(anchors.relocate(a, old, new).block_id, blocks[2].id)

    def test_natural_pagination_all_aspects_contains_anchor_and_complete_source(self):
        root = tk.Tk()
        root.withdraw()
        try:
            metrics = TkMetrics(root)
            s = section('První věta. '+('Opakující se obsah. '*110))
            a = anchors.Anchor(s.id, s.blocks[0].id, 237)
            for hall in Aspect:
                for stream in Aspect:
                    source = Presentation(sections=(s,), hall=OutputConfig(hall), stream=OutputConfig(stream, CameraRegion()))
                    plan = paginate(source, metrics, Typography())
                    selected = next(x for x in plan.slides if x.id == anchors.locate(plan, a))
                    self.assertTrue(any(r.start <= a.offset < r.end for r in selected.ranges))
                    ranges = [r for slide in plan.slides for r in slide.ranges]
                    self.assertEqual(''.join(s.blocks[0].runs[0].text[r.start:r.end] for r in ranges), anchors.text(s.blocks[0]))
                    for slide in plan.slides:
                        if not slide.black:
                            for output in ('hall', 'stream'):
                                self.assertEqual(tuple(p.source for p in getattr(slide, output).pieces if p.source)[0].start, slide.ranges[0].start)
                                self.assertFalse(any(p.source and getattr(slide, output).exclusion and p.box.intersects(getattr(slide, output).exclusion) for p in getattr(slide, output).pieces))
        finally:
            root.destroy()


class LiveEditTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.errors = []
        self.root.report_callback_exception = lambda *e: self.errors.append(e)
        self.discovery = patch('presentationpresenter.ui.monitors', return_value=[Monitor('A', 0, 0, 800, 600)])
        self.discovery.start()
        self.w = MainWindow(self.root, AppSettings())
        self.w.monitor_choices['stream'].set('A')
        self.w.projection_controls.fullscreen = {'hall': False, 'stream': False}
        self.s = section('Stejná věta. Stejná věta. Poslední. '+('Zbývající obsah. '*85))
        self.w.commit(replace(self.w.document, sections=(self.s,)))
        self.w.selected_id = self.s.id
        self.w.load_editor()
        self.w.rebuild()
        self.assertTrue(self.w.start_projection(('hall', 'stream')))
        self.w.jump(1)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.discovery.stop()
        self.assertEqual(self.errors, [])

    def continuation(self):
        w = self.w
        indices = [i for i, s in enumerate(w.plan.slides) if not s.black]
        self.assertGreaterEqual(len(indices), 2)
        w.jump(indices[1])
        return w.live_anchor

    def assert_contains(self, plan, slide_id, anchor):
        slide = next(s for s in plan.slides if s.id == slide_id)
        self.assertEqual(slide.section_id, anchor.section_id)
        section = next(s for s in plan.source.sections if s.id == anchor.section_id)
        block = next(b for b in section.blocks if b.id == anchor.block_id)
        offset = 0
        for run in block.runs:
            if offset <= anchor.offset < offset + len(run.text):
                self.assertTrue(any(r.run_id == run.id and r.start <= anchor.offset-offset < r.end for r in slide.ranges))
                return
            offset += len(run.text)
        self.fail('Anchor has no source character')

    def canvas_text(self):
        return {f: tuple(p.canvas.itemcget(i, 'text') for i in p.canvas.find_all() if p.canvas.type(i) == 'text') for f, p in self.w.projections.items()}

    def test_isolation_draft_preview_undo_redo_and_atomic_apply(self):
        w = self.w
        a = self.continuation()
        original = w.session
        visible = self.canvas_text()
        w.text.insert('1.0', 'Stejná věta. ')
        self.root.update()
        w.rebuild()
        self.assertEqual(w.live_anchor.offset, a.offset + 13)
        # Other live slides are tracked too: visit a black break and come back.
        position = w.current
        w.jump(0)
        w.jump(position)
        self.assertEqual(w.live_anchor.offset, a.offset + 13)
        self.assertIs(w.session.plan, original.plan)
        self.assertEqual(self.canvas_text(), visible)
        w.view_version.set('draft')
        w.switch_version()
        w.thumbnail_clicked(len(w.plan.slides)-1)
        self.assertEqual(w.session.current_slide_id, original.current_slide_id)
        w.undo()
        self.assertEqual(w.live_anchor.offset, a.offset)
        w.redo()
        self.assertEqual(w.live_anchor.offset, a.offset + 13)
        w.rebuild()
        self.assertEqual(self.canvas_text(), visible)
        w.toggle_blackout()
        seen = []
        callbacks = []
        for p in w.projections.values():
            callback = patch.object(p, 'render', side_effect=lambda: seen.append(w.session))
            callbacks.append(callback)
            callback.start()
        try:
            self.assertTrue(w.apply_live())
        finally:
            for callback in callbacks:
                callback.stop()
        self.assertEqual(len(seen), 2)
        self.assertIs(seen[0], seen[1])
        self.assertTrue(w.session.blackout)
        self.assert_contains(w.session.plan, w.session.current_slide_id, replace(a, offset=a.offset+13))
        self.assertEqual(w.session.plan, paginate(w.document, w.metrics, w.typography))
        w.toggle_blackout()
        self.assertNotEqual(self.canvas_text(), {'hall': (), 'stream': ()})

    def test_sentence_change_delete_and_insertion_of_new_paragraph(self):
        w = self.w
        w.text.replace('1.2', '1.4', 'XX')
        self.root.update()
        self.assertEqual(w.live_anchor.offset, 0)
        self.assertTrue(w.apply_live())
        w.text.delete('1.0', '1.13')
        self.root.update()
        self.assertEqual(w.live_anchor.offset, 0)
        self.assertTrue(w.apply_live())
        old_bid = w.live_anchor.block_id
        w.text.insert('1.0', 'Nový odstavec.\n')
        self.root.update()
        self.assertNotEqual(w.live_anchor.block_id, old_bid)
        self.assertEqual(w.document.sections[0].blocks[1].id, old_bid)
        self.assertEqual(w.live_anchor.offset, 0)
        self.assertTrue(w.apply_live())
        selected = next(s for s in w.session.plan.slides if s.id == w.session.current_slide_id)
        self.assertEqual(anchors.capture(w.session.plan, selected), w.live_anchor)

    def test_black_break_removal_section_removal_aspect_and_invalid_apply(self):
        w = self.w
        w.jump(0)
        original = w.session
        w.change_aspect('stream', '4:3')
        w.update_section(replace(w.section(), break_before=False))
        self.assertIs(w.session.plan, original.plan)
        self.assertTrue(w.apply_live())
        self.assertFalse(next(s for s in w.session.plan.slides if s.id == w.session.current_slide_id).black)
        self.assertEqual(w.session.plan.source.stream.aspect, Aspect.STANDARD)
        good = w.session
        w.title.set('X'*10000)
        self.assertFalse(w.apply_live())
        self.assertIs(w.session, good)
        w.undo()
        successor = section('Následující.')
        w.add_section(successor)
        w.selected_id = self.s.id
        w.delete_section()
        self.assertTrue(w.apply_live())
        self.assertEqual(next(s for s in w.session.plan.slides if s.id == w.session.current_slide_id).section_id, successor.id)

    def test_sentence_replacement_with_delete_insert_and_black_end_undo(self):
        w = self.w
        w.text.delete('1.0', '1.13')
        w.text.insert('1.0', 'Opravená věta. ')
        self.root.update()
        self.assertEqual(w.live_anchor.offset, 0)
        self.assertTrue(w.apply_live())
        w.jump(len(w.plan.slides)-1)
        self.assertTrue(w.plan.slides[w.current].id.endswith(':end'))
        original = w.session
        w.view_version.set('draft')
        w.switch_version()
        w.jump(len(w.plan.slides)-1)
        from types import SimpleNamespace
        w.delete_black_slide(SimpleNamespace(widget=w.preview))
        self.assertIs(w.session.plan, original.plan)
        w.undo()
        w.redo()
        self.assertTrue(w.apply_live())
        self.assertFalse(w.plan.slides[w.current].black)
        # Empty replacement has a stable, usable session and can be undone.
        w.commit(replace(w.document, sections=(), black_start=False, black_end=False))
        self.assertTrue(w.apply_live())
        self.assertIsNone(w.session.current_slide_id)
        w.undo()
        self.assertTrue(w.apply_live())
        self.assertIsNotNone(w.session.current_slide_id)

    def test_prepend_first_slide_and_word_at_continuation_use_natural_plan(self):
        w = self.w
        w.text.insert('1.0', 'Přidaná úvodní věta. ')
        self.root.update()
        self.assertTrue(w.apply_live())
        first = next(s for s in w.plan.slides if not s.black)
        self.assertEqual(w.session.current_slide_id, first.id)
        self.assertTrue(anchors.text(w.document.sections[0].blocks[0]).startswith('Přidaná úvodní věta. '))
        a = self.continuation()
        w.text.insert(f'1.0+{a.offset}c', 'NOVÉ ')
        self.root.update()
        target = w.live_anchor
        self.assertEqual(target.offset, a.offset+5)
        self.assertTrue(w.apply_live())
        self.assertEqual(w.session.plan, paginate(w.document, w.metrics, w.typography))
        self.assert_contains(w.session.plan, w.session.current_slide_id, target)
        # The complete text, including the inserted word, occurs exactly once.
        actual = ''.join(r.text for r in w.document.sections[0].blocks[0].runs)
        runs = {r.id: r.text for r in w.document.sections[0].blocks[0].runs}
        reconstructed = ''.join(runs[r.run_id][r.start:r.end] for s in w.plan.slides for r in s.ranges)
        self.assertEqual(reconstructed, actual)

    def test_preview_switch_maps_content_without_projecting_preview_selection(self):
        w = self.w
        a = self.continuation()
        original_id = w.session.current_slide_id
        w.text.insert('1.0', 'Předchozí text. '*30)
        self.root.update()
        w.rebuild()
        mapped = w.live_anchor
        w.view_version.set('draft')
        w.switch_version()
        self.assert_contains(w.plan, w.plan.slides[w.current].id, mapped)
        w.view_version.set('live')
        w.switch_version()
        self.assertEqual(w.plan.slides[w.current].id, original_id)
        self.assertEqual(w.session.current_slide_id, original_id)
        w.view_version.set('draft')
        w.switch_version()
        w.jump(len(w.plan.slides)-1)  # Shared black end, not the live content.
        w.view_version.set('live')
        w.switch_version()
        self.assertTrue(w.plan.slides[w.current].id.endswith(':end'))
        self.assertEqual(w.session.current_slide_id, original_id)
        self.assertIn('Promítá se snímek', w.version_status.get())
        # Only explicit navigation in the live view moves the outputs.
        w.thumbnail_clicked(w.current)
        self.assertEqual(w.session.current_slide_id, w.plan.slides[w.current].id)

    def test_switch_maps_block_identity_and_deleted_block_fallback(self):
        w = self.w
        first, middle, last = (TextBlock((TextRun('Opakovaná věta. '*30),)) for _ in range(3))
        s = replace(w.document.sections[0], blocks=(first, middle, last))
        w.update_section(s)
        self.assertTrue(w.apply_live())
        index = next(i for i, slide in enumerate(w.plan.slides) if slide.ranges and slide.ranges[0].block_id == middle.id)
        w.jump(index)
        original_id = w.session.current_slide_id
        w.update_section(replace(s, blocks=(first, last)))
        w.rebuild()
        w.view_version.set('draft')
        w.switch_version()
        selected = w.plan.slides[w.current]
        self.assertTrue(any(r.block_id == last.id for r in selected.ranges))
        self.assertEqual(w.session.current_slide_id, original_id)

    def prepare_three_pages(self):
        w = self.w
        # Preserve the real font/layout boundaries and stable source identities.
        full = replace(w.document, sections=(self.s,))
        content = [s for s in paginate(full, w.metrics, w.typography).slides if not s.black]
        self.assertGreaterEqual(len(content), 3)
        end = content[2].ranges[-1].end
        block = self.s.blocks[0]
        short = replace(self.s, blocks=(replace(block, runs=(replace(block.runs[0], text=block.runs[0].text[:end]),)),))
        w.commit(replace(full, sections=(short,)))
        w.selected_id = short.id
        w.load_editor()
        self.assertTrue(w.apply_live())
        content = [s for s in w.plan.slides if not s.black]
        self.assertEqual(len(content), 3)
        return content

    def test_three_pages_shrink_to_two_keep_second_or_clamp_third(self):
        w = self.w
        for ordinal, remaining_count in ((1, 2), (2, 2), (2, 1)):
            with self.subTest(original_continuation=ordinal+1, remaining_count=remaining_count):
                content = self.prepare_three_pages()
                index = next(i for i, s in enumerate(w.plan.slides) if s.id == content[ordinal].id)
                w.jump(index)
                old = w.session
                visible = self.canvas_text()
                cut = content[2-remaining_count].ranges[-1].end
                w.text.delete('1.0', f'1.0+{cut}c')
                self.root.update()
                w.rebuild()
                remaining = [s for s in w.draft_plan.slides if not s.black]
                self.assertEqual(len(remaining), remaining_count)
                self.assertIs(w.session.plan, old.plan)
                self.assertEqual(self.canvas_text(), visible)
                # Also confirm from a draft preview at an unrelated place.
                w.view_version.set('draft')
                w.switch_version()
                w.jump(0)
                self.assertTrue(w.apply_live())
                content = [s for s in w.plan.slides if not s.black]
                selected = content[min(ordinal, remaining_count-1)]
                self.assertEqual(w.session.current_slide_id, selected.id)
                self.assertEqual(w.plan.slides[w.current].id, selected.id)
                for output, window in w.projections.items():
                    actual = [window.canvas.itemcget(i, 'text') for i in window.canvas.find_all() if window.canvas.type(i) == 'text']
                    expected = [p.text.replace('\t', '    ').replace('\r', '') for p in getattr(selected, output).pieces]
                    self.assertEqual(actual, expected)

    def test_small_edit_on_second_of_two_pages_keeps_second(self):
        w = self.w
        content = self.prepare_three_pages()
        w.text.delete(f'1.0+{content[1].ranges[-1].end}c', 'end-1c')
        self.root.update()
        self.assertTrue(w.apply_live())
        content = [s for s in w.plan.slides if not s.black]
        self.assertEqual(len(content), 2)
        w.jump(next(i for i, s in enumerate(w.plan.slides) if s.id == content[1].id))
        # The previous anchor would migrate to the preceding page.
        w.text.delete('1.0', '1.1')
        self.root.update()
        self.assertTrue(w.apply_live())
        content = [s for s in w.plan.slides if not s.black]
        self.assertEqual(len(content), 2)
        self.assertEqual(w.session.current_slide_id, content[1].id)

    def test_continuation_survives_move_and_preceding_section_removal(self):
        w = self.w
        content = self.prepare_three_pages()
        current_section = w.document.sections[0]
        before = section('Jiný úsek před textem.')
        after = section('Jiný úsek za textem.')
        w.commit(replace(w.document, sections=(before, current_section, after)))
        self.assertTrue(w.apply_live())
        target = next(s for s in w.plan.slides if s.section_id == current_section.id and s.id == content[1].id)
        w.jump(next(i for i, s in enumerate(w.plan.slides) if s.id == target.id))
        w.commit(replace(w.document, sections=(after, replace(current_section, break_before=False))))
        self.assertTrue(w.apply_live())
        content = [s for s in w.plan.slides if s.section_id == current_section.id and not s.black]
        self.assertEqual(w.session.current_slide_id, content[1].id)

    def test_mouse_thumbnail_focus_keeps_selected_and_projected_borders(self):
        w = self.w
        self.root.deiconify()
        self.root.update()
        for index in (0, 1, 2, 1):
            canvas = w.thumbnails[index]
            canvas.event_generate('<Button-1>', x=10, y=10)
            canvas.focus_force()
            self.root.update()
            self.assertIs(self.root.focus_get(), canvas)
            self.assertEqual(w.session.current_slide_id, w.plan.slides[index].id)
            for i, thumbnail in enumerate(w.thumbnails):
                color = '#00bfff' if i == index else '#666666'
                self.assertEqual(thumbnail.cget('highlightbackground'), color)
                self.assertEqual(thumbnail.cget('highlightcolor'), color)
        # A separately previewed live slide must not lose the green live marker
        # when focus lands on it without a navigation click.
        projected = w.session.current_slide_id
        w.view_version.set('draft')
        w.switch_version()
        w.jump(len(w.plan.slides)-1)
        w.view_version.set('live')
        w.switch_version()
        actual = next(i for i, s in enumerate(w.plan.slides) if s.id == projected)
        w.thumbnails[actual].focus_force()
        self.root.update()
        self.assertEqual(w.thumbnails[actual].cget('highlightcolor'), '#36b36b')
        self.assertEqual(w.session.current_slide_id, projected)


if __name__ == '__main__':
    unittest.main()
