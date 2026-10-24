import hashlib
import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from presentationpresenter.bible import BibleService, BibleError, AmbiguousBook, Passage
from presentationpresenter.bible_window import BibleWindow
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings
from presentationpresenter.session import ProjectionSession


class BibleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = BibleService()

    def test_continuous_text_and_verse_layout(self):
        passage = Passage('TEST', 'Jan', ((3, 36, 'První věta.'),
                                          (4, 1, 'Další věta.\n\nNový odstavec.'),
                                          (4, 2, 'Pokračování.')))
        self.assertEqual(passage.lines(False),
                         ('První věta. Další věta.', 'Nový odstavec. Pokračování.'))
        self.assertEqual(passage.lines(True),
                         ('3:36 První věta. 4:1 Další věta.', 'Nový odstavec. 4:2 Pokračování.'))
        self.assertEqual(len(passage.lines(False, True)), 3)
        self.assertEqual(passage.lines(True, True)[2], '4:2 Pokračování.')
        self.assertEqual(len(passage.section(False).blocks), 2)
        self.assertEqual(len(passage.section(False, True).blocks), 3)
        self.assertEqual(passage.clipboard_text(False), passage.reference + '\n' +
                         'První věta. Další věta.\nNový odstavec. Pokračování.')

    def test_names_aliases_and_john(self):
        s = self.service
        for text, book in [('JAN', 'Jan'), ('Jn', 'Jan'), ('Evangelium podle Jana', 'Jan'),
                           ('1. Jan', '1 Janův'), ('I', None), ('2 J', '2 Janův'),
                           ('3. Janův', '3 Janův'), ('Žalm', 'Žalmy'), ('Zl', 'Žalmy'),
                           ('1 Mojžíšova', 'Genesis'), ('1. Paralipomenon', '1 Paralipomenon'),
                           ('Jakubův', 'Jakub'), ('Nehemiáš', 'Nehemjáš')]:
            if book:
                self.assertEqual(s.resolve(text), book)
        for query, expected in [('Jan 3:16–18', ('Jan', 3)), ('1 J 1:1-2', ('1 Janův', 2)),
                                ('2. Jan 1:1', ('2 Janův', 1)), ('3 Jn 1:1', ('3 Janův', 1))]:
            p = s.parse('B21', query)
            self.assertEqual((p.book, len(p.verses)), expected)
        self.assertIn('Jan', s.suggestions('ja', 'CSP'))
        self.assertIn('1 Janův', s.suggestions('1. ja', 'CSP'))
        for query in ('Janov 1:1', 'Janovy listy 1:1'):
            with self.assertRaises(AmbiguousBook) as caught:
                s.parse('B21', query)
            self.assertIn('1 Janův', caught.exception.candidates)
        with self.assertRaises(AmbiguousBook) as caught:
            s.parse('B21', 'Ja 1:1')
        self.assertEqual(set(caught.exception.candidates), {'Jan', 'Jakub'})
        self.assertEqual(s.parse('B21', 'Janovy listy 1:1', '2 Janův').book, '2 Janův')

    def test_ranges_and_errors(self):
        s = self.service
        p = s.parse('B21', 'Jan 3:36–4:2')
        self.assertEqual([(c,v) for c,v,t in p.verses], [(3,36),(4,1),(4,2)])
        self.assertIn('3:36', p.lines()[0])
        self.assertIn('4:2', p.reference)
        self.assertEqual(len(s.parse('B21', 'Žalm 23').verses), 6)
        self.assertEqual(len(s.parse('B21', 'Jan 3–4').verses), 90)
        for query in ('', 'Foo 1:1', 'Jan', 'Jan 0:1', 'Jan 3:0', 'Jan 3:18–16',
                      'Jan 4:1–3:1', 'Jan 999:1', 'Jan 3:999', 'Jan 3:16–999', 'Jan 3:16xyz'):
            with self.subTest(query=query), self.assertRaises(BibleError):
                s.parse('B21', query)

    def test_real_data_and_read_only(self):
        folder = self.service.directory
        before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.json')}
        s = BibleService()
        self.assertEqual({code:len(s.books(code)) for code in s.translations}, {'B21':66,'BKR':66,'CSP':66,'EKU':66,'NKB':27})
        self.assertEqual(s.problems, {})
        self.assertNotIn('Genesis', s.books('NKB'))
        self.assertEqual(len(s.parse('B21', 'Žalmy 119').verses), 176)
        self.assertEqual(len(s.parse('B21', 'Deuteronomium 9:23–24').verses), 2)
        self.assertEqual(len(s.parse('BKR', 'Žalmy 55:23–24').verses), 2)
        self.assertEqual(len(s.parse('BKR', 'Žalmy 65:13–14').verses), 2)
        for code in s.translations:
            self.assertEqual(s.parse(code, 'Jan 3:16').book, 'Jan')
            self.assertEqual(s.parse(code, '1 Jan 1:1').book, '1 Janův')
        self.assertEqual(before, {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before})

    def test_missing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            data = {'Jan': {'1': {'1':'a','3':'c'}, '3': {'1':'d','2':''}}, 'Unknown': {'1':{'1':'?'}}}
            (folder/'bible_TEST.json').write_text(json.dumps(data), encoding='utf-8')
            (folder/'bible_BAD.json').write_text('{', encoding='utf-8')
            s = BibleService(folder)
            self.assertEqual(s.books('TEST'), ('Jan',))
            self.assertEqual(s.verses('TEST','Jan',1), (1,3))
            for query in ('Jan 1:1–3', 'Jan 1:1–3:1', 'Jan 2:1', 'Jan 1', 'Jan 3', 'Žalm 1:1'):
                with self.assertRaises(BibleError):
                    s.parse('TEST', query)
            self.assertIn('BAD', s.problems)
            self.assertIn('TEST', s.problems)
            self.assertEqual(s.parse('TEST','Jan 1:3').verses, ((1,3,'c'),))


class BibleWindowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)

    def tearDown(self):
        if self.root.winfo_exists():
            self.root.destroy()
        self.tmp.cleanup()
        self.assertEqual(self.errors, [])

    def test_layout_switch_preview_copy_and_insert(self):
        inserted = []
        bible = BibleWindow(self.root, insert=inserted.append)
        bible.query.set('Jan 3:16–18')
        bible.lookup()
        self.assertFalse(bible.verse_per_line.get())
        for separate in (False, True, False):
            for numbers in (False, True):
                bible.verse_per_line.set(separate)
                bible.numbers.set(numbers)
                bible.render()
                expected = bible.passage.clipboard_text(numbers, separate)
                self.assertEqual(bible.preview.get('1.0', 'end-1c'), expected)
                with patch.object(bible.window, 'clipboard_clear'), patch.object(
                        bible.window, 'clipboard_append') as append:
                    bible.copy()
                    append.assert_called_once_with(expected)
                bible.insert()
                self.assertEqual(len(inserted[-1].blocks), 3 if separate else 1)
                self.assertEqual('\n'.join(block.runs[0].text for block in inserted[-1].blocks),
                                 '\n'.join(bible.passage.lines(numbers, separate)))

    def test_embedded_insert_history_live_and_lifecycle(self):
        editor = MainWindow(self.root, AppSettings(), recovery_dir=self.tmp.name)
        self.root.update()
        editor.session = ProjectionSession.confirm(editor.plan)
        live = editor.session.plan
        before = editor.document
        bible = editor.open_bible()
        self.assertIs(editor.open_bible(), bible)
        bible.window.geometry('650x580')
        self.root.update()
        self.assertTrue(bible.insert_button.winfo_ismapped())
        self.assertLess(bible.insert_button.winfo_rooty()+bible.insert_button.winfo_height(),
                        bible.window.winfo_rooty()+bible.window.winfo_height())
        bible.query.set('Jan 3:36–4:2')
        bible.lookup()
        self.assertEqual(bible.selectors['end_chapter'][0].get(), '4')
        bible.numbers.set(False)
        bible.render()
        bible.insert_button.invoke()
        self.root.update()
        section = editor.section()
        self.assertEqual(section.reference, 'Jan 3:36–4:2 (CSP)')
        self.assertEqual(editor.title.get(), section.reference)
        self.assertEqual(len(editor.document.sections), len(before.sections))
        self.assertEqual(section.id, before.sections[0].id)
        self.assertEqual(section.images, ())
        self.assertEqual(len(section.blocks), 1)
        self.assertFalse(section.blocks[0].runs[0].text.startswith('36 '))
        self.assertIs(editor.session.plan, live)
        inserted = editor.document
        editor.undo()
        self.assertEqual(editor.document, before)
        editor.redo()
        self.assertEqual(editor.document, inserted)
        bible.query.set('Jan 3:999')
        bible.lookup()
        self.assertIsNone(bible.passage)
        self.assertEqual(str(bible.insert_button['state']), 'disabled')
        for _ in range(3):
            bible.close()
            bible.close()
            bible = editor.open_bible()
            self.root.update()
            self.assertTrue(bible.alive())
        self.root.destroy()
        self.assertFalse(bible.alive())
        # Teardown must not query the destroyed interpreter.
        self.root = tk.Tk()

    def test_selection_ambiguity_and_clipboard(self):
        bible = BibleWindow(self.root)
        self.root.update()
        self.assertIsNone(bible.insert_button)
        bible.window.geometry('650x580')
        self.root.update()
        for control in (bible.copy_button, bible.translation_box, bible.book_box, bible.preview):
            self.assertTrue(control.winfo_ismapped())
            self.assertLess(control.winfo_rooty()+control.winfo_height(), bible.window.winfo_rooty()+bible.window.winfo_height()+1)
        bible.query.set('Janovy listy 1:1')
        bible.lookup()
        self.assertIsNone(bible.passage)
        bible.suggestions.selection_set(1)
        bible.choose_suggestion()
        self.assertEqual(bible.passage.book, '2 Janův')
        bible.book.set('Jan')
        bible.change_book()
        for key, value in [('start_chapter','3'),('end_chapter','4')]:
            bible.selectors[key][0].set(value)
            bible.update_verses(key.split('_')[0])
        bible.selectors['start_verse'][0].set('36')
        bible.selectors['end_verse'][0].set('2')
        bible.show_selection()
        self.assertEqual(len(bible.passage.verses), 3)
        # Use a mock to avoid replacing the user's actual clipboard.
        with patch.object(bible.window, 'clipboard_clear') as clear, patch.object(bible.window, 'clipboard_append') as append:
            bible.copy()
            clear.assert_called_once()
            append.assert_called_once_with(bible.passage.clipboard_text(False))
        bible.translation.set('CSP')
        bible.query.set('Jan 3:16')
        bible.change_translation()
        self.assertEqual(bible.passage.translation, 'CSP')
        bible.close()

    def test_dropdown_keyboard_mouse_dismiss_and_lifecycle(self):
        bible = BibleWindow(self.root)
        self.root.update()
        bible.query_entry.focus_force()
        self.root.update()
        book_y = bible.book_box.winfo_rooty()
        bible.query.set('Ja')
        self.root.update()
        self.assertTrue(bible.suggestion_popup.winfo_ismapped())
        self.assertEqual(bible.book_box.winfo_rooty(), book_y)
        self.assertEqual(bible.suggestion_popup.winfo_rooty(),
                         bible.query_entry.winfo_rooty()+bible.query_entry.winfo_height())
        bible.query_entry.event_generate('<Down>')
        self.root.update()
        self.assertEqual(bible.suggestions.curselection(), (0,))
        bible.query_entry.event_generate('<Return>')
        self.root.update()
        self.assertEqual(bible.query.get(), 'Jan ')
        self.assertFalse(bible.suggestion_popup.winfo_ismapped())
        bible.query.set('1 Ja')
        self.root.update()
        x, y, w, h = bible.suggestions.bbox(0)
        bible.suggestions.event_generate('<ButtonPress-1>', x=x+4, y=y+h//2)
        bible.suggestions.event_generate('<ButtonRelease-1>', x=x+4, y=y+h//2)
        self.root.update()
        self.assertEqual(bible.query.get(), '1 Janův ')
        self.assertFalse(bible.suggestion_popup.winfo_ismapped())
        bible.query.set('Ma')
        self.root.update()
        bible.query_entry.event_generate('<Escape>')
        self.root.update()
        self.assertFalse(bible.suggestion_popup.winfo_ismapped())
        bible.query.set('Lu')
        self.root.update()
        bible.preview.event_generate('<ButtonPress-1>', x=5, y=5)
        self.root.update()
        self.assertFalse(bible.suggestion_popup.winfo_ismapped())
        bible.query.set('Janovy listy 1:1')
        bible.lookup()
        self.root.update()
        self.assertTrue(bible.suggestion_popup.winfo_ismapped())
        bible.move_suggestion(1)
        bible.query_enter()
        self.assertEqual(bible.passage.book, '1 Janův')
        self.assertFalse(bible.suggestion_popup.winfo_ismapped())
        bible.query.set('Ma')
        self.root.update()
        popup = bible.suggestion_popup
        bible.close()
        self.root.update()
        self.assertFalse(popup.winfo_exists())

    def test_standalone_and_multiple_windows(self):
        # Root owned by BibleWindow, with no MainWindow/settings/recovery.
        self.root.destroy()
        first = BibleWindow()
        self.root = first.window
        other = BibleWindow(self.root)
        self.root.update()
        self.assertIsNone(first.insert_callback)
        self.assertIsNone(first.insert_button)
        self.assertIsNone(other.insert_button)
        other.close()
        self.assertTrue(first.alive())
        first.query.set('Jan 3:16–18')
        first.lookup()
        self.assertEqual(len(first.passage.verses), 3)

    def test_insert_into_empty_or_new_section_and_defaults(self):
        from dataclasses import replace
        editor = MainWindow(self.root, AppSettings(), recovery_dir=self.tmp.name)
        bible = editor.open_bible()
        self.assertEqual(bible.translation.get(), 'CSP')
        self.assertFalse(bible.numbers.get())
        self.assertFalse(bible.verse_per_line.get())
        bible.query.set('Jan 3:16')
        bible.lookup()
        bible.insert()
        first = editor.section()
        self.assertEqual(editor.sections.get(0), f'1. {first.reference}')
        bible.insert()
        self.assertEqual(len(editor.document.sections), 2)
        self.assertEqual(editor.document.sections[0], first)
        editor.add_section()
        blank = editor.section()
        editor.commit(replace(editor.document, sections=tuple(
            replace(s, break_before=False) if s.id == blank.id else s for s in editor.document.sections)))
        bible.insert()
        self.assertEqual(len(editor.document.sections), 3)
        self.assertEqual(editor.section().id, blank.id)
        self.assertFalse(editor.section().break_before)
        editor.undo()
        self.assertEqual(editor.section().reference, '')
        # A title alone is user content and must not be overwritten.
        current = editor.section()
        editor.commit(replace(editor.document, sections=tuple(
            replace(s, title='Vlastní název') if s.id == current.id else s for s in editor.document.sections)))
        bible.insert()
        self.assertEqual(len(editor.document.sections), 4)
        self.assertEqual(editor.document.sections[2].title, 'Vlastní název')
        # Picker still updates the passage without a separate display button.
        bible.selectors['end_verse'][0].set('18')
        bible.selector_changed('end', 'verse')
        self.assertEqual(len(bible.passage.verses), 3)
