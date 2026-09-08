"""Extracted presentation source; legacy behavior is preserved."""
from copy import deepcopy
import xml.etree.ElementTree as ET
from superpresenter.domain.song import Song
from superpresenter.services.song_repository import SongRepository, SongLoadError
from superpresenter.services.construct_parser import parse_construct


class _LegacyWidgetSource():
    def __init__(self, path:str):
        self.fileName = readFileName(path)
        try:
            with open(path,'r',encoding='utf8') as f:
                self.sourceText = f.read()
            self.err = 0
        except (OSError, UnicodeError):
            self.err = 1
        self.variants = ['-----','-----','-----']
        self.sections = []
        self.repetitions = ''
        self.path = path

    def validate(self):
        e = 0
        vars = []
        secs = []
        try:
            self.importSlideName()
        except:
            e += 8
        try:
            self.importRepetitions()
        except:
            e += 4
        try:
            vars = self.importVariants()
        except:
            e += 2
        if e == 0:
            try:
                secs = self.importSections(vars)
            except:
                e += 1
        if e == 0:
            try:
                self.importSlide(vars, secs)
            except:
                e += 16
        return e, vars, secs

    def importSlide(self, variants, sections):
        vars = 0
        secs = 0
        levels= ['','','']
        slide = {}
        for line in self.sourceText.splitlines():
            line = clearEmpties(line)
            if line == '':
                continue
            elif line[0] == '<':
                (tag, cls, idx) = readTag(line)
                if not(cls):
                    params = []
                    (name, idx) = readTagName(line, idx)
                    (params) = readTagParams(line, idx)

                if tag == 'slide':
                    if cls:
                        break
                    else:
                        slide = {'name':name}
                        for param in params:
                            slide.update(param)
                        if slide['name'] == '':
                            slide['name'] = self.fileName
                        levels[0] = 'main'

                elif tag == 'variant':
                    if levels[0] == '':
                        continue
                    elif cls:
                        levels[1] = ''
                        levels[2] = ''
                        secs = 0
                    else:
                        vars += 1
                        var = {'name':name}
                        for param in params:
                            var.update(param)
                        if var['name'] == '':
                            var['name'] = f'variant {vars}'
                        levels[1] = var.pop('name')
                        if levels[1] in variants:
                            slide.update({levels[1]:var})
                        else:
                            levels[1] = ''

                elif tag == 'section':
                    if levels[1] == '':
                        continue
                    elif cls:
                        levels[2] = ''
                    else:
                        secs += 1
                        var = {'name':name, 'lines':[]}
                        for param in params:
                            var.update(param)
                        if var['name'] == '':
                            var['name'] = f's{secs}'
                        levels[2] = var.pop('name')
                        if levels[2] in sections:
                            slide[levels[1]].update({levels[2]:var})
                        else:
                            levels[2] = ''
                else:
                    continue

            else:
                if levels[2] == '':
                    continue
                else:
                    slide[levels[1]][levels[2]]['lines'].append(line)

        return slide

    def importSections(self, variants) -> list:
        vars = 0
        secs = 0
        levels= ['','']
        sections = []
        for line in self.sourceText.splitlines():
            line = clearEmpties(line)
            if line == '':
                continue
            elif line[0] == '<':
                (tag, cls, idx) = readTag(line)
                if not(cls):
                    params = []
                    (name, idx) = readTagName(line, idx)
                    (params) = readTagParams(line, idx)

                if tag == 'slide':
                    if cls:
                        break
                    else:
                        var = {'name':name}
                        for param in params:
                            var.update(param)
                        if var['name'] == '':
                            var['name'] = self.fileName
                        levels[0] = 'main'

                elif tag == 'variant':
                    if levels[0] == '':
                        continue
                    elif cls:
                        levels[1] = ''
                        secs = 0
                    else:
                        vars += 1
                        var = {'name':name}
                        for param in params:
                            var.update(param)
                        if var['name'] == '':
                            var['name'] = f'variant {vars}'
                        levels[1] = var.pop('name')
                        if levels[1] in variants:
                            continue
                        else:
                            levels[1] = ''

                elif tag == 'section':
                    if levels[1] == '' or cls:
                        continue
                    else:
                        secs += 1
                        var = {'name':name}
                        for param in params:
                            var.update(param)
                        if var['name'] == '':
                            var['name'] = f's{secs}'
                        name = var.pop('name')
                        if name in sections:
                            continue
                        else:
                            sections.append(name)
                else:
                    continue

            else:
                continue

        return sections

    def importRepetitions(self):
        vars = 0
        levels= ['','']
        reps = {}
        for line in self.sourceText.splitlines():
            line = clearEmpties(line)
            if line == '':
                continue
            elif line[0] == '<':
                (tag, cls, idx) = readTag(line)
                if not(cls) and tag == 'repetition':
                    params = []
                    (name, idx) = readTagName(line, idx)
                    (params) = readTagParams(line, idx)

                if tag == 'slide':
                    if cls:
                        break
                    else:
                        levels[0]='in'

                elif tag == 'repetition':
                    if levels[0] == '':
                        continue
                    elif cls:
                        levels[1] = ''
                    else:
                        vars += 1
                        var = {'name':name, 'guide':''}
                        for param in params:
                            var.update(param)
                        if var['name'] == '':
                            var['name'] = f'repetition {vars}'
                        levels[1] = var.pop('name')
                        reps.update({levels[1]:var})

            else:
                if levels[1] == '':
                    continue
                else:
                    reps[levels[1]]['guide'] += (line.strip() + ' ')
        for k in reps:
            reps[k]['guide'] = reps[k]['guide'].strip()

        return reps

    def importVariants(self):
        vars = 0
        levels= ''
        variants = []
        for line in self.sourceText.splitlines():
            line = clearEmpties(line)
            if line == '':
                continue
            elif line[0] == '<':
                (tag, cls, idx) = readTag(line)
                if not(cls) and tag == 'variant':
                    params = []
                    (name, idx) = readTagName(line, idx)
                    (params) = readTagParams(line, idx)

                if tag == 'slide':
                    if cls:
                        break
                    else:
                        levels='in'

                elif tag == 'variant':
                    if levels == '' or cls:
                        continue
                    else:
                        vars += 1
                        var = {'name':name}
                        for param in params:
                            var.update(param)
                        if var['name'] == '':
                            var['name'] = f'variant {vars}'
                        name = var.pop('name')
                        variants.append(name)

            else:
                continue

        return variants

    def importSlideName(self):
        slide_name = self.fileName
        for line in self.sourceText.splitlines():
            line = clearEmpties(line)
            if not line:
                continue
            if line[0] == '<':
                tag, cls, idx = readTag(line)
                if tag == 'slide' and not cls:
                    name, idx = readTagName(line, idx)
                    params = readTagParams(line, idx)
                    slide = {'name': name}
                    for p in params:
                        slide.update(p)
                    if slide['name'] == '':
                        slide['name'] = self.fileName
                    slide_name = slide['name']
                    break
        return slide_name

    def readInstructions(self):
        """Compile the independent parser's result for the existing renderers.

        Parsing errors propagate as ConstructError with an original-text offset.
        Commit both legacy fields only after successful parsing and compilation.
        """
        construct = parse_construct(self.repetitions, self.legalSections())
        instructions, used = construct.to_legacy()
        self.instructions = instructions
        self.usedSections = used
        return construct

    def legalSections(self):
        legals = self.importSections([self.variants[0]])
        for var in self.variants[1:]:
            if var != '-----':
                secs = self.importSections([var])
                for idx in range(len(legals)-1,-1,-1):
                    if not legals[idx] in secs:
                        legals.pop(idx)
        return legals

    def _flatten_group_sequence(self, slide):
        """Rozbalí instrukce na sekvenci trojic (sec_name, kind, length),
           kde kind je 'all' (celá sloka) nebo 'part' (výřez/řádek/interval)."""
        secs = self.usedSections
        vars_ = [v for v in self.variants if v != '-----']
        insts = self.instructions
        stk = []
        for a in insts:
            if a == 'all':
                s_idx = stk.pop()
                sec = secs[s_idx]
                n = len(slide[vars_[0]][sec]['lines'])
                stk.append([(sec, 'all', n)])
            elif a == 'line':
                _ = stk.pop()
                s_idx = stk.pop()
                sec = secs[s_idx]
                stk.append([(sec, 'part', 1)])
            elif a == 'lins':
                idx1 = stk.pop()
                idx0 = stk.pop() - 1
                s_idx = stk.pop()
                sec = secs[s_idx]
                stk.append([(sec, 'part', max(0, idx1 - idx0))])
            elif a == 'conn':
                n = stk.pop()
                seq = []
                while n > 0:
                    seq = stk.pop() + seq
                    n -= 1
                stk.append(seq)
            elif a == 'mult':
                n = int(stk.pop())
                seq = stk.pop()
                stk.append(seq * n)
            else:
                stk.append(a)
        return stk.pop() if stk else []

    def _build_group_lengths(self, slide):
        secs   = self.usedSections
        insts  = self.instructions
        vars_  = [v for v in self.variants if v != '-----']

        mem = []
        for a in insts:
            if a == 'all':
                s_idx = mem.pop()
                n = len(slide[vars_[0]][secs[s_idx]]['lines'])
                block = [(s_idx, 'all')] + [(s_idx, 'part')] * max(0, n - 1)
                mem.append(block)

            elif a == 'line':
                _line_idx = mem.pop()
                s_idx = mem.pop()
                mem.append([(s_idx, 'part')])

            elif a == 'lins':
                idx1 = mem.pop()
                idx0 = mem.pop() - 1
                s_idx = mem.pop()
                count = max(0, idx1 - idx0)
                mem.append([(s_idx, 'part')] * count)

            elif a == 'conn':
                n = mem.pop()
                seq = []
                while n > 0:
                    seq = seq + mem.pop()
                    n -= 1
                mem.append(seq)

            elif a == 'mult':
                n = int(mem.pop())
                seq = mem.pop()
                mem.append(seq * n)

            else:
                mem.append(a)

        seq = mem.pop() if mem else []

        groups = []
        run = 0
        last_sec = None

        for sec, kind in seq:
            if last_sec is None:
                run = 1
                last_sec = sec
                continue
            if sec != last_sec or kind == 'all':
                groups.append(run)
                run = 1
                last_sec = sec
            else:
                run += 1

        if run:
            groups.append(run)

        return groups

    def constructLines(self, sourceTypes:list):
        slide = self.importSlide(self.variants, self.usedSections)
        lines = {}

        groups = self._build_group_lengths(slide)
        lines['group_lengths'] = groups

        # Základní nastavení vars (pro případ, že by nebyl short2)
        final_vars = []

        for sT in sourceTypes:
            if sT['type'] == 'long':
                lines['long'], vars_long = self.longText(slide)
                lines['longsteps'] = list(range(len(lines['long'][0])))
                if not final_vars: final_vars = vars_long

            if sT['type'] == 'short':
                stp, lns = self.shortText(slide, sT.get('repeat_start',''), sT.get('repeat_end',''))
                lines['shortsteps'] = stp
                lines['short'] = lns

            elif sT['type'] == 'short2':
                stp, lns = self.shortText(slide, sT.get('repeat_start',''), sT.get('repeat_end',''))
                pairmap = []
                if len(lns) == 1:
                    groups = self._build_group_lengths(slide)
                    src = lns[0]
                    a, b = [], []
                    pos = 0
                    for L in groups:
                        i = 0
                        while i < L:
                            a.append(src[pos + i])
                            if i + 1 < L:
                                b.append(src[pos + i + 1])
                                pairmap.append((pos + i, pos + i + 1))
                            else:
                                b.append('')
                                pairmap.append((pos + i, None))
                            i += 2
                        pos += L
                    lns = [a, b]
                    stp = list(range(len(a)))

                lines['short2steps'] = stp
                lines['short2'] = lns
                if pairmap:
                    lines['short2pairmap'] = pairmap

                # Přepíšeme seznam pro UI na dvojřádky
                new_ui_list = []
                for i in range(len(a)):
                    line1 = a[i]
                    line2 = b[i] if b[i] else ""
                    new_ui_list.append(f"{line1} / {line2}".strip())

                final_vars = new_ui_list

        self.lines = lines
        return final_vars

    def longText(self, slide):
        secs = self.usedSections
        insts = self.instructions
        mem = []
        vars = []
        for var in self.variants:
            if var != '-----':
                vars.append(var)
        for a in insts:
            if a == 'all':
                a = mem.pop()
                n = 0
                lins = [[]]
                srclns = slide[vars[0]][secs[a]]['lines']
                for line in srclns:
                    n += 1
                    lins[0].append(line)
                for var in vars[1:]:
                    lins.append([])
                    srclns = slide[var][secs[a]]['lines']
                    for idx in range(n):
                        if idx < len(srclns):
                            lins[-1].append(srclns[idx])
                        else:
                            lins[-1].append('')
                mem.append(lins)
            elif a == 'line':
                idx = mem.pop()-1
                a = mem.pop()
                lins = []
                for var in vars:
                    lins.append([])
                    srclns = slide[var][secs[a]]['lines']
                    if idx < len(srclns):
                        lins[-1].append(srclns[idx])
                    else:
                        lins[-1].append('')
                mem.append(lins)
            elif a == 'lins':
                idx1 = mem.pop()
                idx0 = mem.pop()-1
                a = mem.pop()
                lins = []
                for var in vars:
                    lins.append([])
                    srclns = slide[var][secs[a]]['lines']
                    for idx in range(idx0,idx1):
                        if idx < len(srclns):
                            lins[-1].append(srclns[idx])
                        else:
                            lins[-1].append('')
                mem.append(lins)
            elif a == 'conn':
                n = mem.pop()
                lins = []
                for _ in vars:
                    lins.append([])
                while n > 0:
                    a = mem.pop()
                    for idx in range(len(lins)):
                        lins[idx] += a[idx]
                    n -= 1
                mem.append(lins)
            elif a == 'mult':
                n = mem.pop()
                a = mem.pop()
                lins = []
                for _ in vars:
                    lins.append([])
                while n > 0:
                    for idx in range(len(lins)):
                        lins[idx] += a[idx]
                    n -= 1
                mem.append(lins)
            else:
                mem.append(a)
        return mem.pop(), vars

    def shortText(self, slide, rep1, rep2):
        secs = self.usedSections
        insts = self.instructions
        mem = []
        vars = []
        steps = []
        for var in self.variants:
            if var != '-----':
                vars.append(var)
        for a in insts:
            if a == 'all':
                stp = 0
                a = mem.pop()
                n = 0
                lins = [[]]
                steps = []
                srclns = slide[vars[0]][secs[a]]['lines']
                for line in srclns:
                    n += 1
                    lins[0].append(line)
                    steps.append(stp)
                    stp += 1
                for var in vars[1:]:
                    lins.append([])
                    srclns = slide[var][secs[a]]['lines']
                    for idx in range(n):
                        if idx < len(srclns):
                            lins[-1].append(srclns[idx])
                        else:
                            lins[-1].append('')
                mem.append(lins)
                mem.append(steps)
            elif a == 'line':
                stp = 0
                idx = mem.pop()-1
                a = mem.pop()
                lins = []
                steps = []
                for var in vars:
                    lins.append([])
                    srclns = slide[var][secs[a]]['lines']
                    if idx < len(srclns):
                        lins[-1].append(srclns[idx])
                    else:
                        lins[-1].append('')
                steps.append(stp)
                stp += 1
                mem.append(lins)
                mem.append(steps)
            elif a == 'lins':
                stp = 0
                idx1 = mem.pop()
                idx0 = mem.pop()-1
                a = mem.pop()
                lins = []
                steps = []
                for var in vars:
                    lins.append([])
                    srclns = slide[var][secs[a]]['lines']
                    for idx in range(idx0,idx1):
                        if idx < len(srclns):
                            lins[-1].append(srclns[idx])
                        else:
                            lins[-1].append('')
                for idx in range(idx0,idx1):
                    steps.append(stp)
                    stp += 1
                mem.append(lins)
                mem.append(steps)
            elif a == 'conn':
                stp = 0
                n = mem.pop()
                lins = []
                steps = []
                for _ in vars:
                    lins.append([])
                while n > 0:
                    s = mem.pop()
                    a = mem.pop()
                    s = [x+stp for x in s]
                    steps += s
                    stp = s[-1]+1
                    for idx in range(len(lins)):
                        lins[idx] += a[idx]
                    n -= 1
                mem.append(lins)
                mem.append(steps)
            elif a == 'mult':
                n = mem.pop()
                s = mem.pop()
                lins = mem.pop()
                steps = []
                for l in lins:
                    l[0] = rep1 + l[0]
                    if n == 2:
                        l[-1] = l[-1] + rep2
                    else:
                        l[-1] = l[-1] + rep2 + f'×{n}'
                while n > 0:
                    steps = steps + s
                    n -= 1
                mem.append(lins)
                mem.append(steps)
            else:
                mem.append(a)
        return mem.pop(), mem.pop()


