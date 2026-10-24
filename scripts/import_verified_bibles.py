"""Convert supplied OpenSong XML; fail on any unaccounted structural damage."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from presentationpresenter.bible import ALIAS_INDEX, normalized, BibleService

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'bible'
AUDIT = OUT / 'source-verification'

class Reference(HTMLParser):
    def __init__(self):
        super().__init__(); self.stack = []; self.verses = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        verse = re.search(r'\bPs-119-(\d+)\b', attrs.get('class', ''))
        if tag not in ('br', 'hr', 'img', 'meta', 'link', 'input'):
            self.stack.append((tag, int(verse[1]) if verse else None, tag in ('sup','h3','h4')))
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]; break
    def handle_data(self, data):
        if any(x[2] for x in self.stack): return
        verse = next((x[1] for x in reversed(self.stack) if x[1]), None)
        if verse: self.verses[verse] = self.verses.get(verse, '') + data + ' '

def main(source):
    AUDIT.mkdir(exist_ok=True)
    ref = Reference()
    ref.feed((AUDIT / 'B21-Psalm119.html').read_text(encoding='utf-8'))
    assert all(v in ref.verses for v in range(100,177)), 'Incomplete external reference'
    changes, summaries, pending = [], [], {}
    for filename, code in [('CZ_Kb','BKR'),('CZ_Csp','CSP'),('CZ_Cep','EKU'),('CZ_Nbk21','B21'),('CZ_Nbk','NKB')]:
        path = source / filename
        raw = path.read_bytes()
        root = ET.fromstring(raw)
        books = {}; removed = 0; gaps = []
        for b in root:
            name = b.get('n')
            if name == 'NULL':
                assert code == 'NKB' and not ''.join(b.itertext()).strip()
                removed += 1; continue
            canonical = {'Izajáš':'Izaiáš','Jeremjáš':'Jeremiáš'}.get(name,name)
            candidates = ALIAS_INDEX.get(normalized(canonical), set())
            assert len(candidates) == 1, name
            canonical = next(iter(candidates))
            assert canonical not in books
            if canonical != name: changes.append(dict(code=code,kind='book-name',before=name,after=canonical))
            chapters = {}; books[canonical] = chapters
            for c in b:
                cn = c.get('n'); assert cn.isdecimal() and int(cn)>0 and cn not in chapters
                verses = {}; chapters[cn] = verses
                for index,v in enumerate(c,1):
                    vn = v.get('n'); text = ''.join(v.itertext()).strip()
                    before = dict(number=vn,text=text)
                    assert vn.isdecimal() and int(vn)>0 and text and '\ufffd' not in text
                    if code == 'BKR' and canonical == 'Žalmy' and (cn,index) in [('55',24),('65',14)]:
                        assert vn == {'55':'23','65':'13'}[cn]
                        vn = str(index)
                    if code == 'B21' and canonical == 'Žalmy' and cn == '119' and index >= 100:
                        assert vn == str(index)[:2] and text.startswith(str(index)[2] + ' ')
                        vn = str(index); text = text[2:].strip()
                        # Compare every repaired verse with the independently published B21.
                        other = ref.verses[index].strip()
                        assert normalized(text) == normalized(other), (index,text,other)
                    if code == 'B21' and canonical == 'Deuteronomium' and cn == '9' and vn == '23':
                        text, tail = text.split('24Bouřili',1)
                        assert tail == ' jste se proti Hospodinu ode dne, kdy jsem vás poznal!'
                        verses['24'] = 'Bouřili' + tail
                        text = text.rstrip()
                        changes.append(dict(code=code,kind='split-verse',reference='Deuteronomium 9:23–24',before=before,after={'23':text,'24':verses['24']}))
                    elif before != dict(number=vn,text=text):
                        changes.append(dict(code=code,kind='number-repair',book=canonical,chapter=cn,before=before,after=dict(number=vn,text=text)))
                    assert vn not in verses, (code,canonical,cn,vn)
                    verses[vn] = text
                chapters[cn] = dict(sorted(verses.items(), key=lambda x:int(x[0])))
                missing = sorted(set(range(1,max(map(int,verses))+1))-set(map(int,verses)))
                if missing: gaps.append(dict(book=canonical,chapter=cn,missing=missing))
            assert sorted(map(int,chapters)) == list(range(1,len(chapters)+1))
        assert len(books) == (27 if code == 'NKB' else 66)
        assert removed == (39 if code == 'NKB' else 0)
        pending[code] = books
        summaries.append(dict(code=code,source=filename,sha256=hashlib.sha256(raw).hexdigest(),books=len(books),chapters=sum(map(len,books.values())),verses=sum(len(v) for c in books.values() for v in c.values()),removed_empty_placeholders=removed,numbering_gaps_preserved=gaps))
    # Verify input/output text conservation, except explicit, audited number repairs.
    backup = AUDIT / 'previous-json'
    backup.mkdir(exist_ok=True)
    for code, books in pending.items():
        target = OUT / f'bible_{code}.json'
        old = backup / target.name
        if target.exists() and not old.exists(): shutil.copy2(target,old)
        target.write_text(json.dumps(books,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (AUDIT/'audit.json').write_text(json.dumps(dict(summaries=summaries,changes=changes),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    service = BibleService(OUT)
    assert not service.problems, service.problems
    for code,books in pending.items():
        assert len(service.books(code)) == len(books)
        for book,chapters in books.items():
            for chapter,verses in chapters.items():
                assert service.translations[code][book][int(chapter)] == {int(v):t for v,t in verses.items()}
    print(json.dumps(summaries,ensure_ascii=True,indent=2))
    print('BibleService: all output verses match; no catalogue warnings.')

if __name__ == '__main__': main(Path(sys.argv[1]))
