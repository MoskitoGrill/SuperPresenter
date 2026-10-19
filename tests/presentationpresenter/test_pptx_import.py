"""Read-only OOXML fixtures and detached-review / draft-publication boundaries."""
import io
import tempfile
import tkinter as tk
import unittest
import zipfile
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from PIL import Image
from presentationpresenter.pptx_import import read_pptx, NS
from presentationpresenter.domain import *
from presentationpresenter.editor import merge_sections
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings
from presentationpresenter.session import ProjectionSession
from presentationpresenter.pptx_import_window import ImportWindow
from presentationpresenter import storage, media

P, A, R = NS['p'], NS['a'], NS['r']
def shape(text, title=False, props='', breaks=False):
    ph = '<p:ph type="title"/>' if title else '<p:ph type="body" idx="1"/>'
    content = '<a:r><a:rPr b="1"/><a:t>'+text+'</a:t></a:r>'
    if breaks:
        content += '<a:br/><a:r><a:t>měkký řádek</a:t></a:r>'
    return f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="pole"/><p:nvPr>{ph}</p:nvPr></p:nvSpPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p>{props}{content}</a:p></p:txBody></p:sp>'

def slide(content='', black=False, extra=''):
    bg = '<p:bg><p:bgPr><a:solidFill><a:srgbClr val="000000"/></a:solidFill></p:bgPr></p:bg>' if black else ''
    return f'<p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}"><p:cSld>{bg}<p:spTree>{content}</p:spTree></p:cSld>{extra}</p:sld>'