class WidgetSource(_LegacyWidgetSource):
    """Presentation adapter over the same Song that the editor uses.

    The old line parser only imports malformed legacy files; subsequent editing
    and presentation use the resulting shared model.
    """
    def __init__(self, path, song=None):
        super().__init__(path)
        self.load_warning = None
        self.song = deepcopy(song) if song is not None else None
        if self.song is None:
            try:
                self.song = SongRepository().load(path)
            except SongLoadError as exc:
                if not isinstance(exc.cause, ET.ParseError):
                    self.err = 1
                    self.load_warning = str(exc)
                    return
                try:
                    variants = super().importVariants()
                    sections = super().importSections(variants)
                    slide = super().importSlide(variants, sections)
                    reps = super().importRepetitions()
                    if not variants or not sections:
                        raise ValueError("Soubor neobsahuje varianty a sekce.")
                    main = next((name for name, rep in reps.items() if str(rep.get('main', '')).lower() in ('1', '1.0', 'true', 'yes')), 'default' if 'default' in reps else next(iter(reps), ''))
                    self.song = Song.from_texts(super().importSlideName(),
                        {lang: {sid: '\n'.join(slide[lang][sid]['lines']) for sid in sections if sid in slide[lang]} for lang in variants},
                        {name: rep['guide'] for name, rep in reps.items()}, main)
                    self.load_warning = str(exc)
                except Exception as legacy_exc:
                    self.err = 1
                    self.load_warning = f"{exc}; {legacy_exc}"
            except (OSError, ValueError) as exc:
                self.err = 1
                self.load_warning = str(exc)
        if self.song is not None:
            self.err = 0
            self.repetitions = self.song.guide

    def loadSong(self):
        """Read the original ordered model for existing repository consumers."""
        return SongRepository().load(self.path)

    def importSlideName(self):
        return self.song.title or self.fileName

    def importVariants(self):
        return list(self.song.variant_texts)

    def importSections(self, variants):
        return list(dict.fromkeys(sid for lang in variants for sid in self.song.variant_texts.get(lang, {})))

    def importRepetitions(self):
        return {name: {'guide': guide, 'main': '1' if name == self.song.main_repetition else '0'}
                for name, guide in self.song.repetition_texts.items()}

    def importSlide(self, variants, sections):
        slide = dict(self.song.attributes)
        slide['name'] = self.importSlideName()
        for i, variant in enumerate(self.song.variants, 1):
            lang = variant.name or f"variant {i}"
            if lang not in variants:
                continue
            data = dict(variant.attributes)
            for j, section in enumerate(variant.sections, 1):
                sid = section.identifier or f"s{j}"
                if sid in sections:
                    attrs = dict(section.attributes)
                    content = '\n'.join(section.lines).strip()
                    attrs['lines'] = [clearEmpties(line) for line in content.splitlines() if clearEmpties(line)]
                    data[sid] = attrs
            slide[lang] = data
        return slide


