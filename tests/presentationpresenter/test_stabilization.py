"""Bounded rendering resources and crash/concurrency-safe local preferences."""
import gc
import io
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
import weakref
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from unittest.mock import patch
from PIL import Image

from presentationpresenter import media
from presentationpresenter.domain import Presentation, ImageSection, TextStyle
from presentationpresenter.layout import paginate, Typography
from presentationpresenter.rendering import TkMetrics, draw
from presentationpresenter.settings import AppSettings, load_settings, save_settings
from presentationpresenter.profiles import defaults, load_profiles, save_profiles


class ResourceTests(unittest.TestCase):
    def asset(self):
        raw = io.BytesIO()
        Image.new('RGBA', (80, 60), (20, 40, 90, 128)).save(raw, 'PNG')
        return media.from_bytes(raw.getvalue())

    def test_raster_cache_keeps_pixels_and_respects_budget(self):
        asset = self.asset()
        cache = media.ScaledRasterCache(max_bytes=5000, max_entries=2)
        expected = media.decode(asset.locator).resize((20, 20), Image.Resampling.LANCZOS)
        with patch('presentationpresenter.media.decode', wraps=media.decode) as decode:
            image = cache.get(asset.locator, (20, 20))
            self.assertEqual(image.tobytes(), expected.tobytes())
            self.assertIs(cache.get(asset.locator, (20, 20)), image)
            self.assertEqual(decode.call_count, 1)
            cache.get(asset.locator, (30, 30))
            self.assertLessEqual(cache.resident_bytes, 5000)
            cache.get(asset.locator, (20, 20))
            self.assertEqual(decode.call_count, 3)  # The old entry was evicted.
            before = cache.resident_bytes
            cache.get(asset.locator, (80, 60))
            self.assertEqual(cache.resident_bytes, before)  # Large items bypass.
        cache.clear()
        self.assertEqual(cache.resident_bytes, 0)
        with self.assertRaises(ValueError):
            cache.get('bad', (10, 10))
        self.assertFalse(cache.entries)

    def test_repeated_canvas_draw_decodes_once_and_caches_do_not_retain_metrics(self):
        root = tk.Tk()
        root.withdraw()
        try:
            metrics = TkMetrics(root)
            asset = self.asset()
            doc = Presentation(sections=(ImageSection('', asset.id, break_after=False),), media=(asset,), black_start=False)
            slide = paginate(doc, metrics).slides[0]
            canvas = tk.Canvas(root)
            with patch('presentationpresenter.media.decode', wraps=media.decode) as decode:
                for _ in range(10):
                    draw(canvas, slide, 'hall', metrics, Typography(), scale=.5)
                self.assertEqual(decode.call_count, 1)
            metrics.width('Příliš žluťoučký kůň', TextStyle(), 36)
            other = TkMetrics(root)
            self.assertEqual(other.font.cache_info().currsize, 0)
            reference = weakref.ref(metrics)
            del metrics
            gc.collect()
            self.assertIsNone(reference())
        finally:
            root.destroy()


class PreferenceWriteTests(unittest.TestCase):
    def test_parallel_saves_are_complete_and_do_not_share_temporary_names(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory)/'settings.json'
            profile_path = Path(directory)/'profiles.json'
            def save(index):
                save_settings(replace(AppSettings(), content_font_size=8+index), settings_path)
                save_profiles((replace(defaults()[0], name=f'QA {index}'),), profile_path)
                self.assertIn(load_settings(settings_path).content_font_size, range(8, 28))
                self.assertEqual(len(load_profiles(profile_path)), 1)
            with ThreadPoolExecutor(max_workers=4) as workers:
                list(workers.map(save, range(20)))
            self.assertIn(load_settings(settings_path).content_font_size, range(8, 28))
            self.assertTrue(load_profiles(profile_path)[0].name.startswith('QA '))
            self.assertFalse(list(Path(directory).glob('*.tmp')))

    def test_replace_failure_preserves_preferences_and_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, save, value in (('settings.json', save_settings, AppSettings()),
                                      ('profiles.json', save_profiles, defaults())):
                path = Path(directory)/name
                save(value, path)
                previous = path.read_bytes()
                with patch('presentationpresenter.atomic_file.os.replace', side_effect=OSError('disk')):
                    with self.assertRaises(OSError):
                        save(value, path)
                self.assertEqual(path.read_bytes(), previous)
                self.assertFalse(list(Path(directory).glob('*.tmp')))


if __name__ == '__main__':
    unittest.main()
