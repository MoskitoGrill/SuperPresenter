"""QR profile persistence, editor transactions and live hall/text coexistence."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PIL import Image

from superpresenter.services.collection_qr import (
    default_settings, geometry, render_image, validate_settings, encode_image, decode_image,
)
from superpresenter.services.projection_config import ConfigError, load_layout, save_layout
from superpresenter.ui.projection_profiles import ProjectionProfiles
import test_projection_editor as editor_tests
import test_release_stability as release


class QRModelTests(unittest.TestCase):
    def test_percent_geometry_and_white_border_preserve_aspect(self):
        for width, height in ((1920, 1080), (800, 600), (400, 800)):
            for size in (1, 25, 100):
                for x, y in ((0, 0), (100, 100), (50, 50)):
                    settings = dict(size_pct=size, x_pct=x, y_pct=y)
                    left, top, side = geometry(settings, width, height)
                    self.assertGreaterEqual(left, 0)
                    self.assertGreaterEqual(top, 0)
                    self.assertLessEqual(left + side, width)
                    self.assertLessEqual(top + side, height)
        rendered = render_image(Image.new('RGBA', (200, 100), 'black'), 100)
        self.assertEqual(rendered.size, (100, 100))
        self.assertEqual(rendered.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(rendered.getpixel((50, 50)), (0, 0, 0))
        self.assertEqual(rendered.getpixel((50, 15)), (255, 255, 255))

    def test_profile_contains_image_and_rejects_invalid_values(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'qr.png'
            Image.new('RGB', (100, 100), 'black').save(source)
            settings = dict(size_pct=25, x_pct=100, y_pct=0, image_data=encode_image(source))
            source.unlink()
            self.assertEqual(decode_image(settings['image_data']).size, (100, 100))
            output = dict(style='hall', collection=True, fullscreen=True,
                          monitor=dict(name='screen', x=0, y=0, width=800, height=600),
                          collection_settings=settings)
            data = dict(version=2, outputs=[output])
            styles = [dict(name='hall')]
            path = Path(folder) / 'profile.json'
            save_layout(path, data, styles)
            self.assertEqual(load_layout(path, styles), data)
            for key, value in [('size_pct', 0), ('x_pct', 101), ('y_pct', float('nan')),
                               ('size_pct', True), ('image_data', 'not base64')]:
                with self.subTest(key=key, value=value):
                    output['collection_settings'] = dict(settings, **{key: value})
                    with self.assertRaises(ConfigError):
                        save_layout(path, data, styles)


class QREditorTests(unittest.TestCase):
    setUp = editor_tests.ProjectionEditorWidgetTests.setUp

    def dialog(self, callback):
        from superpresenter.ui.collection_qr_editor import CollectionQREditor
        self.root.geometry('800x800+30000+30000')
        self.root.deiconify()
        self.editor.win.geometry('800x800+30000+30000')
        self.editor.win.deiconify()
        self.root.update()
        dialog = CollectionQREditor(self.editor.win, self.owner.projStyles[0], None, callback)
        self.addCleanup(lambda: dialog.cancel() if dialog.win.winfo_exists() else None)
        # The fixture hides its parent; map this dialog offscreen for real geometry.
        dialog.win.transient('')
        dialog.win.geometry('720x760+30000+30000')
        dialog.win.deiconify()
        self.root.update()
        dialog.draw()
        return dialog

    def test_dialog_drag_presets_validation_cancel_and_reset(self):
        callback = Mock()
        dialog = self.dialog(callback)
        dialog.position(100, 100)
        self.assertEqual(dialog.current()['x_pct'], 100)
        self.assertGreater(dialog.canvas.winfo_width(), 100)
        x, y, _ = dialog.qr_rect
        dialog.start_drag(SimpleNamespace(x=x + 2, y=y + 2))
        self.assertIsNotNone(dialog.drag_offset, dialog.qr_rect)
        left, top, _, _ = dialog.preview_rect
        dialog.drag(SimpleNamespace(x=left + 2, y=top + 2))
        self.assertEqual(dialog.current()['x_pct'], 0)
        self.assertEqual(dialog.current()['y_pct'], 0)
        dialog.values['size_pct'].set('abc')
        with patch('superpresenter.ui.collection_qr_editor.messagebox.showerror') as error:
            dialog.apply()
            error.assert_called_once()
        callback.assert_not_called()
        dialog.reset()
        self.assertAlmostEqual(dialog.current()['size_pct'], default_settings(self.owner.projStyles[0])['size_pct'], places=2)
        dialog.cancel()
        callback.assert_not_called()

    def test_image_selection_apply_and_profile_roundtrip(self):
        row = self.editor.cards[1]['outputs'][0]
        baseline = self.editor.state()
        dialog = self.dialog(lambda settings: row.update(collection_settings=settings))
        source = Path(self.temporary.name) / 'new-qr.png'
        Image.new('RGB', (120, 120), 'black').save(source)
        with patch('superpresenter.ui.collection_qr_editor.filedialog.askopenfilename', return_value=str(source)):
            dialog.choose_image()
        dialog.values['size_pct'].set('25')
        dialog.position(100, 0)
        dialog.apply()
        self.assertNotEqual(self.editor.state(), baseline)
        self.assertTrue(self.editor.save_profile())
        saved = load_layout(self.editor.entries[self.editor.selected_profile]['path'], self.owner.projStyles)
        settings = saved['outputs'][0]['collection_settings']
        self.assertEqual(settings['size_pct'], 25)
        self.assertEqual(settings['image_name'], source.name)
        self.assertEqual(decode_image(settings['image_data']).size, (120, 120))
        self.editor.original = saved
        self.editor.render_cards()
        self.assertEqual(self.editor.draft()['outputs'][0]['collection_settings'], settings)

    def test_controls_only_visible_for_stationary_hall(self):
        row = self.editor.cards[1]['outputs'][0]
        frame = row['combo'].master
        qr_frame = next(child for child in frame.winfo_children()
                        if any(getattr(widget, 'cget', lambda _: '')('text') == 'Počet řádků'
                               for widget in child.winfo_children() if widget.winfo_class() == 'TLabel'))
        for index, style in enumerate(self.owner.projStyles):
            row['combo'].current(index + 1)
            row['combo'].event_generate('<<ComboboxSelected>>')
            self.root.update_idletasks()
            self.assertEqual(qr_frame.winfo_manager() == 'pack', style['mode'] == 'stationary_hall')


class QRRunningTests(unittest.TestCase):
    setUp = release.ReleaseTests.setUp
    destroy = release.ReleaseTests.destroy
    configure_outputs = release.ReleaseTests.configure_outputs

    def test_live_toggle_text_navigation_resize_and_profile_restore(self):
        gui = self.gui
        self.configure_outputs([0, 1])
        hall, stream = gui.projectors
        hall.collection_settings = dict(size_pct=25, x_pct=100, y_pct=100)
        gui.runButtFun()
        self.assertTrue(gui.runState)
        gui.nextStep()
        texts = [hall.canvas.itemcget(item, 'text') for item in hall.animated[0].items]
        gui.collectionState.set(True)
        gui.changeCollection()
        self.assertEqual(hall.canvas.itemcget(hall.collection_item, 'state'), 'normal')
        self.assertEqual(texts, [hall.canvas.itemcget(item, 'text') for item in hall.animated[0].items])
        self.assertIsNone(stream.collection_item)
        gui.nextStep()
        gui.nextSlide()
        self.assertEqual(hall.canvas.itemcget(hall.collection_item, 'state'), 'normal')
        self.assertEqual(hall.canvas.find_all()[-1], hall.collection_item)
        hall.canvas.configure(width=800, height=600)
        gui.win.update_idletasks()
        self.assertEqual(hall.collection_img.width(), 150)
        self.assertEqual(hall.canvas.coords(hall.collection_item), [650, 450])
        gui.collectionState.set(False)
        gui.changeCollection()
        self.assertEqual(hall.canvas.itemcget(hall.collection_item, 'state'), 'hidden')
        gui.runButtFun()
        gui.profile_dir = Path(self.tmp.name)
        gui._profiles_ready = True
        gui._preserve_last = False
        ProjectionProfiles.persist_layout(gui)
        self.assertTrue(gui.restore_profile(gui.profile_dir / 'last-layout.json'))
        self.assertEqual(gui.projectors[0].collection_settings, dict(size_pct=25, x_pct=100, y_pct=100))
        self.error.assert_not_called()
