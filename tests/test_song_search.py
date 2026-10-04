"""Search service regression tests, without a display."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from superpresenter.domain.song import Song
from superpresenter.services.song_repository import SongRepository
from superpresenter.services.song_search import SongSearch, normalize, excerpt


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'songs'
        self.root.mkdir()
        self.repo = SongRepository()
        self.song = Song.from_texts('Vzácný poklad', {
            'cs': {'v1': 'Tady je poklad mnohem vzácnější než zlato',
                   'r1': 'Zpíváme radostně nový refrén'},
            'uk': {'v1': 'Твій скарб і надія України'}}, {'default': 'v1 r1'})
        self.path = self.root / 'jiny_soubor.xml'
        self.repo.save(self.song, self.path)
        self.index = SongSearch(self.root)
        self.index.rebuild()

    def test_fields_and_normalization(self):
        for query, location in [('Vzácný poklad', 'Název'), ('ácný pok', 'Název'),
                                ('jiny_soubor', 'Soubor'), ('zlato', 'cs / v1'),
                                ('nový refrén', 'cs / r1'), ('надія', 'uk / v1'),
                                ('VZÁCNÝ POKLAD', 'Název'), ('vzacny poklad', 'Název'),
                                ('poklad   vzacnejsi', 'cs / v1'), ('vzácnější poklad', 'cs / v1')]:
            with self.subTest(query=query):
                result, = self.index.search(query)
                self.assertEqual(result.location, location)
                self.assertEqual(result.title, self.song.title)
        self.assertEqual(self.index.search(''), [])
        self.assertEqual(self.index.search('nenalezeno'), [])
        self.assertEqual(normalize('Твій Ї й'), 'твій ї й')
        self.assertNotEqual(normalize('й'), normalize('и'))

    def test_snippet_preserves_original(self):
        self.assertIn('Tady je poklad', self.index.search('Vzácný poklad')[0].snippet)
        result, = self.index.search('poklad vzacnejsi')
        self.assertEqual(result.snippet, 'Tady je poklad mnohem vzácnější než zlato')
        self.song.variants[0].sections[0].lines = ['úvod ' * 80 + 'poklad vzácnější ' + 'konec ' * 80]
        self.repo.save(self.song, self.path)
        self.index.rebuild()
        result, = self.index.search('poklad vzacnejsi')
        self.assertIn('poklad vzácnější', result.snippet)
        self.assertLessEqual(len(result.snippet), 152)

    def test_excerpt_targets_sixth_line_and_keeps_two_lines(self):
        lines = ['První', 'Druhý', 'Třetí', 'Čtvrtý', 'Pátý',
                 'Šestý ukrývá vzácnější poklad', 'Sedmý doplňuje rým', 'Osmý']
        self.assertEqual(excerpt('\n'.join(lines), ['vzacnejsi']),
                         'Šestý ukrývá vzácnější poklad\nSedmý doplňuje rým')
        self.assertEqual(excerpt('\n'.join(lines[:6]), ['poklad']),
                         'Pátý\nŠestý ukrývá vzácnější poklad')
        self.assertEqual(excerpt('první slovo\ndruhý poklad\ntřetí vzácnější',
                                 ['poklad', 'vzacnejsi']),
                         'druhý poklad\ntřetí vzácnější')

    def test_long_context_line_keeps_its_beginning(self):
        context = 'Začátek sousedního řádku ' + 'kontext ' * 40
        snippet = excerpt('Nalezený poklad\n' + context, ['poklad'])
        self.assertTrue(snippet.splitlines()[1].startswith('Začátek sousedního řádku'))
        self.assertTrue(snippet.endswith('…'))

    def test_relevance_and_ties(self):
        for i, (title, filename, body) in enumerate([
                ('poklad', 'a.xml', 'text'), ('poklad nebes', 'b.xml', 'text'),
                ('Můj poklad', 'c.xml', 'text'), ('Soubor', 'poklad.xml', 'text'),
                ('Zeta', 'd.xml', 'poklad'), ('Alfa', 'e.xml', 'poklad')]):
            self.repo.save(Song.from_texts(title, {'cs': {'v1': body}}), self.root / filename)
        self.path.unlink()
        self.index.rebuild()
        results = self.index.search('poklad')
        self.assertEqual([r.title for r in results], ['poklad', 'poklad nebes', 'Můj poklad', 'Soubor', 'Alfa', 'Zeta'])
        self.assertEqual([r.rank for r in results], [0, 1, 2, 3, 4, 4])

    def test_recursive_invalid_and_production_scope(self):
        nested = self.root / 'nested'
        nested.mkdir()
        self.repo.save(self.song, nested / 'valid.XML')
        (self.root / 'bad.xml').write_text('<slide')
        (self.root / '.xml').write_text('<slide/>')
        outside = self.root.parent / 'Testovací písně'
        outside.mkdir()
        self.repo.save(self.song, outside / 'test.xml')
        with self.assertLogs('superpresenter.services.song_search', level='WARNING'):
            self.index.rebuild()
        self.assertEqual(len(self.index.search('poklad')), 2)
        self.assertEqual(self.index.failures, [self.root / 'bad.xml'])

    def test_numeric_query_matches_number_prefix_and_sorts_numerically(self):
        for number in [100, 11, 21, 1, 110, 12, 10, 101]:
            # Titles deliberately sort in the opposite direction.
            title = f'Poklad {1000 - number}'
            self.repo.save(Song.from_texts(title, {'cs': {'v1': 'Text písně'}}),
                           self.root / f'{number} - poklad.xml')
        self.repo.save(Song.from_texts('1 nečíslovaná', {'cs': {'v1': 'Text 1'}}),
                       self.root / 'nečíslovaná.xml')
        self.index.rebuild()
        def numbers(query):
            return [int(result.path.stem.split(' - ')[0]) for result in self.index.search(query)]
        self.assertEqual(numbers('1'), [1, 10, 11, 12, 100, 101, 110])
        self.assertEqual(numbers(' 10 '), [10, 100, 101])
        self.assertEqual(numbers('11'), [11, 110])
        self.assertEqual(numbers('21'), [21])
        self.assertEqual(numbers('999'), [])
        self.assertEqual(self.index.search('1')[0].rank, 0)
        self.assertEqual(self.index.search('1')[0].display_title, '1 – Poklad 999')
        self.assertEqual(self.index.search('1')[0].snippet, 'Text písně')
        # Mixed text/number queries retain substring matching, including 21.
        self.assertIn(self.root.resolve() / '21 - poklad.xml',
                      [result.path for result in self.index.search('1 poklad')])
        self.assertEqual(self.index.search('text 1')[0].title, '1 nečíslovaná')

    def test_cached_queries_and_rebuild_after_save(self):
        with patch.object(self.index.repository, 'load', side_effect=AssertionError('reparse')):
            self.index.search('poklad')
            self.index.search('refrén')
        self.song.title = 'Aktualizovaný název'
        self.repo.save(self.song, self.path)
        self.assertFalse(self.index.search('aktualizovany'))
        self.index.rebuild()
        self.assertEqual(len(self.index.search('aktualizovany')), 1)

    def test_import_without_tk(self):
        code = "import sys; sys.modules['tkinter'] = None; from superpresenter.services.song_search import SongSearch; assert 'screeninfo' not in sys.modules"
        subprocess.run([sys.executable, '-B', '-c', code], check=True)