def fixture(path, slides, extras=None, slide_rels=None):
    rel_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
    with zipfile.ZipFile(path, 'w') as z:
        ids = ''.join(f'<p:sldId id="{i+255}" r:id="r{i}"/>' for i in range(1, len(slides)+1))
        z.writestr('ppt/presentation.xml', f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldSz cx="1000" cy="750"/><p:sldIdLst>{ids}</p:sldIdLst></p:presentation>')
        rels = ''.join(f'<Relationship Id="r{i}" Type="{R}/slide" Target="slides/slide{i}.xml"/>' for i in range(1, len(slides)+1))
        z.writestr('ppt/_rels/presentation.xml.rels', f'<Relationships xmlns="{rel_ns}">{rels}</Relationships>')
        for i, content in enumerate(slides, 1):
            z.writestr(f'ppt/slides/slide{i}.xml', content)
            if slide_rels and i in slide_rels:
                z.writestr(f'ppt/slides/_rels/slide{i}.xml.rels', f'<Relationships xmlns="{rel_ns}">{slide_rels[i]}</Relationships>')
        for name, content in (extras or {}).items():
            z.writestr(name, content)
    return path

class PptxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'source.pptx'
    def tearDown(self):
        self.temp.cleanup()

    def test_join_and_black_boundaries_and_source_preserved(self):
        fixture(self.path, [slide(black=True), slide(shape('Jan 16', True)+shape('A')),
                            slide(shape('Jan 16', True)+shape('B')), slide(black=True),
                            slide(shape('Jan 16', True)+shape('C')), slide(shape('Řím 8', True)+shape('D')),
                            slide(black=True), slide(black=True)])
        original = self.path.read_bytes()
        result = read_pptx(self.path)
        self.assertEqual(len(result.document.sections), 3)
        first, second, third = result.document.sections
        self.assertEqual([b.runs[0].text for b in first.blocks], ['A', 'B'])
        self.assertEqual(first.origin.item_key, '2,3')
        self.assertTrue(first.break_before)
        self.assertTrue(second.break_before)
        self.assertFalse(third.break_before)
        self.assertTrue(result.document.black_end)
        self.assertEqual(len(result.mapping), 8)
        self.assertEqual(len(read_pptx(self.path, join_same=False).document.sections), 4)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(any('sjednoceny' in w for w in result.warnings))
        self.assertEqual(storage.persistence.loads(storage.persistence.dumps(result.document)), result.document)

    def test_bullet_inheritance_soft_break_and_images_portable(self):
        raw = io.BytesIO()
        Image.new('RGB', (80, 40), 'red').save(raw, 'PNG')
        pic = '<p:pic><p:blipFill><a:blip r:embed="image"/></p:blipFill><p:spPr><a:xfrm rot="100"/></p:spPr></p:pic>'
        layout = f'<p:sldLayout xmlns:p="{P}" xmlns:a="{A}"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:txBody><a:lstStyle><a:lvl2pPr><a:buChar char="x"/></a:lvl2pPr></a:lstStyle></p:txBody></p:sp></p:spTree></p:cSld></p:sldLayout>'
        rels = f'<Relationship Id="image" Type="{R}/image" Target="../media/a.png"/><Relationship Id="layout" Type="{R}/slideLayout" Target="../slideLayouts/a.xml"/>'
        fixture(self.path, [slide(shape('Seznam', True)+shape('položka', props='<a:pPr lvl="1"/>', breaks=True)+pic+pic)],
                {'ppt/media/a.png': raw.getvalue(), 'ppt/slideLayouts/a.xml': layout}, {1: rels})
        doc = read_pptx(self.path).document
        block = doc.sections[0].blocks[0]
        self.assertEqual((block.kind, block.level), (BlockKind.BULLET, 1))
        self.assertEqual(''.join(r.text for r in block.runs), 'položka\nměkký řádek')
        self.assertTrue(block.runs[0].style.bold)
        self.assertEqual(len(doc.sections[0].images), 2)
        self.assertTrue(all(not i.repeat and i.hall is None and i.stream is None for i in doc.sections[0].images))
        saved = Path(self.temp.name)/'portable.ppres'
        storage.save(saved, doc)
        self.path.unlink()
        self.assertEqual(storage.load(saved), doc)

    def test_unknown_empty_not_silently_black_and_animation_warning(self):
        fixture(self.path, [slide(extra='<p:timing/>'), slide('<p:graphicFrame/>')])
        result = read_pptx(self.path)
        self.assertEqual(len(result.document.sections), 2)
        self.assertTrue(any('Animace' in w for w in result.warnings))
        self.assertTrue(any('Tabulky' in w for w in result.warnings))
        self.assertTrue(any('Prázdný' in w for w in result.warnings))
        self.assertFalse(any(s.break_before for s in result.document.sections))

    def test_empty_titles_do_not_join_and_numbering_warns(self):
        fixture(self.path, [slide(shape('A', props='<a:pPr lvl="7"><a:buAutoNum type="romanUcPeriod" startAt="5"/></a:pPr>')),
                            slide(shape('B'))])
        result = read_pptx(self.path)
        self.assertEqual(len(result.document.sections), 2)
        self.assertEqual(result.document.sections[0].blocks[0].level, 2)
        self.assertGreaterEqual(len(result.warnings), 2)

    def test_corrupt_and_entity_refused(self):
        self.path.write_bytes(b'not zip')
        with self.assertRaises(ValueError):
            read_pptx(self.path)

    def test_black_cover_and_theme_background(self):
        cover = '<p:sp><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1000" cy="750"/></a:xfrm><a:prstGeom prst="rect"/><a:solidFill><a:srgbClr val="000000"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>'
        scheme_slide = slide().replace('<p:spTree>', '<p:bg><p:bgPr><a:solidFill><a:schemeClr val="tx1"/></a:solidFill></p:bgPr></p:bg><p:spTree>')
        rel_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
        rels = lambda kind, target: f'<Relationships xmlns="{rel_ns}"><Relationship Id="a" Type="{R}/{kind}" Target="{target}"/></Relationships>'
        extras = {'ppt/slideLayouts/a.xml': f'<p:sldLayout xmlns:p="{P}"/>',
                  'ppt/slideLayouts/_rels/a.xml.rels': rels('slideMaster', '../slideMasters/a.xml'),
                  'ppt/slideMasters/a.xml': f'<p:sldMaster xmlns:p="{P}"><p:clrMap tx1="dk1"/></p:sldMaster>',
                  'ppt/slideMasters/_rels/a.xml.rels': rels('theme', '../theme/a.xml'),
                  'ppt/theme/a.xml': f'<a:theme xmlns:a="{A}"><a:themeElements><a:clrScheme><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1></a:clrScheme></a:themeElements></a:theme>'}
        fixture(self.path, [slide(cover), slide(shape('A')), scheme_slide], extras,
                {3: f'<Relationship Id="a" Type="{R}/slideLayout" Target="../slideLayouts/a.xml"/>'})
        result = read_pptx(self.path)
        self.assertEqual(len(result.document.sections), 1)
        self.assertTrue(result.document.sections[0].break_before)
        self.assertTrue(result.document.black_end)

    def test_external_image_warning_and_invalid_package_path(self):
        picture = '<p:pic><p:blipFill><a:blip r:link="image"/></p:blipFill></p:pic>'
        fixture(self.path, [slide(picture)], slide_rels={1: f'<Relationship Id="image" Type="{R}/image" Target="https://example.invalid/image.png" TargetMode="External"/>'})
        result = read_pptx(self.path)
        self.assertTrue(any('obrázek nebyl převzat' in w for w in result.warnings))
        self.assertEqual(len(result.document.media), 0)
        fixture(self.path, [slide(shape('A'))], slide_rels={1: f'<Relationship Id="image" Type="{R}/image" Target="../../../../outside.png"/>'})
        with self.assertRaises(ValueError):
            read_pptx(self.path)
        fixture(self.path, ['<!DOCTYPE x [<!ENTITY x "oops">]>'+slide()])
        with self.assertRaises(ValueError):
            read_pptx(self.path)

    def test_template_title_is_named_textbox(self):
        template = Path('songs/zdrojove soubory/Prezentace - stream vzor.pptx')
        if not template.exists():
            self.skipTest('Local template not distributed with test environment')
        result = read_pptx(template)
        self.assertEqual(result.document.sections[0].title, 'odkaz')
        self.assertIn('Text text', ''.join(r.text for b in result.document.sections[0].blocks for r in b.runs))
        self.assertTrue(any('dekorace' in w for w in result.warnings))

class ImportGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = fixture(Path(self.temp.name)/'source.pptx', [slide(shape('Jan', True)+shape('A')), slide(shape('Jan', True)+shape('B'))])
        self.root = tk.Tk()
        self.w = MainWindow(self.root, AppSettings(), recovery_dir=Path(self.temp.name)/'recovery')
        self.root.after_cancel(self.w.autosave_job)
        self.w.autosave_job = None
        self.errors = []
        self.root.report_callback_exception = lambda *e: self.errors.append(e)
        self.root.update()
    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()
        self.assertFalse(self.errors)

    def test_detached_review_cancel_and_change_option(self):
        original = self.w.document
        review = ImportWindow(self.w, self.path)
        self.root.update()
        self.assertEqual(str(review.insert['state']), 'normal')
        self.assertEqual(len(review.result.document.sections), 1)
        review.join.set(False)
        review.refresh()
        self.assertEqual(str(review.insert['state']), 'normal')
        self.assertEqual(len(review.result.document.sections), 2)
        review.move(1)
        self.assertTrue(review.canvases['hall'].find_all())
        self.assertTrue(review.canvases['stream'].find_all())
        review.window.destroy()
        self.assertEqual(self.w.document, original)
        self.assertIsNone(review.accepted)

    def test_insert_is_confirmation_and_invalid_import_stays_disabled(self):
        original = self.w.document
        review = ImportWindow(self.w, self.path)
        imported = review.result.document
        review.insert.invoke()
        self.assertEqual(review.accepted, imported)
        self.assertEqual(self.w.document, original)
        self.path.write_bytes(b'not a pptx')
        review = ImportWindow(self.w, self.path)
        self.assertEqual(str(review.insert['state']), 'disabled')
        review.accept()
        self.assertIsNone(review.accepted)
        review.window.destroy()

    def test_insert_undo_redo_live_isolation_and_manual_merge(self):
        w = self.w
        w.text.insert('end', 'Původní obsah')
        w.finish_editing()
        w.rebuild()
        original = w.document
        w.session = ProjectionSession.confirm(w.plan)
        session = w.session
        imported = read_pptx(self.path, join_same=False).document
        w.insert_pptx_document(imported)
        after = w.document
        self.assertEqual(len(after.sections), 3)
        self.assertIs(w.session, session)
        w.undo()
        self.assertEqual(w.document, original)
        w.redo()
        self.assertEqual(w.document, after)
        w.selected_id = after.sections[1].id
        w.load_editor()
        with patch('presentationpresenter.ui.messagebox.askyesno', return_value=False):
            w.merge_next_section()
        self.assertEqual(w.document, after)
        with patch('presentationpresenter.ui.messagebox.askyesno', return_value=True):
            w.merge_next_section()
        self.assertEqual(len(w.document.sections), 2)
        self.assertEqual([b.runs[0].text for b in w.document.sections[1].blocks], ['A', 'B'])
        self.assertIs(w.session, session)
        w.undo()
        self.assertEqual(w.document, after)

    def test_starter_and_trailing_black_before_existing_section(self):
        w = self.w
        incoming = read_pptx(self.path).document
        w.insert_pptx_document(incoming)
        self.assertEqual(len(w.document.sections), 1)
        self.assertFalse(w.document.black_end)
        incoming = replace(incoming, sections=tuple(replace(s, id=new_id(), blocks=tuple(TextBlock(tuple(TextRun(r.text) for r in b.runs)) for b in s.blocks)) for s in incoming.sections), black_end=True)
        w.add_section()
        w.selected_id = w.document.sections[0].id
        w.insert_pptx_document(incoming)
        self.assertTrue(w.document.sections[-1].break_before)

    def test_manual_merge_images_uses_grid_and_preserves_outer_breaks(self):
        raw = io.BytesIO()
        Image.new('RGB', (40, 40)).save(raw, 'PNG')
        asset = media.from_bytes(raw.getvalue())
        first = TextSection('A', (TextBlock((TextRun('a'),)),), images=(ImageItem(asset.id, hall=ImagePlacement(0, 0, .2)),), break_before=True)
        second = TextSection('B', (TextBlock((TextRun('b'),)),), images=(ImageItem(asset.id, repeat=False),), break_after=False)
        merged = merge_sections(first, second)
        self.assertEqual(merged.id, first.id)
        self.assertTrue(merged.break_before)
        self.assertFalse(merged.break_after)
        self.assertTrue(all(i.hall is None and i.stream is None for i in merged.images))
        self.assertEqual([i.repeat for i in merged.images], [True, False])
