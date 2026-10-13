"""Read-only Bible catalogue and reference resolution; no UI or legacy imports."""
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
import unicodedata


def normalized(value):
    value = unicodedata.normalize('NFKD', value.casefold())
    return ''.join(c for c in value if not unicodedata.combining(c) and c.isalnum())


# Canonical Czech labels, abbreviations and spelling variants used by our data.
BOOK_ROWS = '''Genesis|Gn|Gen|1 Mojžíšova|1 Moj
Exodus|Ex|2 Mojžíšova|2 Moj
Leviticus|Lv|Lev|Levitikus|3 Mojžíšova|3 Moj
Numeri|Nu|Nm|4 Mojžíšova|4 Moj
Deuteronomium|Dt|Deut|5 Mojžíšova|5 Moj
Jozue|Joz
Soudců|Sd|Soudci
Rút|Rt|Rut
1 Samuelova|1 S|1 Sam|1 Samuel
2 Samuelova|2 S|2 Sam|2 Samuel
1 Královská|1 Kr|1 Královské
2 Královská|2 Kr|2 Královské
1 Paralipomenon|1 Pa|1 Letopisů
2 Paralipomenon|2 Pa|2 Letopisů
Ezdráš|Ezd
Nehemjáš|Neh|Nehemiáš
Ester|Est|Kniha Ester
Jób|Jb|Job
Žalmy|Ž|Žl|Žalm
Přísloví|Př|Pr
Kazatel|Kaz
Píseň písní|Pís|Píseň|Pp
Izaiáš|Iz
Jeremiáš|Jr|Jer
Pláč|Pl
Ezechiel|Ez|Ezech
Daniel|Da|Dan
Ozeáš|Oz
Jóel|Jl|Joel
Ámos|Am|Amos
Abdijáš|Abd|Abdiáš
Jonáš|Jon
Micheáš|Mi|Mich
Nahum|Na|Nah
Abakuk|Abk|Habakuk
Sofonjáš|Sf|Sofoniáš
Ageus|Ag
Zacharjáš|Za|Zachariáš
Malachiáš|Mal
Matouš|Mt|Mat
Marek|Mk|Mar
Lukáš|Lk|Luk
Jan|J|Jn|Evangelium podle Jana|Janovo evangelium
Skutky|Sk|Skutky apoštolů
Římanům|Ř|Řím
1 Korintským|1 K|1 Kor
2 Korintským|2 K|2 Kor
Galatským|Ga|Gal
Efeským|Ef|Efezským
Filipským|Fp|Fil
Koloským|Ko|Kol
1 Tesalonickým|1 Te|1 Tes
2 Tesalonickým|2 Te|2 Tes
1 Timoteovi|1 Tm|1 Tim
2 Timoteovi|2 Tm|2 Tim
Titovi|Tt|Tit
Filemonovi|Fm|Flm
Židům|Žd|Heb
Jakub|Jk|Jakubův
1 Janův|1 J|1 Jn|1 Jan|1 Janova|1 list Janův|První Janův list
2 Janův|2 J|2 Jn|2 Jan|2 Janova|2 list Janův|Druhý Janův list
3 Janův|3 J|3 Jn|3 Jan|3 Janova|3 list Janův|Třetí Janův list
1 Petrův|1 Pt|1 Petr|1 Petrův list
2 Petrův|2 Pt|2 Petr|2 Petrův list
Juda|Ju|Judův
Zjevení|Zj|Zjevení Janovo|Apokalypsa'''
ALIASES = {row.split('|')[0]: tuple(row.split('|')) for row in BOOK_ROWS.splitlines()}
ALIAS_INDEX = {}
for book, aliases in ALIASES.items():
    for alias in aliases:
        ALIAS_INDEX.setdefault(normalized(alias), set()).add(book)
ALIAS_INDEX['janov'] = {'Jan', '1 Janův', '2 Janův', '3 Janův'}
ALIAS_INDEX['janovylisty'] = {'1 Janův', '2 Janův', '3 Janův'}
ALIAS_INDEX['januvlist'] = {'1 Janův', '2 Janův', '3 Janův'}
ALIAS_INDEX['janovalist'] = {'1 Janův', '2 Janův', '3 Janův'}


class BibleError(ValueError):
    pass


class AmbiguousBook(BibleError):
    def __init__(self, candidates):
        self.candidates = tuple(candidates)
        super().__init__('Vyberte jednoznačně knihu: ' + ', '.join(self.candidates))


@dataclass(frozen=True)
class Passage:
    translation: str
    book: str
    verses: tuple  # (chapter, verse, text)

    @property
    def reference(self):
        c, v, _ = self.verses[0]
        ec, ev, _ = self.verses[-1]
        suffix = '' if (c, v) == (ec, ev) else f'–{ev}' if c == ec else f'–{ec}:{ev}'
        return f'{self.book} {c}:{v}{suffix} ({self.translation})'

    def lines(self, numbers=True):
        cross = self.verses[0][0] != self.verses[-1][0]
        return tuple((f'{c}:{v} ' if cross else f'{v} ') + text if numbers else text
                     for c, v, text in self.verses)

    def clipboard_text(self, numbers=True):
        return self.reference + '\n' + '\n'.join(self.lines(numbers))

    def section(self, numbers=True):
        from .domain import TextSection, TextBlock, TextRun
        return TextSection('', tuple(TextBlock((TextRun(line),)) for line in self.lines(numbers)),
                           reference=self.reference, break_before=True)


