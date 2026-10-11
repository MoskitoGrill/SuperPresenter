import json
from dataclasses import replace, FrozenInstanceError
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from presentationpresenter.domain import *
from presentationpresenter.layout import ContentRange, Slide, SlidePlan, with_black_breaks
from presentationpresenter.persistence import dumps, loads
from presentationpresenter.sample import sample_document
from presentationpresenter.session import ProjectionSession
from presentationpresenter.settings import AppSettings, load_settings, save_settings, settings_path

class ModelTests(unittest.TestCase):
    def test_roundtrip_all_content_and_ids(self):
        asset = MediaAsset('media/example.png', 'image/png')
        text = TextSection('Nadpis', (TextBlock((TextRun('český text', TextStyle(True, True, True, '#abcdef')),), BlockKind.BULLET),),
                           reference='odkaz', origin=ImportOrigin('pptx', 'future.pptx', 'slide-1'))
        source = Presentation(sections=(text, ImageSection('Obrázek', asset.id)), media=(asset,))
        self.assertEqual(loads(dumps(source)), source)
        self.assertEqual(loads(dumps(source)).sections[0].blocks[0].runs[0].id, text.blocks[0].runs[0].id)

    def test_defaults_and_independent_outputs(self):
        source = sample_document()
        changed = replace(source, hall=OutputConfig(Aspect.WIDE))
        self.assertEqual(source.hall.aspect, Aspect.STANDARD)
        self.assertEqual(changed.stream, source.stream)
        self.assertEqual(source.stream.camera, CameraRegion(.5, .5, .5, .5, .02))
        self.assertTrue(source.black_start)
        self.assertTrue(source.sections[0].break_after)

    def test_invalid_sources(self):
        section = sample_document().sections[0]
        for create in (
            lambda: Presentation(sections=(section, section)),
            lambda: Presentation(sections=(ImageSection('Missing', 'no-media'),)),
            lambda: Presentation(schema_version=2),
            lambda: Presentation(sections=[section]),
            lambda: Presentation(black_start='false'),
            lambda: TextStyle(color='red'),
            lambda: CameraRegion(x=.8),
            lambda: CameraRegion(gap=float('nan')),
        ):
            with self.subTest(create=create), self.assertRaises(ValueError):
                create()

    def test_codec_rejects_future_corrupt_and_unknown_data(self):
        valid = json.loads(dumps(sample_document()))
        for payload in ('{', '[]', json.dumps({**valid, 'schema_version': 2}),
                        json.dumps({**valid, 'unexpected': 1}),
                        json.dumps({**valid, 'sections': [{'type': 'video'}]})):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                loads(payload)

    def content(self, source):
        section = source.sections[0]
        block = section.blocks[0]
        run = block.runs[0]
        return (Slide('content-1', section.id, (ContentRange(section.id, block.id, run.id, 0, len(run.text)),)),)

    def test_black_breaks_and_stable_ids(self):
        source = sample_document()
        plan = with_black_breaks(source, self.content(source))
        self.assertEqual([s.black for s in plan.slides], [True, False, True])
        self.assertEqual(plan, with_black_breaks(source, self.content(source)))
        disabled = replace(source, black_start=False, sections=(replace(source.sections[0], break_after=False),))
        self.assertEqual(len(with_black_breaks(disabled, self.content(disabled)).slides), 1)
        empty = Presentation(sections=(TextSection('Empty', ()), TextSection('Empty 2', ())))
        self.assertEqual(len(with_black_breaks(empty, ()).slides), 1)

    def test_plan_validates_source_ranges(self):
        source = sample_document()
        slide = self.content(source)[0]
        span = slide.ranges[0]
        with self.assertRaises(ValueError):
            SlidePlan(source, (replace(slide, ranges=(replace(span, end=100000),)),))
        with self.assertRaises(ValueError):
            SlidePlan(source, (replace(slide, section_id='missing'),))
        with self.assertRaises(ValueError):
            ContentRange('s', 'b', 'r', -1, 5)

    def test_session_is_confirmed_snapshot(self):
        source = sample_document()
        plan = with_black_breaks(source, self.content(source))
        live = ProjectionSession.confirm(plan)
        draft = replace(source, title='Edited', sections=())
        self.assertNotEqual(draft, live.plan.source)
        self.assertEqual(live.plan.source, source)
        with self.assertRaises(FrozenInstanceError):
            live.plan.source.title = 'Mutation'
        with self.assertRaises(ValueError):
            replace(live, current_slide_id='missing')

    def test_settings_own_path_roundtrip_and_corruption(self):
        self.assertEqual(settings_path().parent.name, 'PresentationPresenter')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            self.assertEqual(load_settings(path), AppSettings())
            settings = AppSettings(geometry='1200x800+10+20')
            save_settings(settings, path)
            self.assertEqual(load_settings(path), settings)
            path.write_text('{"geometry": "broken"}', encoding='utf-8')
            self.assertEqual(load_settings(path), AppSettings())

    def test_domain_layers_have_no_ui_or_legacy_dependencies(self):
        code = """
import sys, importlib
for name in ('tkinter', 'superpresenter', 'super_presenter', 'song_editor', 'presentation_presenter'):
    sys.modules[name] = None
for module in ('domain', 'layout', 'session', 'persistence', 'settings'):
    importlib.import_module('presentationpresenter.' + module)
"""
        result = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == '__main__':
    unittest.main()
