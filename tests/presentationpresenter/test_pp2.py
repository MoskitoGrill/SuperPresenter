import tkinter as tk
import unittest
from dataclasses import replace
from presentationpresenter.domain import *
from presentationpresenter.layout import *
from presentationpresenter.rendering import TkMetrics, draw
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings


def stress_document():
    return Presentation(sections=(TextSection('Dělení textu', (
        TextBlock((TextRun('Začátek odstavce. '+('Slova českého textu a příklady. '*35)), TextRun(' Tučně a barevně. '*8, TextStyle(True, True, True, '#ffd166')))),
        TextBlock((TextRun('Celá odrážka '+('s několika řádky '*8)),), BlockKind.BULLET),
        TextBlock((TextRun('Velmi dlouhá odrážka '+('opakovaná slova '*260)),), BlockKind.BULLET),
        TextBlock((TextRun('W'*230+'\nNový řádek.  Mezery na konci.   '),)),
    ), reference='Odkaz 1:1–12'), TextSection('Prázdný úsek', ()), TextSection('Bez předělu', (TextBlock((TextRun('Konec.'),)),), break_after=False)))

class PaginationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()
        cls.metrics = TkMetrics(cls.root)
    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def verify(self, source, plan):
        expected = {(s.id,b.id,r.id):r.text for s in source.sections if isinstance(s, TextSection) for b in s.blocks for r in b.runs}
        offsets = {key:0 for key in expected}
        reconstructed = {key:'' for key in expected}
        for slide in plan.slides:
            if slide.black:
                continue
            for span in slide.ranges:
                key = span.section_id, span.block_id, span.run_id
                self.assertEqual(span.start, offsets[key])
                reconstructed[key] += expected[key][span.start:span.end]
                offsets[key] = span.end
            for output in ('hall','stream'):
                layout = getattr(slide, output)
                actual = []
                for piece in layout.pieces:
                    if piece.source:
                        actual.append(piece.source)
                    self.assertGreaterEqual(piece.box.x, 32)
                    self.assertLessEqual(piece.box.x+piece.box.width, layout.width-32+.001)
                    self.assertLessEqual(piece.box.y+piece.box.height, layout.height-32+.001)
                    if layout.exclusion:
                        self.assertFalse(piece.box.intersects(layout.exclusion), piece)
                # Different wrapping must partition exactly the same ordered source ranges.
                def flatten(spans):
                    return [(s.run_id, i) for s in spans for i in range(s.start,s.end)]
                self.assertEqual(flatten(actual), flatten(slide.ranges))
        self.assertEqual(reconstructed, expected)
        self.assertFalse(any(a.black and b.black for a,b in zip(plan.slides,plan.slides[1:])))

    def test_four_aspect_combinations_and_real_canvas_ink(self):
        for hall in Aspect:
            for stream in Aspect:
                with self.subTest(hall=hall,stream=stream):
                    source = replace(stress_document(), hall=OutputConfig(hall),stream=OutputConfig(stream,CameraRegion()))
                    plan = paginate(source,self.metrics)
                    self.verify(source,plan)
                    self.assertGreater(len(plan.slides), 5)
                    for slide in plan.slides:
                        if slide.black:
                            continue
                        for output in ('hall','stream'):
                            canvas = tk.Canvas(self.root)
                            draw(canvas,slide,output,self.metrics,Typography(),show_camera=False)
                            self.root.update_idletasks()
                            layout = getattr(slide,output)
                            for item in canvas.find_all():
                                box = canvas.bbox(item)
                                self.assertGreaterEqual(box[0], 32)
                                self.assertGreaterEqual(box[1], 32)
                                self.assertLessEqual(box[2], layout.width-32)
                                self.assertLessEqual(box[3], layout.height-32)
                                if layout.exclusion and box:
                                    self.assertFalse(Rect(box[0],box[1],box[2]-box[0],box[3]-box[1]).intersects(layout.exclusion))
                            canvas.destroy()
                    self.assertEqual(plan,paginate(source,self.metrics))

    def test_bullet_moves_whole_and_oversized_bullet_continues(self):
        bullet = TextBlock((TextRun('odrážka '*50),),BlockKind.BULLET)
        source = Presentation(sections=(TextSection('Název',(TextBlock((TextRun('úvod '*140),)),bullet)),))
        plan = paginate(source,self.metrics)
        bullet_slides = [s for s in plan.slides if any(r.block_id==bullet.id for r in s.ranges)]
        self.assertEqual(len(bullet_slides),1)
        self.assertEqual(bullet_slides[0].ranges[0].block_id,bullet.id)
        long_plan = paginate(stress_document(),self.metrics)
        self.assertTrue(any(p.text=='↳' for s in long_plan.slides if not s.black for p in s.stream.pieces))

    def test_movable_camera_and_long_heading(self):
        for camera in (CameraRegion(.2,.35,.4,.3,.04),CameraRegion(0,.5,.5,.5),CameraRegion(.5,0,.5,.5)):
            source = replace(stress_document(),stream=OutputConfig(Aspect.STANDARD,camera))
            self.verify(source,paginate(source,self.metrics))
        source = Presentation(sections=(TextSection('Dlouhý název '*20,(TextBlock((TextRun('Obsah'),)),)),))
        self.verify(source,paginate(source,self.metrics))
        with self.assertRaises(LayoutError):
            paginate(replace(source,sections=(replace(source.sections[0],title='W'*10000),)),self.metrics)

    def test_break_flags_empty_blocks_and_format_boundaries(self):
        source = Presentation(black_start=False,sections=(TextSection('Bez černé\nDalší řádek',(TextBlock(()), TextBlock((TextRun('slovo'),TextRun('navazuje',TextStyle(italic=True)),TextRun('\n\nKonec\ttext\r\n')))),break_after=False),))
        plan = paginate(source,self.metrics)
        self.verify(source,plan)
        self.assertFalse(any(s.black for s in plan.slides))

    def test_ui_rebuild_both_outputs(self):
        window = MainWindow(self.root,AppSettings())
        for hall in Aspect:
            for stream in Aspect:
                window.change_aspect('hall',hall.value)
                window.change_aspect('stream',stream.value)
                self.root.update()
                self.assertEqual(window.plan.source.hall.aspect,hall)
                self.assertEqual(window.plan.source.stream.aspect,stream)
        # No close(): tests do not save real user preferences.

    def test_many_empty_paragraphs_keep_block_identities(self):
        blocks = tuple(TextBlock(()) for _ in range(30))
        source = Presentation(sections=(TextSection('Prázdné odstavce',blocks),))
        plan = paginate(source,self.metrics)
        self.assertEqual([b for s in plan.slides for b in s.block_ids], [b.id for b in blocks])
        self.assertGreater(len([s for s in plan.slides if not s.black]),1)

if __name__=='__main__':
    unittest.main()
