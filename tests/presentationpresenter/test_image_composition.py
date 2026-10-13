"""Mixed-content layout, portable v2, camera tolerance and editing regressions."""
import io
import json
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from presentationpresenter.domain import *
from presentationpresenter import media, persistence, storage
from presentationpresenter.composition import compose_pair, constrain, normalize, CAMERA_OVERLAP_TOP, CAMERA_OVERLAP_LEFT, camera_core, grid
from presentationpresenter.layout import paginate, Rect, geometry
from presentationpresenter.rendering import TkMetrics, draw
from presentationpresenter.editor import duplicate_section
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings

def asset(size=(400, 200), color='orange'):
    raw = io.BytesIO()
    Image.new('RGB', size, color).save(raw, 'PNG')
    return media.from_bytes(raw.getvalue())

def source(text='', count=2):
    assets = tuple(asset((400, 200) if n%2 == 0 else (200, 400), 'orange' if n%2 == 0 else 'blue') for n in range(count))
    section = TextSection('', (TextBlock((TextRun(text),)),), images=tuple(ImageItem(a.id) for a in assets), break_after=False, break_before=True)
    return Presentation(sections=(section,), media=assets, black_start=False, black_end=True)

class GeometryTests(unittest.TestCase):
    def test_grid_and_ratios_all_output_aspects(self):
        for hall in Aspect:
            for stream in Aspect:
                for count in (1, 2, 3, 6):
                    doc = replace(source(count=count), hall=OutputConfig(hall), stream=OutputConfig(stream, CameraRegion()))
                    layouts = compose_pair(doc, doc.sections[0])
                    for layout in layouts:
                        self.assertEqual(len(layout.images), count)
                        for index, item in enumerate(layout.images):
                            size = media.dimensions(doc.media[index].locator)
                            self.assertAlmostEqual(item.box.width/item.box.height, size[0]/size[1])
                            self.assertGreaterEqual(item.box.x, 0)
                            self.assertLessEqual(item.box.x+item.box.width, layout.width+1e-8)
                            self.assertLessEqual(item.box.y+item.box.height, layout.height+1e-8)
                            if layout.exclusion:
                                self.assertFalse(item.box.intersects(layout.exclusion))
                            self.assertFalse(any(item.box.intersects(other.box) for other in layout.images[index+1:]))

    def test_camera_asymmetric_limit_and_editor_only_warning(self):
        doc = source(count=1)
        w, h, camera, _ = geometry(doc.stream)
        allowance = camera.height*CAMERA_OVERLAP_LEFT
        proposed = Rect(camera.x-200, camera.y+80, 200+allowance, (200+allowance)/2)
        box = constrain(proposed, doc.stream)
        self.assertAlmostEqual(box.x+box.width-camera.x, allowance)
        for proposed in (Rect(camera.x-100, camera.y+30, 300, 150), Rect(camera.x+30, camera.y-50, 400, 200), Rect(w-40, h-40, 300, 150)):
            box = constrain(proposed, doc.stream)
            core = camera_core(camera)
            self.assertFalse(box.intersects(core))
            self.assertLessEqual(box.x+box.width, w+1e-8)
            self.assertLessEqual(box.y+box.height, h+1e-8)
        top = camera.height*CAMERA_OVERLAP_TOP
        above = Rect(camera.x+100, camera.y-150, 300, 150+top)
        self.assertEqual(constrain(above, doc.stream), above)
        self.assertAlmostEqual(above.y+above.height-camera.y, top)
        custom = OutputConfig(Aspect.WIDE, CameraRegion(.2, .25, .3, .4, .02))
        _, _, c, _ = geometry(custom)
        right_edge = Rect(c.x+c.width-c.height*.05, c.y+70, 100, 80)
        self.assertEqual(constrain(right_edge, custom), right_edge)

    def test_camera_layout_uses_left_bottom_for_portrait_and_three_images(self):
        config = OutputConfig(Aspect.WIDE, CameraRegion())
        _, _, _, exclusion = geometry(config)
        two = grid(((360, 520), (900, 420)), config)
        self.assertGreater(two[0].y+two[0].height, exclusion.y+100)
        self.assertLessEqual(two[0].x+two[0].width, exclusion.x+1e-8)
        self.assertGreaterEqual(two[1].x, exclusion.x)
        self.assertLessEqual(two[1].y+two[1].height, exclusion.y+1e-8)
        sizes = ((360, 520), (900, 420), (400, 520))
        reference = grid(sizes, OutputConfig(Aspect.STANDARD))
        three = grid(sizes, config, reference=reference)
        self.assertLessEqual(three[0].y+three[0].height, three[2].y)
        self.assertGreater(three[2].y+three[2].height, exclusion.y+100)
        self.assertLessEqual(three[2].x+three[2].width, exclusion.x+1e-8)
        self.assertLessEqual(three[1].y+three[1].height, exclusion.y+1e-8)

    def test_varied_camera_and_larger_combinations(self):
        sizes = ((350, 600), (1200, 400), (480, 640), (500, 500), (900, 600), (300, 900), (750, 400), (400, 700), (800, 800))
        for config, count in ((OutputConfig(Aspect.WIDE, CameraRegion(.2, .25, .3, .4, .02)), 8),
                              (OutputConfig(Aspect.STANDARD, CameraRegion()), 9)):
            boxes = grid(sizes[:count], config)
            w, h, _, exclusion = geometry(config)
            self.assertEqual(len(boxes), count)
            for index, box in enumerate(boxes):
                self.assertAlmostEqual(box.width/box.height, sizes[index][0]/sizes[index][1])
                self.assertGreaterEqual(box.x, 0)
                self.assertGreaterEqual(box.y, 0)
                self.assertLessEqual(box.x+box.width, w+1e-8)
                self.assertLessEqual(box.y+box.height, h+1e-8)
                self.assertFalse(box.intersects(exclusion))
                self.assertFalse(any(box.intersects(other) for other in boxes[index+1:]))

    def test_linked_relative_size_order_and_independent_stream(self):
        doc = source(count=2)
        section = doc.sections[0]
        images = (replace(section.images[0], hall=ImagePlacement(.05, .05, .25)),
                  replace(section.images[1], hall=ImagePlacement(.55, .4, .15)))
        section = replace(section, images=images)
        doc = replace(doc, sections=(section,))
        hall, stream = compose_pair(doc, section)
        self.assertLess(stream.images[0].box.x, stream.images[1].box.x)
        self.assertLess(stream.images[0].box.y, stream.images[1].box.y)
        self.assertAlmostEqual(hall.images[0].box.width/hall.images[1].box.width,
                               stream.images[0].box.width/stream.images[1].box.width)
        before = stream.images[0].box.width
        larger = replace(section, images=(replace(images[0], hall=ImagePlacement(.05, .05, .3)), images[1]))
        self.assertGreater(compose_pair(doc, larger)[1].images[0].box.width, before)
        frozen = replace(section, stream_linked=False, images=tuple(replace(i, stream=normalize(p.box, doc.stream)) for i, p in zip(section.images, stream.images)))
        moved = replace(frozen, images=(replace(frozen.images[0], hall=ImagePlacement(.1, .1, .4)), frozen.images[1]))
        self.assertEqual(compose_pair(doc, frozen)[1], compose_pair(doc, moved)[1])

    def test_portable_v2_and_v1_migration(self):
        doc = source('Text')
        section = replace(doc.sections[0], stream_linked=False, images=tuple(replace(i, hall=ImagePlacement(.1, .2, .15), stream=ImagePlacement(.1, .1, .2), repeat=False) for i in doc.sections[0].images))
        doc = replace(doc, sections=(section,))
        self.assertEqual(persistence.loads(persistence.dumps(doc)), doc)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'new.ppres'
            storage.save(path, doc)
            self.assertEqual(json.loads(path.read_text())['version'], 2)
            self.assertEqual(storage.load(path), doc)
            v1 = json.loads(persistence.dumps(doc))
            v1['schema_version'] = 1
            for s in v1['sections']:
                s.pop('images')
                s.pop('stream_linked')
            path.write_text(json.dumps({'format': 'PresentationPresenter', 'version': 1, 'document': v1}), encoding='utf-8')
            loaded = storage.load(path)
            self.assertEqual(loaded.schema_version, 2)
            self.assertEqual(loaded.id, doc.id)
            self.assertEqual(loaded.sections[0].id, section.id)
            self.assertEqual(loaded.sections[0].images, ())
            for field, value in (('repeat', 'false'), ('hall', {'x': float('nan'), 'y': 0, 'width': .3})):
                invalid = json.loads(persistence.dumps(doc))
                invalid['sections'][0]['images'][0][field] = value
                with self.assertRaises(ValueError):
                    persistence.loads(json.dumps(invalid))

class MixedTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.metrics = TkMetrics(self.root)
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()

    def test_complete_text_wrap_repeat_and_first_only(self):
        text = 'Odstavec s obrázky a dlouhým společným textem. ' * 75
        for ha in Aspect:
            for sa in Aspect:
                doc = replace(source(text, count=2), hall=OutputConfig(ha), stream=OutputConfig(sa, CameraRegion()))
                section = doc.sections[0]
                section = replace(section, images=(replace(section.images[0], repeat=False), section.images[1]))
                doc = replace(doc, sections=(section,))
                plan = paginate(doc, self.metrics)
                slides = [s for s in plan.slides if not s.black]
                self.assertGreater(len(slides), 1)
                reconstructed = ''.join(text[r.start:r.end] for s in slides for r in s.ranges)
                self.assertEqual(reconstructed, text)
                for index, slide in enumerate(slides):
                    for output in ('hall', 'stream'):
                        layout = getattr(slide, output)
                        self.assertEqual(len(layout.images), 2 if index == 0 else 1)
                        for piece in layout.pieces:
                            if piece.text:
                                self.assertFalse(any(piece.box.intersects(p.box) for p in layout.images))
                                if layout.exclusion:
                                    self.assertFalse(piece.box.intersects(layout.exclusion))
                    hall = [(p.source.run_id, p.source.start, p.source.end) for p in slide.hall.pieces if p.source]
                    stream = [(p.source.run_id, p.source.start, p.source.end) for p in slide.stream.pieces if p.source]
                    self.assertEqual(''.join(text[a:b] for _, a, b in hall), ''.join(text[a:b] for _, a, b in stream))
                duplicate = duplicate_section(section, slides[-1])
                self.assertEqual(len(duplicate.images), 1)
                self.assertNotEqual(duplicate.images[0].id, section.images[1].id)

    def test_empty_section_insertion_edit_mouse_and_isolation(self):
        w = MainWindow(self.root, AppSettings(), recovery_dir=Path(self.temp.name)/'recovery')
        old = w.document
        sid = w.selected_id
        path = Path(self.temp.name)/'picture.png'
        raw = io.BytesIO()
        Image.new('RGB', (400, 200), 'green').save(raw, 'PNG')
        path.write_bytes(raw.getvalue())
        w.insert_image(path)
        self.assertEqual(len(w.document.sections), 1)
        self.assertEqual(w.document.sections[0].id, sid)
        w.insert_image(path)
        self.assertEqual(len(w.document.sections[0].images), 2)
        w.undo()
        w.undo()
        self.assertEqual(w.document, old)
        w.redo()
        w.redo()
        w.edit_images()
        editor = w.image_editor
        self.root.update()
        editor.values['width'].set('25')
        editor.values['x'].set('5')
        editor.values['y'].set('5')
        editor.apply_fields()
        self.assertAlmostEqual(w.document.sections[0].images[0].hall.width, .25)
        from presentationpresenter.session import ProjectionSession
        w.session = ProjectionSession.confirm(w.draft_plan)
        previous = w.session
        editor.output.set('stream')
        editor.refresh()
        editor.values['width'].set('15')
        editor.values['x'].set('5')
        editor.values['y'].set('5')
        editor.apply_fields()
        self.assertFalse(w.document.sections[0].stream_linked)
        fixed = compose_pair(w.document, w.document.sections[0])[1]
        editor.output.set('hall')
        editor.refresh()
        placed = editor.layout.images[0]
        b = placed.box
        x = editor.origin[0]+(b.x+b.width/2)*editor.scale
        y = editor.origin[1]+(b.y+b.height/2)*editor.scale
        editor.press(SimpleNamespace(x=x, y=y))
        editor.motion(SimpleNamespace(x=x+15, y=y+10))
        editor.release(SimpleNamespace(x=x+15, y=y+10))
        self.assertEqual(compose_pair(w.document, w.document.sections[0])[1], fixed)
        self.assertIs(w.session, previous)
        editor.repeat.set(False)
        editor.change_repeat()
        self.assertFalse(w.document.sections[0].images[0].repeat)
        editor.recalculate()
        self.assertFalse(w.document.sections[0].stream_linked)
        editor.linked.set(True)
        editor.change_link()
        self.assertTrue(w.document.sections[0].stream_linked)
        editor.window.destroy()
        self.assertIsNone(w.image_editor)

    def test_camera_warning_never_drawn_on_projection(self):
        doc = source(count=1)
        w, h, camera, _ = geometry(doc.stream)
        tolerance = camera.height*CAMERA_OVERLAP_LEFT
        box = Rect(camera.x-200, camera.y+80, 200+tolerance, (200+tolerance)/2)
        section = replace(doc.sections[0], stream_linked=False,
                          images=(replace(doc.sections[0].images[0], stream=normalize(box, doc.stream)),))
        doc = replace(doc, sections=(section,))
        slide = next(s for s in paginate(doc, self.metrics).slides if not s.black)
        self.assertTrue(any('zakryje kamera' in s for s in slide.stream.warnings))
        canvas = tk.Canvas(self.root)
        draw(canvas, slide, 'stream', self.metrics, None, show_camera=True)
        self.assertTrue(canvas.find_withtag('camera-warning'))
        draw(canvas, slide, 'stream', self.metrics, None, show_camera=False)
        self.assertFalse(canvas.find_withtag('camera-warning'))

    def test_full_first_only_image_can_precede_text_without_loss(self):
        doc = source('Následující text. '*20, count=1)
        section = doc.sections[0]
        section = replace(section, images=(replace(section.images[0], hall=ImagePlacement(0, 0, 1), repeat=False),))
        doc = replace(doc, sections=(section,))
        # A 4:3 media asset fills the entire 4:3 hall and obstructs every row.
        full = asset((400, 300))
        doc = replace(doc, media=(full,), sections=(replace(section, images=(replace(section.images[0], media_id=full.id),)),))
        plan = paginate(doc, self.metrics)
        content = [s for s in plan.slides if not s.black]
        self.assertEqual(len(content[0].hall.images), 1)
        self.assertFalse(content[0].ranges)
        self.assertFalse(content[1].hall.images)
        text = doc.sections[0].blocks[0].runs[0].text
        self.assertEqual(''.join(text[r.start:r.end] for s in content for r in s.ranges), text)

    def test_mixed_two_projection_windows_publish_and_resize(self):
        from presentationpresenter.projection import Monitor
        w = MainWindow(self.root, AppSettings(), recovery_dir=Path(self.temp.name)/'recovery')
        w.commit(source('Text vedle obrázků. '*30))
        w.rebuild()
        inventory = [Monitor('A', 0, 0, 800, 600), Monitor('B', -640, 0, 640, 360)]
        with patch('presentationpresenter.ui.monitors', return_value=inventory):
            w.monitor_choices['hall'].set('A')
            w.monitor_choices['stream'].set('B')
            for output in ('hall', 'stream'):
                w.projection_controls.fullscreen[output] = False
            self.assertTrue(w.start_projection(('hall', 'stream')))
            w.jump(1)
            self.root.update()
            previous = w.session
            for window in w.projections.values():
                self.assertEqual(sum(window.canvas.type(i) == 'image' for i in window.canvas.find_all()), 2)
                self.assertFalse(window.canvas.find_withtag('camera-warning'))
            w.edit_images()
            editor = w.image_editor
            self.root.update()
            b = editor.layout.images[0].box
            x = editor.origin[0]+(b.x+b.width)*editor.scale
            y = editor.origin[1]+(b.y+b.height)*editor.scale
            editor.press(SimpleNamespace(x=x, y=y))
            self.assertTrue(editor.drag[3])
            editor.release(SimpleNamespace(x=x-20, y=y-10))
            self.assertIs(w.session, previous)
            self.assertTrue(w.apply_live())
            for window in w.projections.values():
                self.assertEqual(sum(window.canvas.type(i) == 'image' for i in window.canvas.find_all()), 2)
                self.assertFalse(window.canvas.find_withtag('camera-warning'))

if __name__ == '__main__':
    unittest.main()