class BibleService:
    def __init__(self, directory=None):
        root = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
        self.directory = Path(directory) if directory else root / 'bible'
        self.translations, self.problems, self.extents = {}, {}, {}
        for path in sorted(self.directory.glob('bible_*.json')):
            code = path.stem.removeprefix('bible_')
            try:
                raw = json.loads(path.read_text(encoding='utf-8-sig'))
                if not isinstance(raw, dict):
                    raise BibleError('Neplatná struktura překladu.')
                books, warnings = {}, []
                for key, chapters in raw.items():
                    candidates = ALIAS_INDEX.get(normalized(key), set())
                    if len(candidates) != 1 or not isinstance(chapters, dict):
                        warnings.append(f'Neznámá/neplatná kniha {key!r}.')
                        continue
                    book = next(iter(candidates))
                    if book in books:
                        raise BibleError(f'Duplicitní kniha {book}.')
                    valid = {}
                    for chapter, verses in chapters.items():
                        if not chapter.isdecimal() or int(chapter) < 1 or not isinstance(verses, dict):
                            warnings.append(f'{book}: neplatná kapitola {chapter!r}.')
                            continue
                        values = {int(v): text.strip() for v, text in verses.items()
                                  if v.isdecimal() and int(v) > 0 and isinstance(text, str) and text.strip()}
                        # Keep the declared last verse even when its text is empty.
                        # Whole-chapter requests must not silently truncate it.
                        self.extents[code, book, int(chapter)] = max(
                            (int(v) for v in verses if v.isdecimal() and int(v) > 0), default=0)
                        if len(values) != len(verses):
                            warnings.append(f'{book} {chapter}: chybné/prázdné verše nejsou dostupné.')
                        if values:
                            valid[int(chapter)] = values
                    if valid:
                        books[book] = valid
                if books:
                    self.translations[code] = books
                else:
                    warnings.append('Žádná bezpečně identifikovatelná kniha; překlad není dostupný.')
                if warnings:
                    self.problems[code] = ' '.join(warnings)
            except (OSError, ValueError) as exc:
                self.problems[code] = str(exc)

    def books(self, translation):
        return tuple(book for book in ALIASES if book in self.translations.get(translation, {}))

    def chapters(self, translation, book):
        return tuple(sorted(self.translations.get(translation, {}).get(book, {})))

    def verses(self, translation, book, chapter):
        return tuple(sorted(self.translations.get(translation, {}).get(book, {}).get(chapter, {})))

    def suggestions(self, text, translation):
        prefix = normalized(text)
        return tuple(book for book in self.books(translation)
                     if any(normalized(a).startswith(prefix) for a in ALIASES[book]))

    def resolve(self, text):
        key = normalized(text)
        candidates = ALIAS_INDEX.get(key)
        if candidates is None:
            candidates = {b for b, aliases in ALIASES.items() if any(normalized(a).startswith(key) for a in aliases)} if key else set()
        ordered = tuple(b for b in ALIASES if b in candidates)
        if len(ordered) > 1:
            raise AmbiguousBook(ordered)
        if not ordered:
            raise BibleError('Neznámý název nebo zkratka knihy.')
        return ordered[0]

    def parse(self, translation, text, selected_book=None):
        match = re.fullmatch(r'\s*(.+?)\s+(\d+)\s*(?::\s*(\d+))?\s*(?:[-–—]\s*(\d+)\s*(?::\s*(\d+))?)?\s*', text)
        if not match:
            raise BibleError('Zadejte např. Jan 3:16–18, Jan 3:36–4:2 nebo Žalm 23.')
        name, c, v, end, ev = match.groups()
        if selected_book:
            try:
                resolved = self.resolve(name)
                candidates = (resolved,)
            except AmbiguousBook as exc:
                candidates = exc.candidates
            if selected_book not in candidates:
                raise BibleError('Vybraná kniha neodpovídá odkazu.')
            book = selected_book
        else:
            book = self.resolve(name)
        c = int(c)
        ec = int(end) if ev or (end and v is None) else c
        verses = self.verses(translation, book, ec)
        if v is None:
            start = 1
            finish = self.extents.get((translation, book, ec), max(verses, default=0))
        else:
            start = int(v)
            finish = int(ev or end or v)
        return self.passage(translation, book, c, start, ec, finish)

    def passage(self, translation, book, chapter, verse, end_chapter, end_verse):
        if (chapter, verse) > (end_chapter, end_verse) or min(chapter, verse, end_chapter, end_verse) < 1:
            raise BibleError('Rozsah je obrácený nebo obsahuje nulu.')
        data = self.translations.get(translation, {}).get(book)
        if not data:
            raise BibleError(f'{book} není v překladu {translation} dostupná.')
        if chapter not in data or end_chapter not in data:
            raise BibleError('Požadovaná kapitola není v datech dostupná.')
        result = []
        for c in range(chapter, end_chapter + 1):
            values = data.get(c)
            if not values:
                raise BibleError(f'Kapitola {c} není v datech dostupná.')
            first = verse if c == chapter else 1
            last = end_verse if c == end_chapter else self.extents.get((translation, book, c), max(values))
            if last > max(values) or first not in values:
                raise BibleError(f'Požadovaný verš v kapitole {c} není dostupný.')
            for v in range(first, last + 1):
                if v not in values:
                    raise BibleError(f'Verš {c}:{v} chybí v datech; pasáž nelze vložit neúplně.')
                result.append((c, v, values[v]))
        return Passage(translation, book, tuple(result))