def readTagName(tag:str, idx=0):
    name = ''
    l = len(tag)
    while idx < l:
        a = tag[idx]
        if a == "=" or a == ':' or a == '>':
            return name, idx
        if a == "'" or a == '"':
            break
        idx += 1
    idx += 1
    while idx < l:
        b = tag[idx]
        if b == a or b == '>' or b == '=' or b == ':':
            break
        name = name + b
        idx += 1
    return name, idx


def readFileName(path:str):
    name = ''
    idx = len(path)-1
    while idx > 0:
        a = path[idx]
        idx -= 1
        if a == '\\' or a =='/':
            break
        if a == '.':
            name = ''
            continue
        name = a + name
    return name


def clearEmpties(line: str):
    # odstraň BOM a levé mezery/taby; čistě bílé řádky vrať jako ''
    s = line.replace('\uFEFF', '').lstrip(' \t')
    return s if s else ''


def readTagParams(tag:str, idx=0):
    l = len(tag)
    out = []
    while idx < l:
        if tag[idx] == '>':
            break
        if tag[idx] == '=' or tag[idx] == ':':
            # var name
            var = ''
            k = idx-1
            b = tag[k]
            while b == ' ' or b == '\t':
                k -= 1
                b = tag[k]
            while not(b == ' ' or b == '\t'):
                var = b + var
                k -= 1
                b = tag[k]
            # value
            val = ''
            idx += 1
            if idx == l:
                return out
            a = tag[idx]
            if a == '>':
                return out
            while a == ' ' or a == '\t':
                idx += 1
                if idx == l:
                    return out
                a = tag[idx]
                if a == '>':
                    return out
            if a == '"' or a == "'":
                idx += 1
                if idx == l:
                    return out
                b = tag[idx]
                while not(b == a):
                    val = val + b
                    idx += 1
                    if idx == l:
                        out.append({var:val})
                        return out
                    b = tag[idx]
                out.append({var:val})
            else:
                val = val + a
                idx += 1
                if idx == l:
                    try:
                        numval = float(val)
                        out.append({var:numval})
                    except ValueError:
                        out.append({var:val})
                    return out
                a = tag[idx]
                while not(a == ' ' or a == '\t' or a =='>'):
                    val = val + a
                    idx += 1
                    if idx == l:
                        try:
                            numval = float(val)
                            out.append({var:numval})
                        except ValueError:
                            out.append({var:val})
                        return out
                    a = tag[idx]
                try:
                    numval = float(val)
                    out.append({var:numval})
                except ValueError:
                    out.append({var:val})
        idx += 1
    return out


def readTag(tag:str):
    isClose = tag[1] == '/'
    name = ''
    idx = 0
    for a in tag[(1+isClose):]:
        if a==' ' or a=='\t' or a=='>' or a=='"' or a=="'":
            break
        name = name + a
        idx += 1
    return name, isClose, idx
