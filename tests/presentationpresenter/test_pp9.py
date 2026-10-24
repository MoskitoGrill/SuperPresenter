"""PP9: preflight, damaged drafts, lifecycle and larger real-font plans."""
import io
import tempfile
import tkinter as tk
import unittest
from dataclasses import replace
from unittest.mock import patch
from PIL import Image
from presentationpresenter.domain import *
from presentationpresenter.layout import paginate, Typography, Rect
from presentationpresenter.media import from_bytes
from presentationpresenter.preflight import check
from presentationpresenter.projection import Monitor, configure_dpi
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow

configure_dpi()


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.inventory = [Monitor('QA', 0, 0, 1024, 768)]
        self.discovery = patch('presentationpresenter.ui.monitors', return_value=self.inventory)
        self.discovery.start()
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.w = MainWindow(self.root, AppSettings(), recovery_dir=self.temp.name)
        self.w.projection_controls.fullscreen = dict(hall=False, stream=False)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.discovery.stop()
        self.temp.cleanup()
        self.assertEqual(self.errors, [])

    def check(self, document, plan=None, outputs=('hall',)):
        return check(document, self.w.metrics, self.w.typography, self.inventory,
                     dict(hall='QA', stream='QA'), dict(hall=False, stream=False), outputs, plan)

    def image(self):
        stream = io.BytesIO()
        Image.new('RGB', (300, 200), 'blue').save(stream, 'PNG')
        return from_bytes(stream.getvalue())

    def test_output_checks_and_multiple_unlayoutable_sections(self):
        w = self.w
        sections = tuple(TextSection('titulek '*2000, (TextBlock((TextRun('Text'),)),)) for _ in range(2))
        doc = replace(w.document, sections=sections)
        issues = self.check(doc)
        self.assertEqual({i.section_id for i in issues}, {s.id for s in sections})
        w.projection_controls.enabled = dict(hall=True, stream=True)
        w.projection_controls.fullscreen['stream'] = True
        self.assertTrue(any('stejném monitoru' in i.message for i in w.collect_preflight()))
        w.monitor_choices['hall'].set('gone')
        self.assertTrue(any(i.output == 'hall' and 'dostupný' in i.message for i in w.collect_preflight()))
        self.assertFalse(w.start_projection(()))
        self.assertIsNone(w.session)

    def test_monitor_discovery_failure_does_not_use_stale_inventory(self):
        w = self.w
        with patch('presentationpresenter.ui.monitors', side_effect=RuntimeError('QA nedostupné')):
            self.assertFalse(w.start_projection(('hall',)))
            self.assertTrue(any('Nelze ověřit monitory' in i.message for i in w.collect_preflight()))
            self.assertIsNone(w.session)
        self.assertTrue(w.start_projection(('hall',)))

    def test_media_failure_is_reported_and_live_draft_survives(self):
        w = self.w
        self.assertTrue(w.start_projection(('hall',)))
        session = w.session
        bad = MediaAsset('data:image/png;base64,broken', 'image/png')
        section = TextSection('Vadný obrázek', (), images=(ImageItem(bad.id),))
        w.commit(replace(w.document, sections=w.document.sections+(section,), media=(bad,)))
        w.rebuild()
        self.assertIs(w.session, session)
        self.assertFalse(w.apply_live())
        self.assertIs(w.session, session)
        issues = w.collect_preflight()
        issue = next(i for i in issues if i.section_id == section.id)
        w.show_preflight()
        w.navigate_preflight(issue)
        self.assertEqual(w.selected_id, section.id)
        self.assertFalse(w.viewing_live())
        self.assertIs(w.session, session)
        w.preflight_window.refresh()
        self.root.update()
        self.assertTrue(w.preflight_window.tree.get_children())
        self.assertEqual(w.preflight_window.tree.cget('style'), 'PP.Preflight.Treeview')

    def test_geometry_checks_and_allowed_camera_warning(self):
        asset = self.image()
        section = TextSection('', (), images=(ImageItem(asset.id, stream=ImagePlacement(.1, .1, .2)),), stream_linked=False)
        doc = replace(self.w.document, sections=(section,), media=(asset,))
        plan = paginate(doc, self.w.metrics)
        self.assertFalse(self.check(doc, plan))
        slide = next(s for s in plan.slides if not s.black)
        image = slide.stream.images[0]
        # 10 px into the left camera edge is within the accepted tolerance.
        allowed = replace(slide.stream, images=(replace(image, box=Rect(480, 400, 170, 100)),), warnings=('Část obrázku zakryje kamera.',))
        changed = replace(plan, slides=tuple(replace(s, stream=allowed) if s.id == slide.id else s for s in plan.slides))
        self.assertTrue(self.check(doc, changed))
        self.assertFalse(any(i.blocking for i in self.check(doc, changed)))
        bad = replace(allowed, images=(replace(image, box=Rect(650, 400, 200, 100)),))
        changed = replace(plan, slides=tuple(replace(s, stream=bad) if s.id == slide.id else s for s in plan.slides))
        self.assertTrue(any(i.blocking and 'kamery' in i.message for i in self.check(doc, changed)))
        narrow = replace(bad, camera=Rect(650, 360, 10, 360))
        changed = replace(plan, slides=tuple(replace(s, stream=narrow) if s.id == slide.id else s for s in plan.slides))
        self.assertFalse(any(i.blocking for i in self.check(doc, changed)))

    def test_long_plans_all_aspects_and_complete_source(self):
        sections = tuple(TextSection(f'Úsek {n}', (TextBlock((TextRun('Příliš žluťoučký kůň. '*80, TextStyle(family='Calibri')),), BlockKind.NUMBERED, level=n % 3),), break_after=False, break_before=True) for n in range(25))
        for hall in Aspect:
            for stream in Aspect:
                doc = replace(self.w.document, sections=sections, hall=replace(self.w.document.hall, aspect=hall), stream=replace(self.w.document.stream, aspect=stream))
                plan = paginate(doc, self.w.metrics)
                self.assertFalse(self.check(doc, plan))
                for section in sections:
                    run = section.blocks[0].runs[0]
                    spans = [r for s in plan.slides for r in s.ranges if r.run_id == run.id]
                    self.assertEqual(''.join(run.text[r.start:r.end] for r in spans), run.text)

    def test_detects_text_overflow_camera_and_lost_range(self):
        doc = replace(self.w.document, sections=(TextSection('Text', (TextBlock((TextRun('Ověření'),)),)),))
        plan = paginate(doc, self.w.metrics)
        slide = next(s for s in plan.slides if not s.black)
        piece = slide.stream.pieces[-1]
        layout = replace(slide.stream, pieces=(replace(piece, box=Rect(900, 690, 500, 60)),))
        changed = replace(plan, slides=tuple(replace(s, stream=layout, ranges=()) if s.id == slide.id else s for s in plan.slides))
        issues = self.check(doc, changed)
        self.assertTrue(any('přetéká' in i.message for i in issues))
        self.assertTrue(any('rezervované' in i.message for i in issues))
        self.assertTrue(any('právě jednou' in i.message for i in issues))

    def test_report_navigation_never_projects_and_repeated_lifecycle(self):
        w = self.w
        asset = self.image()
        section = TextSection('Titulek '*2000, (TextBlock((TextRun('Obsah'),)),))
        w.commit(replace(w.document, sections=(section,), media=(asset,)))
        w.rebuild()
        self.assertFalse(w.start_projection(('hall',)))
        self.assertIsNone(w.session)
        self.assertIsNotNone(w.preflight_window)
        w.undo()
        w.rebuild()
        self.assertFalse(w.layout_failed)
        self.assertNotIn('Náhled není aktuální', w.status.get())
        for _ in range(5):
            self.assertTrue(w.start_projection(('hall', 'stream')))
            session = w.session
            w.show_preflight()
            self.assertIs(w.session, session)
            w.playback.start(.1, True)
            w.toggle_blackout()
            w.stop_projection()
            self.assertFalse(w.playback.running)
            self.assertFalse(w.projections)
            self.assertIsNone(w.session)
        self.root.update()

    def test_long_counter_and_minimum_editor_space(self):
        w = self.w
        for label in (w.location_label, w.header_location_label):
            self.assertGreaterEqual(label.winfo_reqwidth(), w.navigation_layout.counter_font.measure('99999/99999')+2)
        self.root.geometry('1100x650')
        self.root.update()
        w.workspace.sash_place(0, 0, 220)
        self.root.update_idletasks()
        w.flush_workspace_resize()
        self.assertGreater(w.text.winfo_height(), 1)


if __name__ == '__main__':
    unittest.main()
