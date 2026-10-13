import base64
import io
import json
import tempfile
import tkinter as tk
import unittest
import subprocess
import sys
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from PIL import Image
from presentationpresenter import media, storage
from presentationpresenter.domain import *
from presentationpresenter.editor import History, duplicate_section
from presentationpresenter.layout import paginate, image_layout
from presentationpresenter.rendering import TkMetrics, draw
from presentationpresenter.recovery import Recovery
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings

def raw_image(size=(600, 300)):
    stream = io.BytesIO()
    Image.new('RGB', size, '#ed8936').save(stream, 'PNG')
    return stream.getvalue()

def document():
    asset = media.from_bytes(raw_image())
    return Presentation(sections=(ImageSection('Obrázek', asset.id, break_after=False, break_before=True),), media=(asset,), black_start=False, black_end=True)

class StorageTests(unittest.TestCase):
    def test_portable_without_original_and_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            original = folder/'source.png'
            original.write_bytes(raw_image())
            asset = media.from_path(original)
            doc = replace(document(), media=(asset,), sections=(ImageSection('Foto', asset.id),),
                          hall=OutputConfig(Aspect.WIDE), stream=OutputConfig(Aspect.STANDARD, CameraRegion(.2, .3, .3, .4, .01)))
            storage.save(folder/'portable.ppres', doc)
            original.unlink()
            loaded = storage.load(folder/'portable.ppres')
            self.assertEqual(doc, loaded)
            self.assertEqual(media.dimensions(loaded.media[0].locator), (600, 300))
            self.assertNotIn('source.png', (folder/'portable.ppres').read_text())
            self.assertNotIn('monitor', (folder/'portable.ppres').read_text())

    def test_interrupted_replace_and_invalid_save_preserve_previous(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.ppres'
            doc = document()
            storage.save(path, doc)
            before = path.read_bytes()
            with patch('presentationpresenter.storage.os.replace', side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):
                    storage.save(path, replace(doc, title='New'))
            self.assertEqual(path.read_bytes(), before)
            with patch('presentationpresenter.storage.os.fsync', side_effect=OSError('write interrupted')):
                with self.assertRaises(OSError):
                    storage.save(path, replace(doc, title='Partial'))
            self.assertEqual(path.read_bytes(), before)
            bad = replace(doc, media=(replace(doc.media[0], locator='invalid'),))
            with self.assertRaises(ValueError):
                storage.save(path, bad)
            self.assertEqual(storage.load(path), doc)
            self.assertEqual(list(Path(directory).glob('*.tmp')), [])

    def test_corruption_versions_and_invalid_media(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'bad.ppres'
            encoded = json.loads(storage.encode(document()))
            invalid = [b'{', b'\xff', b'[]', b'null']
            for field, value in [('version', 99), ('version', True), ('format', 'other')]:
                invalid.append(json.dumps({**encoded, field: value}).encode())
            broken = json.loads(storage.encode(document()))
            broken['document']['media'][0]['locator'] = 'data:image/png;base64,bm90IGFuIGltYWdl'
            invalid.append(json.dumps(broken).encode())
            for payload in invalid:
                path.write_bytes(payload)
                with self.assertRaises(ValueError):
                    storage.load(path)

    def test_recovery_crash_clean_and_failed_write(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Recovery(directory)
            doc = document()
            first.write(doc)
            second = Recovery(directory)
            self.assertNotIn(first.path, second.candidates())
            first.release()  # OS releases the same lock when a process crashes.
            self.assertIn(first.path, second.candidates())
            self.assertEqual(storage.load(first.path), doc)
            with patch('presentationpresenter.storage.os.replace', side_effect=OSError('disk')):
                with self.assertRaises(OSError):
                    first.write(replace(doc, title='Not written'))
            self.assertEqual(storage.load(first.path), doc)
            first.release()
            second.write(replace(doc, title='Recovered'))
            second.clean()
            self.assertTrue(first.path.exists())

    def test_legacy_import_preserves_original_and_warns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'original.json'
            payload = json.dumps([{'link': 'Odkaz', 'text': 'A\nB', 'style': 'unsupported'},
                                  {'image': True, 'img_data': base64.b64encode(raw_image()).decode()},
                                  {'image': True, 'img_data': 'bad'}, 7]).encode()
            path.write_bytes(payload)
            doc, warnings = storage.import_legacy(path)
            self.assertEqual(len(doc.sections), 2)
            self.assertGreaterEqual(len(warnings), 4)
            self.assertEqual(path.read_bytes(), payload)
            storage.save(Path(directory)/'converted.ppres', doc)

    def test_actual_unclean_process_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            code = ('import os, sys; from presentationpresenter.recovery import Recovery; '
                    'from presentationpresenter.editor import blank_document; '
                    'Recovery(sys.argv[1]).write(blank_document()); os._exit(7)')
            process = subprocess.run([sys.executable, '-B', '-c', code, directory], capture_output=True, timeout=20)
            self.assertEqual(process.returncode, 7, process.stderr)
            recovery = Recovery(directory)
            candidates = recovery.candidates()
            self.assertEqual(len(candidates), 1)
            self.assertEqual(len(storage.load(candidates[0]).sections), 1)

    def test_maximal_image_fit_all_aspects_and_camera_positions(self):
        for aspect in Aspect:
            for camera in (None, CameraRegion(), CameraRegion(.2, .25, .3, .4, .02)):
                for size in ((600, 300), (300, 600), (500, 500)):
                    layout = image_layout(OutputConfig(aspect, camera), size, 'unused')
                    box = layout.image_box
                    self.assertAlmostEqual(box.width/box.height, size[0]/size[1])
                    self.assertGreater(box.width, 0)
                    self.assertGreaterEqual(box.x, 0)
                    self.assertGreaterEqual(box.y, 0)
                    self.assertLessEqual(box.x+box.width, layout.width)
                    self.assertLessEqual(box.y+box.height, layout.height)
                    if layout.exclusion:
                        self.assertFalse(box.intersects(layout.exclusion))
                    if camera is None:
                        self.assertTrue(box.width == layout.width or box.height == layout.height)

class UITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.root.withdraw()
        self.window = MainWindow(self.root, AppSettings(), recovery_dir=Path(self.temp.name)/'recovery')

    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()

    def test_image_undo_duplicate_render_and_live_isolation(self):
        window = self.window
        source = Path(self.temp.name)/'photo.png'
        source.write_bytes(raw_image())
        before = window.document
        window.insert_image(source)
        source.unlink()
        draft = window.document
        window.undo()
        self.assertEqual(window.document, before)
        window.redo()
        self.assertEqual(window.document, draft)
        window.copy_section()
        self.assertEqual(len(window.document.sections), 2)
        self.assertNotEqual(window.document.sections[0].id, window.document.sections[1].id)
        window.rebuild()
        plan = window.draft_plan
        slide = next(s for s in plan.slides if s.hall and s.hall.images)
        canvas = tk.Canvas(self.root)
        for output in ('hall', 'stream'):
            draw(canvas, slide, output, window.metrics, window.typography)
            self.assertTrue(any(canvas.type(i) == 'image' for i in canvas.find_all()))
        from presentationpresenter.session import ProjectionSession
        window.session = ProjectionSession.confirm(plan)
        previous = window.session
        window.commit(replace(window.document, title='Unsaved draft'))
        window.autosave()
        self.assertEqual(storage.load(window.recovery.path), window.document)
        self.assertIs(window.session, previous)
        window.apply_live()
        self.assertEqual(window.session.plan.source, window.document)

    def test_open_invalid_keeps_history_and_live_recovery_offer(self):
        window = self.window
        from presentationpresenter.session import ProjectionSession
        window.session = ProjectionSession.confirm(window.draft_plan)
        previous, old = window.session, window.document
        path = Path(self.temp.name)/'corrupt.ppres'
        path.write_text('{')
        with patch('presentationpresenter.ui.filedialog.askopenfilename', return_value=str(path)), patch('presentationpresenter.ui.messagebox.showerror') as error:
            window.open_document()
            error.assert_called_once()
        self.assertEqual(window.document, old)
        self.assertIs(window.session, previous)
        doc = document()
        storage.save(path, doc)
        with patch('presentationpresenter.ui.filedialog.askopenfilename', return_value=str(path)):
            window.open_document()
        self.assertEqual(window.document, doc)
        self.assertIs(window.session, previous)
        window.undo()
        self.assertEqual(window.document, old)
        crashed = Recovery(window.recovery.directory)
        crashed.write(doc)
        crashed.release()
        with patch('presentationpresenter.ui.messagebox.askyesno', return_value=True):
            window.offer_recovery()
        self.assertEqual(window.document, doc)
        self.assertIs(window.session, previous)
        self.assertFalse(crashed.path.exists())
        self.assertEqual(storage.load(window.recovery.directory/'archive'/crashed.path.name), doc)
        self.assertEqual(storage.load(window.recovery.path), doc)
        with patch('presentationpresenter.ui.messagebox.askyesno') as prompt:
            window.offer_recovery()
            prompt.assert_not_called()

    def test_recovery_offered_once_and_new_crash_has_latest_draft(self):
        w = self.window
        old = Recovery(w.recovery.directory)
        old.write(document())
        old.release()
        older = Recovery(w.recovery.directory)
        older.write(replace(document(), title='Older'))
        older.release()
        with patch('presentationpresenter.ui.messagebox.askyesno', return_value=True) as prompt:
            w.offer_recovery()
            self.assertEqual(prompt.call_count, 1)
        w.commit(replace(w.document, title='Updated after recovery'))
        w.autosave()
        w.recovery.release()  # A second crash leaves the current journal.
        next_run = Recovery(w.recovery.directory)
        candidates = next_run.candidates()
        self.assertEqual(candidates, [w.recovery.path])
        self.assertEqual(storage.load(candidates[0]).title, 'Updated after recovery')
        self.assertEqual(len(list((w.recovery.directory/'archive').glob('*.ppres'))), 2)
        w.recovery.clean()  # Normal close retires only the current journal.
        self.assertEqual(next_run.candidates(), [])

    def test_declined_recovery_is_not_offered_again(self):
        w = self.window
        old = Recovery(w.recovery.directory)
        old.write(document())
        old.release()
        before = w.document
        with patch('presentationpresenter.ui.messagebox.askyesno', return_value=False) as prompt:
            w.offer_recovery()
            self.assertEqual(prompt.call_count, 1)
        self.assertEqual(w.document, before)
        self.assertEqual(Recovery(w.recovery.directory).candidates(), [])
        self.assertTrue((w.recovery.directory/'archive'/old.path.name).exists())

    def test_failed_recovery_adoption_keeps_previous_journal(self):
        w = self.window
        old = Recovery(w.recovery.directory)
        old.write(document())
        old.release()
        with patch('presentationpresenter.ui.messagebox.askyesno', return_value=True), patch.object(w.recovery, 'write', side_effect=OSError('disk full')):
            w.offer_recovery()
        self.assertTrue(old.path.exists())
        self.assertIn(old.path, Recovery(w.recovery.directory).candidates())

    def test_two_projection_windows_images_blackout_and_draft(self):
        from presentationpresenter.projection import Monitor
        w = self.window
        w.commit(document())
        w.rebuild()
        inventory = [Monitor('A', 0, 0, 800, 600), Monitor('B', -640, 0, 640, 360)]
        with patch('presentationpresenter.ui.monitors', return_value=inventory):
            w.monitor_choices['hall'].set('A')
            w.monitor_choices['stream'].set('B')
            w.refresh_monitors()
            for output in ('hall', 'stream'):
                w.projection_controls.fullscreen[output] = False
            self.assertTrue(w.start_projection(('hall', 'stream')))
            w.jump(1)
            self.root.update()
            for window in w.projections.values():
                self.assertTrue(any(window.canvas.type(i) == 'image' for i in window.canvas.find_all()))
            session = w.session
            w.delete_section()
            w.undo()
            self.assertIs(w.session, session)
            w.toggle_blackout()
            for window in w.projections.values():
                self.assertFalse(window.canvas.find_all())
            w.toggle_blackout()
            w.apply_live()
            for window in w.projections.values():
                self.assertTrue(any(window.canvas.type(i) == 'image' for i in window.canvas.find_all()))

    def test_save_new_document_resets_path_and_json_is_protected(self):
        w = self.window
        w.commit(document())
        path = Path(self.temp.name)/'saved.ppres'
        with patch('presentationpresenter.ui.filedialog.asksaveasfilename', return_value=str(path)):
            self.assertTrue(w.save_document())
        self.assertEqual(w.saved_document, w.document)
        with patch('presentationpresenter.ui.messagebox.askyesno', return_value=True):
            w.new_document()
        self.assertIsNone(w.file_path)
        self.assertEqual(storage.load(path).sections[0].title, 'Obrázek')
        original = Path(self.temp.name)/'original.json'
        original.write_text('[]')
        with patch('presentationpresenter.ui.filedialog.asksaveasfilename', return_value=str(original)), patch('presentationpresenter.ui.messagebox.showerror'):
            self.assertFalse(w.save_document())
        self.assertEqual(original.read_text(), '[]')

if __name__ == '__main__':
    unittest.main()
