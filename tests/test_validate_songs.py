"""Isolated data checks, without importing the GUI or changing real songs."""

from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

from scripts.validate_songs import main, validate_directory, validate_song


VALID = ('<slide name="Píseň"><variant name="čeština">'
         '<section name="v1">Text písně</section></variant>'
         '<repetition>v1 v1</repetition></slide>')


class SongValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.path = self.directory / "píseň\u00a0test.xml"

    def check(self, xml):
        self.path.write_text(xml, encoding="utf-8")
        before = self.path.read_bytes()
        issues = validate_song(self.path)
        self.assertEqual(before, self.path.read_bytes())
        return {(i.severity, i.code) for i in issues}

    def test_valid_song(self):
        self.assertEqual(self.check(VALID), set())

    def test_unclosed_section(self):
        self.assertEqual(self.check(VALID.replace('</section>', '')), {('error', 'xml')})

    def test_wrong_root(self):
        self.assertIn(('error', 'root'), self.check(VALID.replace('slide', 'song')))

    def test_missing_variant(self):
        self.assertIn(('error', 'variant_missing'), self.check('<slide name="Song"/>'))

    def test_unknown_reference(self):
        self.assertIn(('error', 'repetition_reference'), self.check(VALID.replace('v1 v1', 'v1 r1')))

    def test_missing_repetition_is_warning(self):
        self.assertEqual(self.check(VALID.replace('<repetition>v1 v1</repetition>', '')),
                         {('warning', 'repetition_missing')})

    def test_unknown_expression_is_not_partially_interpreted(self):
        for expression in ['(v1 r9)*3', 'v1.1:2', '__import__("os")', 'v1,r9']:
            with self.subTest(expression=expression):
                self.assertEqual(self.check(VALID.replace('v1 v1', expression)),
                                 {('warning', 'repetition_unchecked')})

    def test_legacy_ids(self):
        for sid in ['r', 'b', 'r0', 'v1a', 'v1b']:
            with self.subTest(sid=sid):
                self.assertEqual(self.check(VALID.replace('v1', sid)), set())

    def test_required_names_and_text(self):
        for old, new, code in [('name="Píseň"', 'name=" "', 'title'),
                               ('name="čeština"', '', 'variant_name'),
                               ('name="v1"', 'name="bad id"', 'section_id'),
                               ('Text písně', '  ', 'section_text')]:
            with self.subTest(code=code):
                self.assertIn(('error', code), self.check(VALID.replace(old, new)))

    def test_duplicate_id(self):
        self.assertIn(('error', 'section_duplicate'), self.check(VALID.replace(
            '</variant>', '<section name="v1">Other</section></variant>')))

    def test_reference_missing_in_one_variant(self):
        self.assertEqual(self.check(VALID.replace('</variant>', '</variant>'
            '<variant name="English"><section name="v2">Text</section></variant>')),
            {('warning', 'repetition_variant')})

    def test_recursive_scan_and_exit_codes(self):
        nested = self.directory / 'nested'
        nested.mkdir()
        (nested / 'song.xml').write_text(VALID, encoding='utf-8')
        self.assertEqual(len(validate_directory(self.directory)[0]), 1)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.directory)]), 0)
            self.check(VALID.replace('<repetition>v1 v1</repetition>', ''))
            self.assertEqual(main([str(self.directory)]), 0)
            self.check('<broken>')
            self.assertEqual(main([str(self.directory), '--details']), 1)

    def test_missing_and_empty_directory(self):
        for directory in [self.directory, self.directory / 'absent']:
            with self.subTest(directory=directory), self.assertRaises(ValueError):
                validate_directory(directory)


if __name__ == '__main__':
    unittest.main()
