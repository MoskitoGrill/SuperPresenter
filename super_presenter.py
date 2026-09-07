import os
from copy import deepcopy
import xml.etree.ElementTree as ET
from superpresenter.domain.song import Song
from superpresenter.services.song_repository import SongRepository, SongLoadError
from superpresenter.services.song_edit_session import validate_editor_fields
import tkinter as tk
from os import path
from screeninfo import get_monitors
import json
from tkinter import font as tkFont
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox as tkmsg
import time
import math
from PIL import ImageTk, Image
from superpresenter.services.construct_parser import parse_construct, ConstructError
from superpresenter.services.stationary_navigation import (
    CueNavigation, StationaryPageWidget, build_plan, style_mode,
)


class _LegacyWidgetSource():
    def __init__(self, path:str):
        self.fileName = readFileName(path)
        try:
            with open(path,'r',encoding='utf8') as f:
                self.sourceText = f.read()
            self.err = 0
        except:
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


class SortingWin():
    def __init__(self, masterWin:tk.Tk, winStyle, lines, positions):
        self.win = tk.Toplevel(masterWin)
        self.win.configure(winStyle['window'])
        self.win.geometry(f'+{masterWin.winfo_rootx() + 100}'+\
            f'+{masterWin.winfo_rooty() + 100}')

        self.selected = 0

        myfont = tkFont.Font(name=winStyle['font']['name'],
            family=winStyle['font']['family'],
            size=winStyle['font']['size'],
            weight=winStyle['font']['weight'])
        self.lines = []
        self.labels = []
        self.positions = positions
        self.positions0 = positions
        idx = 0
        self.win.bind('<B1-Motion>',self.motion)
        for line in lines:
            col = 2*int(idx/winStyle['rows'])
            row = idx % winStyle['rows']

            self.labels.append(tk.Label(self.win, font=myfont, text=f' {idx+1}.'))
            self.labels[-1].config(winStyle['order'])
            self.labels[-1].grid(column = col, row = row)

            self.lines.append(tk.Label(self.win, font=myfont, text= line))
            self.lines[-1].config(winStyle['lines'])
            self.lines[-1].grid(column = col+1, row = row)
            self.lines[-1].bind('<Button>', self.click)
            self.lines[-1].bind('<ButtonRelease>', self.place)

            idx += 1
        self.rows = winStyle['rows']
        self.win.update()
        self.w = self.lines[0].winfo_x() + self.lines[0].winfo_width()
        self.h = self.lines[0].winfo_y() + self.lines[0].winfo_height()

    def click(self, e:tk.Event):
        self.x = e.x_root - self.win.winfo_rootx()
        self.y = e.y_root - self.win.winfo_rooty()
        self.idx = int(self.x/self.w)*self.rows + int(self.y/self.h)
        self.t = time.time()
        self.c1 = 0
        self.selected = 1
        self.win.after(30, self.drag)
        self.skip = 0

    def motion(self, e):
        self.x = e.x_root - self.win.winfo_rootx()
        self.y = e.y_root - self.win.winfo_rooty()

    def drag(self):
        if self.selected:
            self.c1 += 1
            self.lines[self.idx].lift()
            self.lines[self.idx].place(x= self.x, y= self.y, anchor = 'center')
            if self.c1 > 10:
                self.c1 = 0
                self.skip = 1
                idx = self.place()
                self.skip = 0
                self.idx = idx
                self.selected = 1
            self.win.after(30, self.drag)

    def place(self, *e):
        self.selected = 0
        idx = min(int(self.x/self.w)*self.rows + int(self.y/self.h),
            len(self.lines)-1)
        line = self.lines.pop(self.idx)
        self.lines.insert(idx, line)
        pos = self.positions.pop(self.idx)
        self.positions.insert(idx, pos)
        for idx2 in range(min(self.idx, idx), len(self.lines)):
            if self.skip:
                if idx2 == idx:
                    continue
            col = 2*int(idx2/self.rows)
            row = idx2 % self.rows
            self.lines[idx2].grid(column = col+1, row = row)
        self.win.update()
        return idx

class GUI():
    def __init__(self):
        self.title = 'Super Presenter v.0.2'
        self.dir = path.dirname(__file__)
        self.noOfSteps = 0

        self.projectors = []
        self.projectorID = -1
        # self.monText = ''
        # self.projStyle = ''

        # self.var1text = ''
        # self.var2text = ''
        # self.var3text = ''
        self.sources = []
        self.sourceID = -1
        self.sourceList = []
        self.onlineSources = []
        self.projPlacements = []
        self.animation = 0
        self.t = time.time()

        self.runState = False

        self.win = tk.Tk()
        self.initWins()
        try:
            self.setStyle()
        except:
            tkmsg.showerror('Error loading styles',
                'Unknown error occured while loading GUI styles\n'+\
                    'Check "gui_styles.json" file.')
        self.placeWidgets()

        self.getMonitors()
        self.getProjectorStyles()
        
        self.newProjector()

        self.assign()
        
        self.draft_open = False
        
    def setStyle(self, styleName=''):
        with open(self.dir + '\\gui_style.json', 'r', encoding='utf-8') as f:
            dta = json.loads(f.read())
        if styleName == '':
            style = dta[dta['def_style']]
        else:
            style = dta[styleName]

        fonts = []
        for font in style['fonts']:
            fonts.append(tkFont.Font(name=font['name'], family=font['family'],
                    size=font['size'], weight=font['weight']))

        s = ttk.Style()
        s.theme_use('clam')
        for tStyle in style['Tstyles']:
            s.configure(tStyle['name'],
                foreground=tStyle['foreground'],
                fieldbackground=tStyle['fieldbackground'],
                background=tStyle['background'])

        self.sorterStyle = style['sorter']

        self.onStyle = style['runON']
        self.offStyle = style['runOFF']

        self.win.config(style['win'])
        
        self.leftFrame.config(style['mainFrame'])
        self.rightFrame.config(style['mainFrame'])

        self.stepsFrame.config(style['mainFrame'])
        self.navFrame.config(style['mainFrame'])

        self.stepsLang.config(style['stepLang'])
        self.stepsList.config(style['stepList'])

        self.nextBtn.config(style['mainButton'])
        self.prevBtn.config(style['mainButton'])
        self.nextFileBtn.config(style['mainButton'])
        self.prevFileBtn.config(style['mainButton'])
        self.stepsLabel.config(style['stepsLabel'])

        self.projNtbk.config(style['secondaryFrame'])
        self.projNav.config(style['secondaryFrame'])
        self.projSet.config(style['secondaryFrame'])
        self.projRun.config(style['secondaryFrame'])

        self.nextProj.config(style['projButton'])
        self.prevProj.config(style['projButton'])
        self.projsLabel.config(style['projsLabel'])
        self.addProj.config(style['projButton'])
        self.delProj.config(style['projButton'])
        self.loadProjs.config(style['projButton'], width=5)
        self.saveProjs.config(style['projButton'], width=5)
        
        self.openProjs.config(style['projButton'], width=15)
        self.openProjs.config(style["runOFF"])
        self.fullscreenCheck.config(style['checkButton'])
        self.collectionCheck.config(style['checkButton'])
        
        self.stepsHead.config(style['mainFrame'])
        self.stepsLangLabel.config(style['mainLabel'])
        self.slideLabel.config(style['mainLabel'])

        self.chooseProjLabel.config(style['secondaryLabel'])
        self.chooseStyleLabel.config(style['secondaryLabel'])
        self.chooseProj.config(style['stepLang'])
        self.chooseStyle.config(style['stepLang'])

        ##### right halve
        self.sourceFrame.config(style['mainFrame'])

        self.sourceNav.config(style['mainFrame'])
        self.sourceEdit.config(style['mainFrame'])
        self.sourceChanges.config(style['mainFrame'])
        self.repetitions.config(style['secondaryFrame'])
        self.variants.config(style['secondaryFrame'])
        
        self.addSlokaBtn.config(style['projButton'], width=6)
        self.addRefrenBtn.config(style['projButton'], width=6)
        self.addBridgeBtn.config(style['projButton'], width=6)
        self.addLangBtn.config(style['projButton'], width=12)

        ### source
        ## navigation
        self.sourceNum.config(style['stepsLabel'])
        self.prevSource.config(style['projButton'])
        self.nextSource.config(style['projButton'])
        self.openSource.config(style['projButton'])
        self.closeSource.config(style['projButton'])
        self.newSource.config(style['projButton'])  
        self.changeOrder.config(style['projButton'], width=8)
        self.openPresentation.config(style['projButton'], width=12)
        self.sourceLab.config(style['sourcesLabel'])
        try:
            lab_bg   = self.sourceLab.cget("background")
            lab_fg   = self.sourceLab.cget("foreground")
            lab_font = self.sourceLab.cget("font")
        except Exception:
            # fallback, kdyby styl nevrátil hodnoty
            lab_bg   = style['sourcesLabel'].get('background', '#444444')
            lab_fg   = style['sourcesLabel'].get('foreground', 'white')
            lab_font = style['sourcesLabel'].get('font', ('Courier New', 14, 'bold'))

        self.sourceTitleEntry.configure(
            bg=lab_bg,
            fg=lab_fg,
            insertbackground=lab_fg,   # barva kurzoru
            font=lab_font,
            relief='flat', bd=0,       # bez rámečku
            highlightthickness=0,
            justify='center'           # stejná „vibe“ jako nadpis
        )
        # volitelně potlač focus-ring, hlavně na Windows:
        self.sourceTitleEntry.configure(highlightbackground=lab_bg, highlightcolor=lab_bg)
        # repetitions
        self.repLab.config(style['secondaryLabel'])
        self.repIn.config(style['entryWin'])
        self.repExp.config(style['projButton'], width=15)
        self.repImp.config(style['projButton'], width=15)
        # variants
        self.var1Lab.config(style['secondaryLabel'])
        self.var2Lab.config(style['secondaryLabel'])
        self.var3Lab.config(style['secondaryLabel'])
        self.var1Combo.config(style['stepLang'])
        self.var2Combo.config(style['stepLang'])
        self.var3Combo.config(style['stepLang'])

    def initWins(self):
        self.win.title(self.title)
        self.win.resizable(0,0)
        self.win.geometry('+20+20')
        from song_editor import SongEditor, add_title_placeholder

        ##### halve window
        self.leftFrame = tk.Frame(self.win)
        self.rightFrame = tk.Frame(self.win)
        self.fullscreenState = tk.BooleanVar()

        ### left halve
        ## navigation
        # list
        self.stepsFrame = tk.Frame(self.leftFrame)

        self.stepsHead = tk.Frame(self.stepsFrame)
        self.stepsLang = ttk.Combobox(self.stepsHead, width=20)
        self.stepsLang.state(['readonly'])
        self.stepsLangLabel = tk.Label(self.stepsHead,
                text='Preview language:')
        self.slideLabel = tk.Label(self.stepsHead, text = '0 / 0')

        self.stepsList = tk.Listbox(
            self.stepsFrame,
            activestyle='dotbox',
            selectmode='extended'   
        )
        self.stepsScroll = tk.Scrollbar(self.stepsFrame,
                orient='vertical', command=self.stepsList.yview)
        self.stepsList['yscrollcommand'] = self.stepsScroll.set
        # buttons
        self.navFrame = tk.Frame(self.leftFrame)
        self.nextBtn = tk.Button(self.navFrame, text='>')
        self.prevBtn = tk.Button(self.navFrame, text='<')
        self.nextFileBtn = tk.Button(self.navFrame, text='>>')
        self.prevFileBtn = tk.Button(self.navFrame, text='<<')
        self.stepsLabel = tk.Label(self.navFrame, text='0 / 0')

        ## projection window setup
        self.projNtbk = tk.Frame(self.leftFrame)
        self.projNav = tk.Frame(self.projNtbk)
        self.projSet = tk.Frame(self.projNtbk)
        self.projRun = tk.Frame(self.projNtbk)
        # navigation buttons
        self.nextProj = tk.Button(self.projNav, text='>')
        self.prevProj = tk.Button(self.projNav, text='<')
        self.projsLabel = tk.Label(self.projNav, text='0 / 0')
        self.addProj = tk.Button(self.projNav, text='+')
        self.delProj = tk.Button(self.projNav, text='del')
        self.loadProjs = tk.Button(self.projNav, text='load')
        self.saveProjs = tk.Button(self.projNav, text='save')
        # projection settings
        self.chooseProjLabel = tk.Label(self.projSet, text='Display')
        self.chooseStyleLabel = tk.Label(self.projSet, text='Style')
        self.chooseProj = ttk.Combobox(self.projSet, width=20)
        self.chooseStyle = ttk.Combobox(self.projSet, width=20)
        self.chooseProj.state(['readonly'])
        self.chooseStyle.state(['readonly'])
        # projection run
        self.openProjs = tk.Button(self.projRun, text='▶')
        self.fullscreenCheck = tk.Checkbutton(self.projRun, text='fullscreen',
            variable=self.fullscreenState, command=self.changeFullscreen)

        self.collectionState = tk.BooleanVar(value=False)
        self.collectionCheck = tk.Checkbutton(
            self.projRun,
            text='Sbírka',
            variable=self.collectionState,
            command=self.changeCollection
        )
        
        ##### right halve
        self.sourceFrame = tk.Frame(self.rightFrame)

        self.sourceNav = tk.Frame(self.sourceFrame)
        self.sourceEdit = tk.Frame(self.sourceFrame)
        self.sourceChanges = tk.Frame(self.sourceFrame)
        self.repetitions = tk.Frame(self.rightFrame)
        self.variants = tk.Frame(self.rightFrame)

        ### source
        ## navigation
        self.sourceNum = tk.Label(self.sourceNav, text='0 / 0')
        self.prevSource = tk.Button(self.sourceNav, text='<')
        self.nextSource = tk.Button(self.sourceNav, text='>')
        self.closeSource = tk.Button(self.sourceNav, text='✕')
        self.openSource = tk.Button(self.sourceNav, text='+')
        self.newSource = tk.Button(self.sourceNav, text='new')
        self.changeOrder = tk.Button(self.sourceNav, text='order')
        self.openPresentation = tk.Button(self.sourceNav, text='prezentace')
        self.sourceLab = tk.Label(self.sourceNav, text='-----')
        self.song_title = tk.StringVar(master=self.win)
        self.sourceTitleEntry = tk.Entry(self.sourceNav, width=40, textvariable=self.song_title)
        add_title_placeholder(self.sourceTitleEntry, self.song_title)
        
        self.song_editor_frame = tk.Frame(self.sourceEdit)
        self.song_editor_frame.grid(column=0, row=0, sticky='nsew')
        self.song_editor_widget = SongEditor(
            self.song_editor_frame, embedded=True, title_variable=self.song_title,
            on_saved=self.on_editor_saved)
        # edit
        from song_editor import SongEditor
        # source changes
        self.addSlokaBtn = tk.Button(self.sourceChanges, text="Sloka", command=lambda: self.song_editor_widget.add_section_to_all_languages('v'))
        self.addRefrenBtn = tk.Button(self.sourceChanges, text="Refrén", command=lambda: self.song_editor_widget.add_section_to_all_languages('r'))
        self.addBridgeBtn = tk.Button(self.sourceChanges, text="Bridge", command=lambda: self.song_editor_widget.add_section_to_all_languages('b'))
        self.addLangBtn = tk.Button(self.sourceChanges, text="Přidat jazyk", command=self.song_editor_widget.open_language_dialog)
        # repetitions
        self.repLab = tk.Label(self.repetitions, text='Construct')
        self.repImp = tk.Button(self.repetitions, text='import')
        self.repExp = tk.Button(self.repetitions, text='export')
        self.construct_variable = tk.StringVar(master=self.win)
        self.repIn = tk.Entry(self.repetitions, textvariable=self.construct_variable)
        self._syncing_song = False
        self.construct_variable.trace_add("write", self._construct_changed)
        self.song_editor_widget.on_changed = self._editor_changed
        # variants
        self.var1Lab = tk.Label(self.variants, text='Variant 1')    
        self.var2Lab = tk.Label(self.variants, text='Variant 2')
        self.var3Lab = tk.Label(self.variants, text='Variant 3')
        self.var1Combo = ttk.Combobox(self.variants)
        self.var2Combo = ttk.Combobox(self.variants)
        self.var3Combo = ttk.Combobox(self.variants)
        self.var1Combo.state(['readonly'])
        self.var2Combo.state(['readonly'])
        self.var3Combo.state(['readonly'])
    

    def placeWidgets(self):
        ##### halve window
        self.leftFrame.grid(column=0, row=0, padx=10, sticky=('n','s'))
        self.rightFrame.grid(column=1, row=0, padx=10, sticky=('n','s'))
        self.rightFrame.grid_rowconfigure(0, weight=1)
        self.rightFrame.grid_rowconfigure(1, weight=0)
        self.rightFrame.grid_rowconfigure(2, weight=0)
        self.rightFrame.grid_columnconfigure(0, weight=1)
        
        ### left halve
        ## navigation
        # list
        self.stepsFrame.grid(column=0,row=0)

        self.stepsHead.grid(column=0,row=0, sticky=('w','e'))
        self.stepsLang.grid(column=1, row=0, sticky='w')
        self.stepsLangLabel.grid(column=0,row=0, sticky=('w','e'))
        self.slideLabel.grid(column=2, row=0, padx=(50,5))

        self.stepsList.grid(column=0,row=1,sticky=('n','s','e','w'))
        self.stepsScroll.grid(column=1,row=1, sticky=('n','s'))
        # buttons
        self.navFrame.grid(column=0, row=1, pady=5)
        self.nextBtn.grid(row=0, column=3, sticky=('w','e'))
        self.prevBtn.grid(row=0, column=1, sticky=('w','e'))
        self.nextFileBtn.grid(row=0, column=4, sticky=('w','e'))
        self.prevFileBtn.grid(row=0, column=0, sticky=('w','e'))
        self.stepsLabel.grid(column=2, row= 0, sticky=('e','w'))

        ## projection window setup
        self.projNtbk.grid(column=0, row=2, pady=7)
        self.projNav.grid(column=0, row=0, sticky=('w','e'))
        self.projSet.grid(column=0, row=1, sticky=('w','e'))
        self.projRun.grid(column=0, row=2)
        # navigation buttons
        self.nextProj.grid(row=0, column=2, sticky=('w','e'), padx=2)
        self.prevProj.grid(row=0, column=0, sticky=('e'), padx=2)
        self.projsLabel.grid(column=1, row= 0, sticky=('e','w'))
        self.addProj.grid(row=0, column=3, sticky=('w','e'), padx=2)
        self.delProj.grid(row=0, column=4, sticky=('w','e'), padx=2)
        self.loadProjs.grid(row=0, column=5, sticky=('w','e'), padx=7)
        self.saveProjs.grid(row=0, column=6, sticky=('w','e'), padx=(2,7))
        # projection settings
        self.chooseProjLabel.grid(row=0, column=0, sticky='e',
             pady=5, padx=10)
        self.chooseStyleLabel.grid(row=1, column=0, sticky='e',
             pady=5, padx=10)
        self.chooseProj.grid(row=0, column=1, sticky='w',
             pady=5, padx=10)
        self.chooseStyle.grid(row=1, column=1, sticky='w',
             pady=5, padx=10)
        # projection run
        self.openProjs.grid(row=0, column=0, padx=7)
        self.fullscreenCheck.grid(column=1, row=0,padx= 7)
        self.collectionCheck.grid(column=1, row=1, padx=7)
        
        ##### right halve
        self.sourceFrame.grid(column=0, row=0, sticky=('nsew'))

        self.sourceFrame.grid_rowconfigure(0, weight=0)
        self.sourceFrame.grid_rowconfigure(1, weight=1)
        self.sourceFrame.grid_rowconfigure(2, weight=0)
        self.sourceFrame.grid_columnconfigure(0, weight=1)

        self.sourceNav.grid(column=0, row=0)
        self.sourceEdit.grid(column=0, row=1, sticky='nsew')
        
        self.sourceEdit.grid_rowconfigure(0, weight=1)
        self.sourceEdit.grid_columnconfigure(0, weight=1)

        self.sourceChanges.grid(column=0, row=2)
        # self.repetitions.grid(column=0, row=1, sticky='ew', pady=(8, 0))
        self.variants.grid(column=0, row=2, sticky='ew', pady=(0, 8))

        self.explainLabel = tk.Label(self.rightFrame, text="v = Sloka, r = Refrén, b = Bridge | (v) = 1 Opakování | (v)*x = x Opakování | v.x = Pouze x řádek")
        self.explainLabel.grid(column=0, row=3, padx=5, pady=5, sticky='w')
        ### source
        ## navigation
        self.sourceNum.grid(column=1, row=0, padx=3)
        self.prevSource.grid(column=0, row=0, padx=3)
        self.nextSource.grid(column=2, row=0, padx=3)
        self.closeSource.grid(column=3, row=0, padx=3)
        self.openSource.grid(column=4, row=0, padx=3)
        self.newSource.grid(column=5,row=0, padx=3)
        self.changeOrder.grid(column=6, row=0, sticky='e', padx=3)
        self.openPresentation.grid(column=7, row=0, sticky='e', padx=3)
        self.sourceTitleEntry.grid(column=0, row=2, columnspan=8, padx=3, pady=5, sticky='we')
        # variants
        self.var1Lab.grid(column=0, row=0, padx=10, pady= 3)
        self.var2Lab.grid(column=0, row=1, padx=10, pady= 3)
        self.var3Lab.grid(column=0, row=2, padx=10, pady= 3)
        self.var1Combo.grid(column=1, row=0, padx=4, pady= 3)
        self.var2Combo.grid(column=1, row=1, padx=4, pady= 3)
        self.var3Combo.grid(column=1, row=2, padx=4, pady= 3)
        
        self.addSlokaBtn.grid(column=0, row=0, padx=4)
        self.addRefrenBtn.grid(column=1, row=0, padx=4)
        self.addBridgeBtn.grid(column=2, row=0, padx=4)
        self.addLangBtn.grid(column=3, row=0, padx=4)

    def on_closing(self):
        if not self._prepare_song_transition():
            return
        # Zavřít editor prezentací, pokud běží
        if hasattr(self, "presentation_editor_win"):
            if self.presentation_editor_win.poll() is None:
                self.presentation_editor_win.terminate()

        self.win.destroy()

    def assign(self):
        # projectors options
        self.openProjs.configure(command=self.runButtFun)
        self.addProj.configure(command=self.newProjector)
        self.delProj.configure(command=self.delProjector)
        self.nextProj.configure(command=self.nextProjector)
        self.prevProj.configure(command=self.prevProjector)
        #sources options
        self.openSource.configure(command=self.addSource)
        self.prevSource.configure(command=self.prevSourceFun)
        self.nextSource.configure(command=self.nextSourceFun)
        self.closeSource.configure(command=self.closeSourceFun)
        self.newSource.configure(command=self.newSongFun)
        self.changeOrder.configure(command=self.sortSources)
        self.openPresentation.configure(command=self.openPresentationEditor)


        self.saveProjs.configure(state='disabled')
        self.loadProjs.configure(state='disabled')
        # self.changeOrder.configure(state='disabled')
        self.repExp.configure(state='disabled')
        self.repImp.configure(state='disabled')
      
        self.stepsList.bind('<<ListboxSelect>>',self.stepSelect)
        self.stepsList.bind('<Button-1>', self._stationary_click)
        self.chooseProj.bind('<<ComboboxSelected>>', self.changeProjector)
        self.chooseStyle.bind('<<ComboboxSelected>>', self.changeStyle)
        self.stepsLang.bind('<<ComboboxSelected>>', self.stepsLangUpdate)

        self.var1Combo.bind('<<ComboboxSelected>>', self.setVariant1)
        self.var2Combo.bind('<<ComboboxSelected>>', self.setVariant2)
        self.var3Combo.bind('<<ComboboxSelected>>', self.setVariant3)

        self.nextFileBtn.configure(command=self.nextSlide)
        self.prevFileBtn.configure(command=self.prevSlide)
        self.nextBtn.configure(command=self.nextStep)
        self.prevBtn.configure(command=self.prevStep)
        self.win.bind('<Button-1>', lambda e: e.widget.focus_set())
        self.win.bind('<Shift-Right>', self.nextSlideKey)
        self.win.bind('<Shift-Left>', self.prevSlideKey)
        self.win.bind('<Right>', self.nextStepKey)
        self.win.bind('<Left>', self.prevStepKey)
        self.win.bind('<F5>', self.runButtFun)
        self.win.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _is_on_draft(self):
        return self.draft_open and self.sourceID == len(self.sourceList)

    def _prepare_song_transition(self):
        return self.song_editor_widget.confirm_transition()

    def _update_new_button_state(self):
        self.newSource.configure(state='normal')

    def _construct_changed(self, *_):
        if not self._syncing_song:
            self.song_editor_widget.set_selected_repetition_text(self.construct_variable.get())

    def _editor_changed(self, song):
        self._syncing_song = True
        try:
            self.construct_variable.set(song.guide)
            languages = list(song.variant_texts)
            for index, combo in enumerate((self.var1Combo, self.var2Combo, self.var3Combo)):
                choices = languages if index == 0 else ['-----'] + languages
                current = combo.get()
                combo['values'] = choices
                if current not in choices:
                    combo.set(choices[0] if choices else '')
        finally:
            self._syncing_song = False

    def total_sources(self):
        return len(self.sourceList) + (1 if self.draft_open else 0)

    def viewDraft(self, *e):
        self.sourceNum.configure(text=f'{self.sourceID+1} / {self.total_sources()}')
        self.sourceLab.config(text='(neuložená píseň)')
        self._editor_changed(self.song_editor_widget.snapshot())

    def on_editor_restored(self, song, clean_song, path):
        """Show recovered work while keeping presentation data at its clean baseline."""
        if path:
            source = WidgetSource(path, clean_song)
            languages = source.importVariants()
            source.variants = [languages[0] if languages else '-----', '-----', '-----']
            self.sources.append(source)
            self.sourceList.append(len(self.sources) - 1)
            self.sourceID = len(self.sourceList) - 1
            self.draft_open = False
            self.viewSource(reload_editor=False)
            self._editor_changed(song)
        else:
            self.draft_open = True
            self.sourceID = len(self.sourceList)
            self.viewDraft()
        self._update_new_button_state()

    def on_editor_saved(self, song, path, renamed_from=None):
        """Publish a fresh saved snapshot; running presentations retain their snapshot."""
        same_path = lambda a, b: os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
        selected_languages = [combo.get() for combo in (self.var1Combo, self.var2Combo, self.var3Combo)]
        current = self.sourceList[self.sourceID] if 0 <= self.sourceID < len(self.sourceList) else None
        idx = None
        for i, source in enumerate(self.sources):
            if same_path(source.path, path) or (renamed_from and same_path(source.path, renamed_from)):
                updated = WidgetSource(path, song)
                languages = updated.importVariants()
                choices = selected_languages if i == current else source.variants
                updated.variants = [value if value in languages else (languages[0] if j == 0 and languages else '-----') for j, value in enumerate(choices)]
                self.sources[i] = updated
                if idx is None:
                    idx = i
        if idx is None:
            updated = WidgetSource(path, song)
            languages = updated.importVariants()
            updated.variants = [value if value in languages else (languages[0] if j == 0 and languages else '-----') for j, value in enumerate(selected_languages)]
            self.sources.append(updated)
            idx = len(self.sources) - 1
        if idx not in self.sourceList:
            self.sourceList.append(idx)
        self.draft_open = False
        self.sourceID = self.sourceList.index(idx)
        self._update_new_button_state()
        self.viewSource(reload_editor=False)

    def run(self):
        tk.mainloop()

    def openSongEditor(self):
        import subprocess
        import sys
        if hasattr(self, "song_editor_win") and self.song_editor_win.poll() is None:
            return  # Editor už běží
        path = os.path.join(self.dir, 'song_editor.py')
        self.song_editor_win = subprocess.Popen([sys.executable, path])

    def openPresentationEditor(self):
        import subprocess
        import sys
        if hasattr(self, "presentation_editor_win") and self.presentation_editor_win.poll() is None:
            return  # Prezentace už běží
        path = os.path.join(self.dir, 'presentation_presenter.py')
        self.presentation_editor_win = subprocess.Popen([sys.executable, path])

    def getMonitors(self):
        self.monitors = get_monitors()
        self.monitors.sort(key=lambda m: m.x)

        id = 0
        monitorList = []
        for mon in self.monitors:
            id += 1
            mon.name = f'disp{id} ({mon.x},{mon.y})'
            monitorList.append(mon.name)

        self.chooseProj['values'] = monitorList

        if monitorList:
            self.chooseProj.set(monitorList[0])

    def getProjectorStyles(self):
        with open(self.dir + '\\projectors_styles.json', 'r', encoding='utf-8') as f:
            dta = json.loads(f.read())
        self.animationParams = dta['animation']
        dta = dta['styles']
        self.projStyles = []
        names = []
        for style in dta:
            self.projStyles.append(style)
            names.append(style['name'])
        self.chooseStyle['values'] = names

    def _testList(self):
        for i in range(1, 101):
            self.stepsList.insert('end','Line %d of 100' % i)
        self.stepsList.selection_set(0)

    def _testProj(self):
        self.newProjector()
        self.loadSource(
            'C:\\Users\\gurl3\\Hobby\\python_tests\\'+\
                'super_presenter\\songs\\vsade_tam_kde_su.xml'
        )
        vars = self.sources[-1].importVariants()
        self.var2Combo.set(vars[1])
        self.setVariant2()
        self.repIn.delete(0, 'end')
        self.repIn.insert(0, '(v1 v2.1:3 (v2.4)*3)v1')
        self.saveRepetitions()
        self.loadSource(
            'C:\\Users\\gurl3\\Hobby\\python_tests\\'+\
                'super_presenter\\songs\\vsade_tam_kde_su_2.xml'
        )
        vars = self.sources[-1].importVariants()
        self.var2Combo.set(vars[0])
        self.setVariant2()
        self.repIn.delete(0, 'end')
        self.repIn.insert(0, '(v1 v2(v2))')
        self.projectors[-1].style = 1
        self.runButtFun()
        
        # self.stepGoTo(0)

    # projectors options
    def newProjector(self,*e):
        l = len(self.projectors)
        if l < 5:
            new_proj = ProjWindow(self)

            if l > 0 and hasattr(self, 'monitors'):
                new_proj.monitor = len(self.monitors) - 1
            else:
                new_proj.monitor = 0

            self.projectors.append(new_proj)
            self.projectorID = l
            self.openProjector()

    def openProjector(self):
        proj = self.projectors[self.projectorID]
        self.projsLabel.configure(
            text= f'{self.projectorID+1} / {len(self.projectors)}')
        self.monText = self.chooseProj.current(proj.monitor)
        self.chooseProj.current(proj.monitor)
        self.projStyle = self.chooseStyle.current(proj.style)
        if proj.fullscreen:
            self.fullscreenCheck.select()
        else:
            self.fullscreenCheck.deselect()
        if getattr(proj, 'collection', False):
            self.collectionCheck.select()
        else:
            self.collectionCheck.deselect()    

    def changeStyle(self, *e):
        if self.projectorID >=0:
            self.projectors[self.projectorID].style = \
                self.chooseStyle.current()

    def changeProjector(self, *e):
        if self.projectorID >=0:
            self.projectors[self.projectorID].monitor = \
                self.chooseProj.current()

    def changeFullscreen(self, *e):
        if self.projectorID >=0:
            self.projectors[self.projectorID].fullscreen = \
                self.fullscreenState.get()

    def delProjector(self, *e):
        l = len(self.projectors)
        if l > 1:
            if self.projectorID >= l-1:
                self.projectorID = l-2
            self.projectors.pop(self.projectorID)
            self.openProjector()

    def nextProjector(self, *e):
        if self.projectorID < len(self.projectors)-1:
            self.projectorID += 1
            self.openProjector()

    def prevProjector(self, *e):
        if self.projectorID > 0:
            self.projectorID -= 1
            self.openProjector()

    # source options
    def addSource(self, *e):
        paths = filedialog.askopenfilenames(title='Otevřít píseň', initialdir=os.path.join(self.dir, "songs"),
            filetypes=(('Textové soubory', ('*.xml', '*.txt')), ('Všechny soubory', ('*.*'))))
        for path in paths:
            if not self.loadSource(path):
                break

    def loadSource(self, path):
        src = WidgetSource(path)
        if src.err:
            tkmsg.showerror('Chyba načítání', f'Nelze načíst {path}:\n{src.load_warning or "Soubor není dostupný."}')
            return False
        try:
            validate_editor_fields(src.song)
        except ValueError as exc:
            tkmsg.showerror('Chyba načítání', str(exc))
            return False
        ok, variants, _ = self.validateSource(src)
        if not ok or not self._prepare_song_transition():
            return False
        if src.load_warning:
            tkmsg.showwarning('Starší formát písně', f'{path}\nSoubor byl načten tolerantním importem. Uložení vytvoří platné XML.\n{src.load_warning}')
        src.variants = [variants[0], '-----', '-----']
        self.draft_open = False
        self.sources.append(src)
        self.sourceList.append(len(self.sources) - 1)
        self.sourceID = len(self.sourceList) - 1
        self.viewSource()
        return True

    def viewSource(self, *e, reload_editor=True):
        if self._is_on_draft():
            self.viewDraft()
            return
        if 0 <= self.sourceID < len(self.sourceList):
            src = self.sources[self.sourceList[self.sourceID]]
            if reload_editor and not self.song_editor_widget.load_song(src.song, src.path):
                return False
            self.sourceNum.configure(text=f'{self.sourceID+1} / {self.total_sources()}')
            self.sourceLab.config(text=src.fileName)
            languages = src.importVariants()
            for i, combo in enumerate((self.var1Combo, self.var2Combo, self.var3Combo)):
                combo['values'] = languages if i == 0 else ['-----'] + languages
                combo.set(src.variants[i])
            return True
        return False

    def validateSource(self, src:WidgetSource):
        err, vars, secs = src.validate()
        if err > 0:
            txt = 'Error ocured while loading source.'
            if err & 8 == 8:
                txt += '\nUnable to read slide name.'
            if err & 4 == 4:
                txt += '\nUnable to read repetitions.'
            if err & 2 == 2:
                txt += '\nUnable to read variants.'
            if err & 1 == 1:
                txt += '\nUnable to read sections.'
            if err & 16 == 16:
                txt += '\nUnable to read lines'
            tkmsg.showerror('Error while loading source', txt)
            return 0, [], []
        else:
            if len(vars) == 0:
                tkmsg.showerror('Error while loading source',
                    'Thera are no variants defined in the file')
                return 0, [], []
            if len(secs) == 0:
                tkmsg.showerror('Error while loading source',
                    'Thera are no sections defined in the file')
                return 0, [], []
            return 1, vars, secs

    def saveRepetitions(self, *e):
        self.song_editor_widget.set_selected_repetition_text(self.repIn.get())

    def prevSourceFun(self, *e):
        if self.sourceID > 0:
            target = self.sourceList[self.sourceID - 1]
            if not self._prepare_song_transition():
                return
            self.draft_open = False
            self.sourceID = self.sourceList.index(target)
            self.viewSource()

    def nextSourceFun(self, *e):
        if self.sourceID + 1 < len(self.sourceList):
            target = self.sourceList[self.sourceID + 1]
            if not self._prepare_song_transition():
                return
            self.draft_open = False
            self.sourceID = self.sourceList.index(target)
            self.viewSource()

    def _set_variant(self, index, combo):
        if 0 <= self.sourceID < len(self.sourceList):
            source = self.sources[self.sourceList[self.sourceID]]
            if combo.get() in source.song.variant_texts or (index > 0 and combo.get() == '-----'):
                source.variants[index] = combo.get()

    def setVariant1(self, *e):
        self._set_variant(0, self.var1Combo)

    def setVariant2(self, *e):
        self._set_variant(1, self.var2Combo)

    def setVariant3(self, *e):
        self._set_variant(2, self.var3Combo)

    def closeSourceFun(self, *e):
        if not self._prepare_song_transition():
            return
        if self._is_on_draft():
            self.draft_open = False
        elif 0 <= self.sourceID < len(self.sourceList):
            self.sourceList.pop(self.sourceID)
        self.sourceID = min(self.sourceID, len(self.sourceList) - 1)
        if self.sourceID >= 0:
            self.viewSource()
        else:
            self.viewSource0()

    def viewSource0(self, *e):
        if not self.song_editor_widget.new_song():
            return False
        self.sourceNum.configure(text='0 / 0')
        self.sourceLab.config(text='-----')
        self.draft_open = False
        self._update_new_button_state()
        return True

    def sortSources(self, *e):
        if not self._prepare_song_transition():
            return
        if len(self.sourceList) > 0:
            self.sorter = SortingWin(self.win, self.sorterStyle, 
                [self.sources[x].importSlideName() for x in self.sourceList], self.sourceList)
            self.sorter.win.protocol("WM_DELETE_WINDOW", self.closeSorter)

    def closeSorter(self, *e):
        a = tkmsg.askyesnocancel('Save', 'Save current order')
        if a == True:
            if not self._prepare_song_transition():
                return
            current = self.sourceList[self.sourceID] if 0 <= self.sourceID < len(self.sourceList) else None
            self.sourceList = self.sorter.positions
            if current in self.sourceList:
                self.sourceID = self.sourceList.index(current)
            self.sorter.win.destroy()
            del self.sorter
            self.viewSource()
        elif a == False:
            self.sorter.win.destroy()
            del self.sorter
        else:
            return

    def runButtFun(self, *e):
        if not self.runState and not self._prepare_song_transition():
            return
        # Tlačítko dočasně vypnout – ale VŽDY ho na konci znovu povolit
        self.openProjs.configure(state='disabled')
        try:
            self.runState = not self.runState

            if self.runState:
                # --- START PREZENTACE ---
                self.openProjs.config(self.onStyle)
                self.win.bind('<Escape>', self.runButtFun)

                self.addProj.configure(state='disabled')
                self.delProj.configure(state='disabled')
                self.fullscreenCheck.configure(state='disabled')
                self.chooseProj.configure(state='disabled')
                self.chooseStyle.configure(state='disabled')

                # 1. Načti typy zdrojů podle stylů
                try:
                    types = self.getSourceTypes()
                except Exception:
                    tkmsg.showerror('Error in projector styles',
                                    'Error occurred while loading styles for projectors\n'
                                    'Check "projector_styles.json"')
                    self.runState = False
                    self._cleanup_after_stop()
                    return

                # Explicit modes; legacy navigation remains isolated below.
                self.pair2_active = False
                self.stationary_active = any(
                    style_mode(self.projStyles[p.style]) != 'legacy_scroll'
                    for p in self.projectors)
                self.stationary_navigation = None
                stationary_plans = []

                if len(self.sourceList) > 0:
                    self.saveRepetitions()

                self.prevVars = []
                self.onlineSources = [deepcopy(self.sources[idx]) for idx in self.sourceList]

                # 3. PŘÍPRAVA ZDROJŮ (PÍSNÍ)
                construct_error = None
                for src in self.onlineSources:
                    # Výběr správného konstruktu (opakování)
                    guide = (src.repetitions or '').strip()

                    # Pokud není Construct definován, zkusíme najít hlavní (main) v XML
                    if not guide:
                        reps = src.importRepetitions()
                        def pick_main(reps_dict: dict) -> str:
                            for nm, d in reps_dict.items():
                                v = d.get("main", "")
                                if isinstance(v, (int, float)) and v > 0:
                                    return nm
                                if isinstance(v, str) and v.strip().lower() in ("1", "true", "yes"):
                                    return nm
                            if "default" in reps_dict:
                                return "default"
                            return next(iter(reps_dict), "")
                        
                        sel = pick_main(reps)
                        guide = (reps.get(sel, {}).get("guide", "") or "").strip()
                    
                    src.repetitions = guide
                    try:
                        src.readInstructions()
                    except ConstructError as exc:
                        construct_error = exc
                        self._display_construct_error(src.importSlideName(), exc)
                        break

                    # Sestavení řádků (Zde se aktivuje logika short2 pro stream)
                    try:
                        vars_ = src.constructLines(types)
                        if self.stationary_active:
                            plan, src.cue_legacy_steps = build_plan(
                                src.song,
                                [v for v in src.variants if v != '-----'], guide)
                            stationary_plans.append(plan)
                    except Exception as ex:
                        tkmsg.showerror('Error in projector styles',
                            'Error occurred while constructing source text\n'
                            'Check "projectors_styles.json"\n' + str(ex))
                        self.runState = False
                        self._cleanup_after_stop()
                        return

                    # Uložíme výsledné texty pro UI seznam vlevo
                    self.prevVars.append([0] + vars_)

                # Pokud došlo k chybě při přípravě kterékoli písně, zastavíme
                if construct_error is not None:
                    self.runState = False
                    self._cleanup_after_stop()
                    return

                if self.stationary_active:
                    self.stationary_navigation = CueNavigation(stationary_plans)

                # 4. OTEVŘENÍ OKEN PROJEKTORŮ
                self.runningSlide = 0
                for proj in self.projectors:
                    try:
                        proj.project()
                        proj.set_collection_visible(getattr(proj, "collection", False))
                    except Exception as e:
                        tkmsg.showerror('Error in projector styles',
                            f'Error occurred while constructing "{self.projStyles[proj.style]["name"]}"\n'
                            'Check "projector_styles.json"\n\n' + str(e))
                        self.runState = False
                        self._cleanup_after_stop()
                        return

                self.previewSlide()

            else:
                # --- STOP PREZENTACE ---
                self._cleanup_after_stop()

        finally:
            # VŽDY povolit tlačítko zpět, i když kód spadne
            self.openProjs.configure(state='normal')

    def _display_construct_error(self, slide_name, err):
        """Pomocná metoda pro zobrazení chyb v konstruktu"""
        tkmsg.showerror('Error constructing text',
                        f'Error in source "{slide_name}"\n'
                        'Check construct input.\n' + str(err))

    def _cleanup_after_stop(self):
        self.openProjs.config(self.offStyle)
        self.win.bind('<Escape>', doNothing)

        self.addProj.configure(state='normal')
        self.delProj.configure(state='normal')
        self.fullscreenCheck.configure(state='normal')
        self.chooseProj.configure(state='readonly')
        self.chooseStyle.configure(state='readonly')

        self.stepsList.delete(0, 'end')
        self.stepsLabel.configure(text='0 / 0')
        self.slideLabel.configure(text='0 / 0')

        # zavři okna projektorů
        for proj in self.projectors:
            proj.stopProjection()

        # reset běhového stavu
        self.onlineSources = []
        self.stationary_navigation = None
        self.stationary_active = False
        self.animation = 0

    def onProjectorClose(self, *e):
        if tkmsg.askyesno('Stop presentation',
            'Do you want to stop running presentation?'):
            self.runButtFun()

    def previewSlide(self):
        self.currentStep = 0
        if getattr(self, 'stationary_navigation', None) is not None:
            self.stationary_navigation.select(self.runningSlide)
        if len(self.onlineSources) > 0:
            self.loadSteps()
            idx = self.runningSlide
            self.slideLabel.configure(text=f'{self.runningSlide+1} /'+\
                f' {len(self.onlineSources)}')
            self.stepsLang['values'] = self.prevVars[idx][1:]
            self.stepsLang.set(self.prevVars[idx][self.prevVars[idx][0]+1])
            if getattr(self, 'stationary_active', False):
                self.stepsLang['values'] = [' / '.join(
                    v for v in self.onlineSources[idx].variants if v != '-----')]
                self.stepsLang.current(0)

    def loadSteps(self):
        self.stepsList.delete(0,'end')
        src = self.onlineSources[self.runningSlide]
        if getattr(self, 'stationary_active', False):
            self.pair2_active = self.paged_active = False
            nav = self.stationary_navigation
            nav.select(self.runningSlide, self.currentStep)
            self.noOfSteps = nav.last_step
            self.cue_rows = [(None, 0, False)]
            self.stepsList.insert('end', '')
            for cue in nav.plans[nav.song].cues:
                for line in cue.stream_page.lines:
                    self.stepsList.insert('end', line.text)
                    self.cue_rows.append((cue, cue.step_index + 1, True))
            self.stepsList.insert('end', '')
            self.cue_rows.append((None, nav.last_step, False))
            self._select_stationary_rows()
            self.stepUpdate()
            return

        # 1) kolik aktivních variant?
        active_var_count = len(self.prevVars[self.runningSlide]) - 1

        # 2) co používají styly
        uses_short2 = False
        uses_stanza = False
        stanza_page_size = 8
        for proj in self.projectors:
            stl = self.projStyles[proj.style]
            for w in stl.get('widgets', []):
                if w.get('type') == 'one_line' and w.get('source') == 'short2':
                    uses_short2 = True
                if w.get('type') == 'stanza_paged':
                    uses_stanza = True
                    stanza_page_size = int(w.get('lines_per_page', 8))

        self._paged_page_size = stanza_page_size
        
        # 3) režimy
        self.pair2_active = bool(uses_short2 and active_var_count == 1 and 'short2steps' in src.lines)
        self.pair2_map = src.lines.get('short2pairmap', [])
        self.paged_active = bool(uses_stanza and not self.pair2_active)

        # 4) předpočítej stránky pro stacionární sál
        if self.paged_active:
            starts, pos = [], 0
            for L in src.lines.get('group_lengths', []):
                k = 0
                while k < L:
                    starts.append(pos + k)  # index prvního řádku na stránce
                    k += stanza_page_size
                pos += L
            self.paged_starts = starts

        # 5) počet kroků (0 = úvod, poslední = konec)
        long_count = len(src.lines.get('longsteps', []))
        if self.pair2_active:
            step_count = len(src.lines.get('short2steps', []))
        elif self.paged_active:
            step_count = len(self.paged_starts)
        else:
            step_count = long_count
        self.noOfSteps = step_count + 1

        # 6) naplň náhled
        self.stepsList.insert('end','-----')
        for line in src.lines['long'][self.prevVars[self.runningSlide][0]]:
            self.stepsList.insert('end', line)
        self.stepsList.insert('end','-----')
        self.stepsList.selection_set(self.currentStep)
        self.stepUpdate()
    
    def stepsLangUpdate(self, *e):
        self.prevVars[self.runningSlide][0] = self.stepsLang.current()
        self.loadSteps()
    
    def stepUpdate(self):
        if getattr(self, 'stationary_active', False):
            nav = self.stationary_navigation
            cue = nav.cue
            self.stepsLabel.configure(text=(
                f'Krok {nav.step}/{nav.last_step - 1} · '
                f'Sál {cue.hall_page.index + 1} · Stream {cue.stream_page.index + 1}'
                if cue else ('Úvod' if nav.step == 0 else 'Konec')))
            return
        if getattr(self, 'pair2_active', False):
            if self.currentStep == 0:
                cur = 0
            elif self.currentStep >= self.noOfSteps:
                cur = len(self.onlineSources[self.runningSlide].lines['short2steps'])
            else:
                pi = self._pair_index_for_list_index(self.currentStep)
                cur = (pi + 1) if pi is not None else 0
            total = len(self.onlineSources[self.runningSlide].lines['short2steps'])
            self.stepsLabel.configure(text=f'{cur} / {total}')
        elif getattr(self, 'paged_active', False):
            if self.currentStep == 0:
                cur = 0
            elif self.currentStep >= self.noOfSteps:
                cur = len(self.paged_starts)
            else:
                gi = self.currentStep - 1  # 0-based index řádku
                pi = 0
                for i, s in enumerate(self.paged_starts):
                    if s <= gi:
                        pi = i
                    else:
                        break
                cur = pi + 1
            total = len(self.paged_starts)
            self.stepsLabel.configure(text=f'{cur} / {total}')
        else:
            self.stepsLabel.configure(text=f'{self.currentStep} / {self.noOfSteps}')

    def stepSelect(self, e):
        if getattr(self, 'stationary_active', False):
            self._stationary_select_row(int(self.stepsList.index('active')))
            return
        # 1) preferuj skutečný výběr
        sel = self.stepsList.curselection()
        if sel:
            idx = sel[-1]
        else:
            # 2) první klik po ztrátě fokusu – vem položku pod kurzorem
            idx = self.stepsList.nearest(e.y) if hasattr(e, 'y') else int(self.stepsList.index('active'))

        if getattr(self, 'pair2_active', False) and idx > 0:
            pi = self._pair_index_for_list_index(idx)
            self.currentStep = self._list_index_for_pair_start(pi) if pi is not None else idx
        else:
            self.currentStep = idx

        self.stepsList.selection_clear(0, 'end')
        self.stepsList.selection_set(self.currentStep)

        if getattr(self, 'pair2_active', False) and self.currentStep > 0:
            pi = self._pair_index_for_list_index(self.currentStep)
            if pi is not None and self.pair2_map[pi][1] is not None:
                self.stepsList.selection_set(self.pair2_map[pi][1] + 1)

        if getattr(self, 'paged_active', False):
            self._select_paged_block()

        self.stepUpdate()
        self.stepGoTo()

    def _line_to_pair(self, s):
        return 0 if s == 0 else ((s - 1) // 2) + 1

    def _pair_index_for_list_index(self, list_idx):
        """Vrátí index páru pro index v listboxu (včetně offsetu 1 kvůli '-----')."""
        k = list_idx - 1
        for i, (a, b) in enumerate(self.pair2_map):
            if k == a or (b is not None and k == b):
                return i
        return None

    def _list_index_for_pair_start(self, pair_i):
        """Vrátí index do listboxu na 1. řádek páru pair_i (včetně offsetu 1)."""
        return self.pair2_map[pair_i][0] + 1
    
    def stepGoTo(self, anim=1):
        if getattr(self, 'stationary_active', False):
            self.stationary_navigation.select(self.runningSlide, self.currentStep)
            self.animation = 0
            self._show_stationary_cue()
            return
        t = time.time()
        # Tato metoda se stará pouze o časování a animaci. 
        # Samotné odeslání dat dělá pomocná funkce _update_projectors.
        if time.time() - self.t < self.animationParams['anim_timeout']:
            self.t = t
            self.animation = 0
            self._update_projectors(anim=0)
        elif self.animation or anim == 0:
            self.t = t
            self.animation = 0
            self._update_projectors(anim=0)
        else:
            self.t = t
            self.animation = 1
            self.animated = list(range(len(self.projectors)))
            self.win.after(self.animationParams['dt'], self.animmator)

    def _sync_stationary_navigation(self):
        nav = self.stationary_navigation
        if not nav.plans:
            return
        changed_song = self.runningSlide != nav.song
        self.runningSlide, self.currentStep = nav.song, nav.step
        if changed_song:
            for proj in self.projectors:
                proj.switchSource()
            self.loadSteps()
            self.stepsLang['values'] = [' / '.join(
                v for v in self.onlineSources[nav.song].variants if v != '-----')]
            self.stepsLang.current(0)
        elif not hasattr(self, 'cue_rows'):
            self.loadSteps()
        self._select_stationary_rows()
        self.slideLabel.configure(text=f'{nav.song + 1} / {len(nav.plans)}')
        self._show_stationary_cue()

    def _stationary_click(self, event):
        if getattr(self, 'stationary_active', False):
            self.stepsList.focus_set()
            self._stationary_select_row(self.stepsList.nearest(event.y))
            return 'break'

    def _stationary_select_row(self, index):
        if not 0 <= index < len(self.cue_rows):
            return
        cue, boundary_step, _ = self.cue_rows[index]
        step = cue.step_index + 1 if cue else boundary_step
        self.stationary_navigation.select(self.runningSlide, step)
        self._sync_stationary_navigation()

    def _select_stationary_rows(self):
        """Text rows belong directly to cues; hall tint also covers the other half."""
        nav = self.stationary_navigation
        active = nav.cue
        stream = any(style_mode(self.projStyles[p.style]) == 'stationary_stream'
                     for p in self.projectors)
        self.stepsList.selection_clear(0, 'end')
        first = None
        hall_rows = []
        background = self.stepsList.cget('background')
        rgb = self.stepsList.winfo_rgb(background)
        alternate = '#' + ''.join(
            f'{round((channel / 257) * 0.92 + 255 * 0.08):02x}' for channel in rgb)
        selection_rgb = self.stepsList.winfo_rgb(self.stepsList.cget('selectbackground'))
        hall_background = '#' + ''.join(
            f'{round((channel / 257) * 0.92 + 255 * 0.08):02x}'
            for channel in selection_rgb)
        section_number = 0
        previous_cue = None
        for index, (cue, step, text_row) in enumerate(self.cue_rows):
            if cue is not None and cue is not previous_cue:
                if (previous_cue is None or
                        cue.occurrence_id != previous_cue.occurrence_id
                        and cue.hall_page is not previous_cue.hall_page):
                    section_number += 1
                previous_cue = cue
            row_background = (alternate if cue is not None and section_number % 2 == 0
                              else background)
            same_hall = active is not None and cue is not None and cue.hall_page is active.hall_page
            if same_hall:
                hall_rows.append(index)
            self.stepsList.itemconfigure(index,
                background=hall_background if same_hall else row_background,
                foreground=self.stepsList.cget('foreground'))
            selected = (text_row and (cue is active if stream else same_hall)
                        or cue is None and step == nav.step)
            if selected:
                self.stepsList.selection_set(index)
            if step == nav.step and first is None:
                first = index
        if first is not None:
            self.stepsList.activate(first)
            if hall_rows:
                self.stepsList.see(hall_rows[-1])
                self.stepsList.see(hall_rows[0])
            self.stepsList.see(first)

    def _show_stationary_cue(self):
        nav = self.stationary_navigation
        if not nav.plans:
            return
        cue = nav.cue
        for proj in self.projectors:
            mode = style_mode(self.projStyles[proj.style])
            if mode != 'legacy_scroll':
                page = (cue.hall_page if mode == 'stationary_hall'
                        else cue.stream_page) if cue else None
                proj.showStationaryPage(page)
            else:
                # Mixed setups follow the source row at the beginning of a cue.
                src = self.onlineSources[nav.song]
                long_step = (src.cue_legacy_steps[nav.step - 1] if cue else
                             (0 if nav.step == 0 else len(src.lines['longsteps']) + 1))
                pairmap = src.lines.get('short2pairmap', [])
                pair_step = next((i + 1 for i, pair in enumerate(pairmap)
                                  if long_step - 1 in pair),
                                 0 if long_step == 0 else len(pairmap) + 1)
                proj.switch((pair_step if pairmap else long_step, long_step), 0)
        self.stepUpdate()
        if os.environ.get('SUPERPRESENTER_CUE_DEBUG') == '1':
            print('[stationary] ' + nav.diagnostic(), flush=True)

    def _update_projectors(self, anim=1):
        """Pomocná metoda, která bezpečně aktualizuje všechna okna projektorů."""
        for proj in self.projectors:
            try:
                mode = style_mode(self.projStyles[proj.style])
                
                if mode == 'stationary_stream':
                    if getattr(self, 'pair2_active', False):
                        if self.currentStep == 0:
                            send_idx = 0
                        elif self.currentStep >= self.noOfSteps:
                            send_idx = len(self.pair2_map)
                        else:
                            pi = self._pair_index_for_list_index(self.currentStep)
                            send_idx = pi if pi is not None else 0
                        proj.switch(send_idx, anim)
                    else:
                        proj.switch(self.currentStep, anim)
                else:
                    # SÁL: Zjistíme sloku podle pairmap
                    pairmap = self.onlineSources[self.runningSlide].lines.get('short2pairmap')
                    if pairmap and self.currentStep < len(pairmap):
                        real_line_index = pairmap[self.currentStep][0]
                        long_step = self.get_long_step_from_line(real_line_index)
                        proj.switch(long_step, anim)
                    else:
                        # Pokud není stream aktivní nebo chybí mapování, sál jde 1:1
                        proj.switch(self.currentStep, anim)
            except Exception as e:
                # Pokud by cokoli selhalo, zkusíme aspoň základní přepnutí, aby program nespadl
                print(f"Update error: {e}")
                proj.switch(self.currentStep, anim)

    def animmator(self):
        if self.animation != 1:
            return
        stillanimated = []

        # spočti send_idx stejně jako v stepGoTo
        if getattr(self, 'pair2_active', False):
            pair_len = len(self.onlineSources[self.runningSlide].lines.get('short2steps', []))
            long_len = len(self.onlineSources[self.runningSlide].lines.get('longsteps', []))
            if self.currentStep == 0:
                send_idx = (0, 0)
            elif self.currentStep >= self.noOfSteps:
                send_idx = (pair_len + 1, long_len + 1)
            else:
                pi = self._pair_index_for_list_index(self.currentStep)
                if pi is None:
                    send_idx = (0, self.currentStep)                 # stream prázdný, sál jede long
                else:
                    send_idx = (pi + 1, self.pair2_map[pi][0] + 1)   # (pair, first-long-of-pair)
        else:
            send_idx = (None, self.currentStep)

        for idx in self.animated:
            a = self.projectors[idx].switch(send_idx, 1)
            if a:
                stillanimated.append(idx)
        if not stillanimated:
            self.animation = 0
            return
        self.animated = stillanimated
        self.win.after(self.animationParams['dt'], self.animmator)

    def nextSlide(self):
        if self.runState and getattr(self, 'stationary_active', False):
            if self.runningSlide + 1 < len(self.onlineSources):
                self.stationary_navigation.select(self.runningSlide + 1)
                self._sync_stationary_navigation()
            return
        if self.runState:
            if self.runningSlide < len(self.onlineSources)-1:
                self.runningSlide += 1
                # self.stepsList.selection_set(self.currentStep)
                self.previewSlide()
                for proj in self.projectors:
                    proj.switchSource()
    
    def prevSlide(self):
        if self.runState and getattr(self, 'stationary_active', False):
            if self.runningSlide > 0:
                self.stationary_navigation.select(self.runningSlide - 1)
                self._sync_stationary_navigation()
            return
        if self.runState:
            if self.runningSlide > 0:
                self.runningSlide -= 1
                # self.stepsList.selection_set(self.currentStep)
                self.previewSlide()
                for proj in self.projectors:
                    proj.switchSource()

    def nextStep(self):
        if not self.runState:
            return
        if getattr(self, 'stationary_active', False):
            self.stationary_navigation.move(1)
            self._sync_stationary_navigation()
            return

        # --- PÁROVANÝ STREAM (short2) ---
        if getattr(self, 'pair2_active', False):
            if self.animation == 0:
                self.stepsList.selection_clear(0, 'end')
                if self.currentStep == 0:
                    new_idx = self._list_index_for_pair_start(0) if self.pair2_map else self.noOfSteps
                else:
                    pi = self._pair_index_for_list_index(self.currentStep) or 0
                    if pi + 1 < len(self.pair2_map):
                        new_idx = self._list_index_for_pair_start(pi + 1)
                    else:
                        self.nextSlide()
                        return
                self.currentStep = new_idx
                self.stepsList.selection_set(self.currentStep)
                self._select_paged_block()
                pi = self._pair_index_for_list_index(self.currentStep)
                if pi is not None and self.pair2_map[pi][1] is not None:
                    self.stepsList.selection_set(self.pair2_map[pi][1] + 1)
                self.stepUpdate()
            self.stepGoTo()
            return

        # --- STACIONÁRNÍ SÁL (paged) ---
        if getattr(self, 'paged_active', False):
            if self.animation == 0:
                self.stepsList.selection_clear(0, 'end')

                long_len = len(self.onlineSources[self.runningSlide].lines.get('longsteps', []))
                last_sep_idx = long_len + 1  # index posledního "-----" v Listboxu

                if self.currentStep == 0:
                    # první stránka, pokud existuje
                    if self.paged_starts:
                        new_idx = self.paged_starts[0] + 1
                    else:
                        # žádné řádky → rovnou "konec" = prázdno (poslední -----)
                        new_idx = last_sep_idx
                else:
                    gi = self.currentStep - 1  # reálný index řádku (0-based)
                    new_idx = None
                    for s in self.paged_starts:
                        if s > gi:
                            new_idx = s + 1
                            break

                    if new_idx is None:
                        # NENÍ další stránka → nejdřív skoč na POSLEDNÍ "-----"
                        if self.currentStep < last_sep_idx:
                            new_idx = last_sep_idx
                        else:
                            # už jsme na posledním "-----" → další píseň
                            self.nextSlide()
                            return

                self.currentStep = new_idx
                self.stepsList.selection_set(self.currentStep)
                self._select_paged_block()   # u posledního "-----" nic nevybírá (správně)
                self.stepUpdate()
            self.stepGoTo()  # pošle prázdný slide při posledním "-----"
            return

        # --- NEPAGED (původní chování) ---
        if self.currentStep < self.noOfSteps:
            if self.animation == 0:
                self.stepsList.selection_clear(0, 'end')
                self.currentStep = min(self.currentStep + 1, self.noOfSteps)
                self.stepsList.selection_set(self.currentStep)
                self._select_paged_block()
                self.stepUpdate()
            self.stepGoTo()
        else:
            self.nextSlide()
    def prevStep(self):
        if self.runState and getattr(self, 'stationary_active', False):
            self.stationary_navigation.move(-1)
            self._sync_stationary_navigation()
            return
        if not self.runState:
            return

        # NOVÉ: na úplně prvním "-----" → přejdi na předchozí píseň
        # a nastav se na poslední obsahový řádek (ne na závěrečné "-----").
        if self.currentStep == 0 and self.runningSlide > 0:
            # Přepni na předchozí píseň (rebuildne flags, paged_starts atd.)
            self.prevSlide()

            # Zvol cílový index podle aktivního režimu
            target = 0
            if getattr(self, 'pair2_active', False) and getattr(self, 'pair2_map', []):
                # poslední pár → jeho první řádek
                target = self._list_index_for_pair_start(len(self.pair2_map) - 1)
            elif getattr(self, 'paged_active', False):
                # poslední reálný řádek long (nikoli závěrečné "-----")
                long_len = len(self.onlineSources[self.runningSlide].lines.get('longsteps', []))
                target = long_len if long_len > 0 else self.noOfSteps  # fallback: když by píseň byla prázdná
            else:
                # klasika: poslední obsahový krok (noOfSteps = long_count + 1 kvůli závěrečnému "-----")
                target = max(1, self.noOfSteps - 1) if self.noOfSteps > 0 else 0

            if self.animation == 0:
                self.stepsList.selection_clear(0, 'end')
                self.currentStep = target
                self.stepsList.selection_set(self.currentStep)

                # u pair2 zvýrazni i druhý řádek páru (pokud existuje)
                if getattr(self, 'pair2_active', False) and self.currentStep > 0:
                    pi = self._pair_index_for_list_index(self.currentStep)
                    if pi is not None and self.pair2_map[pi][1] is not None:
                        self.stepsList.selection_set(self.pair2_map[pi][1] + 1)

                # u paged vyznač celou stránku
                self._select_paged_block()
                self.stepUpdate()

            self.stepGoTo(0)  # rovnou bez animace
            return

        # --- PÁROVANÝ STREAM (short2) ---
        if getattr(self, 'pair2_active', False):
            if self.animation == 0:
                self.stepsList.selection_clear(0, 'end')
                if self.currentStep <= 1:
                    new_idx = 0
                else:
                    pi = self._pair_index_for_list_index(self.currentStep) or 0
                    if pi > 0:
                        new_idx = self._list_index_for_pair_start(pi - 1)
                    else:
                        new_idx = 0
                self.currentStep = new_idx
                self.stepsList.selection_set(self.currentStep)
                self._select_paged_block()
                if self.currentStep > 0:
                    pi = self._pair_index_for_list_index(self.currentStep)
                    if pi is not None and self.pair2_map[pi][1] is not None:
                        self.stepsList.selection_set(self.pair2_map[pi][1] + 1)
                self.stepUpdate()
            self.stepGoTo()
            return

        # --- STACIONÁRNÍ SÁL (paged) ---
        if getattr(self, 'paged_active', False):
            if self.animation == 0:
                self.stepsList.selection_clear(0, 'end')
                if self.currentStep <= 1:
                    new_idx = 0
                else:
                    gi = self.currentStep - 1
                    prev_start = None
                    for s in self.paged_starts:
                        if s < gi:
                            prev_start = s
                        else:
                            break
                    new_idx = (prev_start + 1) if prev_start is not None else 0
                self.currentStep = new_idx
                self.stepsList.selection_set(self.currentStep)
                self._select_paged_block()
                self.stepUpdate()
            self.stepGoTo()
            return

        # --- NEPAGED (původní chování) ---
        if self.currentStep > 0:
            if self.animation == 0:
                self.stepsList.selection_clear(0, 'end')
                self.currentStep = max(self.currentStep - 1, 0)
                self.stepsList.selection_set(self.currentStep)
                self._select_paged_block()
                self.stepUpdate()
            self.stepGoTo()
        else:
            if self.runningSlide > 0:
                # (zde už to díky hornímu bloku obvykle neskončí)
                self.prevSlide()
                self.stepsList.selection_clear(self.currentStep)
                self.currentStep = self.noOfSteps - 1
                self.stepsList.selection_set(self.currentStep)
                self._select_paged_block()
                self.stepGoTo(0)
    def nextSlideKey(self, *e):
        try:
            a = self.win.focus_get()._name
        except:
            a = ''
        if not a in ['!text', '!entry']:
            self.nextSlide()

    def prevSlideKey(self, *e):
        try:
            a = self.win.focus_get()._name
        except:
            a = ''
        if not a in ['!text', '!entry']:
            self.prevSlide()

    def nextStepKey(self, *e):
        try:
            a = self.win.focus_get()._name
        except:
            a = ''
        if not a in ['!text', '!entry']:
            self.nextStep()

    def prevStepKey(self, *e):
        try:
            a = self.win.focus_get()._name
        except:
            a = ''
        if not a in ['!text', '!entry']:
            self.prevStep()

    def getSourceTypes(self):
        types = [{'type':'long'}]
        for proj in self.projectors:
            if style_mode(self.projStyles[proj.style]) != 'legacy_scroll':
                continue
            srctypes = self.projStyles[proj.style]['sources']
            for srctype in srctypes:
                if not srctype in types:
                    types.append(srctype)
        return types

    def newSongFun(self, *e):
        if not self.song_editor_widget.new_song():
            return
        self.draft_open = True
        self.sourceID = len(self.sourceList)
        self._update_new_button_state()
        self.viewDraft()

    def _select_paged_block(self):
        if not getattr(self, 'paged_active', False):
            return
        # v paged módu je currentStep index řádku+1; jen úvod vynech
        if self.currentStep <= 0:
            return

        # horní mez podle počtu řádků, ne podle počtu stránek
        long_len = len(self.onlineSources[self.runningSlide].lines.get('longsteps', []))
        if self.currentStep > long_len:
            return

        gi = self.currentStep - 1  # 0-based index řádku

        # najdi index stránky, do které řádek patří
        page_i = 0
        for i, s in enumerate(self.paged_starts):
            if s <= gi:
                page_i = i
            else:
                break

        start = self.paged_starts[page_i]

        # hranice skupiny (sloky), do které start patří
        groups = self.onlineSources[self.runningSlide].lines.get('group_lengths', [])
        pos = 0
        group_end = len(self.onlineSources[self.runningSlide].lines.get('long', [[]])[0])  # fallback
        for L in groups:
            if pos <= start < pos + L:
                group_end = pos + L
                break
            pos += L

        # další stránka (může být i začátek další sloky)
        if page_i + 1 < len(self.paged_starts):
            next_boundary = self.paged_starts[page_i + 1]
        else:
            next_boundary = group_end

        # nepřekroč stránku ani konec sloky
        end_excl = min(start + self._paged_page_size, next_boundary, group_end)
        end_incl = max(start, end_excl - 1)  # Listbox bere 'last' inkluzivně

        self.stepsList.selection_clear(0, 'end')
        self.stepsList.selection_set(start + 1, end_incl + 1)  

    def changeCollection(self, *e):
        if self.projectorID >= 0:
            show = self.collectionState.get()
            proj = self.projectors[self.projectorID]
            proj.collection = show  # vždy ulož

            # je-li okno/Canvas už otevřený, zkus rovnou přepnout
            try:
                proj.set_collection_visible(show)
            except Exception:
                # okno zatím neběží → nic, stav je uložený a promítne se při startu
                pass

    def get_long_step_from_line(self, line_idx):
        try:
            src = self.onlineSources[self.runningSlide]
            groups = src.lines.get('group_lengths', [])
            current_total = 0
            for i, length in enumerate(groups):
                current_total += length
                if line_idx < current_total:
                    return i
        except:
            pass
        return 0
                
class Widget_OneLine():
    def __init__(self, canvas:tk.Canvas, source, style, fonts):
        self.source = source[style['source']]
        self.steps = source[style['source']+'steps']
        self.fonts = fonts
        self.style = style
        self.canvas = canvas
        self.lines = []
        self.srcType = style['source']
        y = style['y'] -style['y1']*0.5
        for _ in self.source[1:]:
            y -= style['y2']*0.5
        self.lines.append(canvas.create_text(style['x'], y, fill=style['fill'],
            font=fonts[style['primaryFont']], text='', anchor = 'n'))
        y += style['y1']
        for _ in self.source[1:]:
            self.lines.append(canvas.create_text(style['x'], y, fill=style['fill'],
                font=fonts[style['secondaryFont']], text='', anchor = 'n'))
            y += style['y2']

    def switch(self, idx, *e):
        if idx == 0 or idx > len(self.steps):
            for id2 in self.lines:
                self.canvas.itemconfigure(id2, {'text':''})
        else:
            var = 0
            for id2 in self.lines:
                self.canvas.itemconfigure(
                    id2,{'text':self.source[var][self.steps[idx-1]]})
                var+=1
        return 0

    def switchSource(self, source):
        self.source = source[self.srcType]
        self.steps = source[self.srcType+'steps']
        for line in self.lines:
            self.canvas.delete(line)
        self.lines = []
        self.srcType = self.style['source']
        y = self.style['y'] -self.style['y1']*0.5
        for _ in self.source[1:]:
            y -= self.style['y2']*0.5
        self.lines.append(self.canvas.create_text(self.style['x'], y, fill=self.style['fill'],
            font=self.fonts[self.style['primaryFont']], text='', anchor = 'n'))
        y += self.style['y1']
        for _ in self.source[1:]:
            self.lines.append(self.canvas.create_text(self.style['x'], y, fill=self.style['fill'],
                font=self.fonts[self.style['secondaryFont']], text='', anchor = 'n'))
            y += self.style['y2']

    def widgetRaise2top(self):
        for line in self.lines:
            self.canvas.tag_raise(line)

class Widget_FlowLines():
    def __init__(self, canvas:tk.Canvas, source, style, fonts):
        self.source = source[style['source']]
        self.steps = source[style['source']+'steps']
        self.laststep = max(self.steps+[-1])+1
        self.canvas = canvas
        self.lines = []
        self.yCoords = []
        self.style = style
        self.fonts = fonts
        self.idx = 0
        self.animation = 0
        y = style['y'] - style['y1']*0.5
        for _ in self.source[1:]:
            y -= style['y2']*0.5
        self.row = style['y1'] + (len(self.source)-1)*style['y2'] +\
            style['gap']
        for idx in range(len(self.source[0])):
            self.lines.append(canvas.create_text(style['x'], y, fill=style['fill'],
                font=fonts[style['primaryFont']], text=self.source[0][idx], 
                anchor = 'n'))
            self.yCoords.append(y)
            y += style['y1']
            for idx2 in range(1,len(self.source)):
                self.lines.append(canvas.create_text(style['x'], y, fill=style['fill'],
                    font=fonts[style['secondaryFont']], text=self.source[idx2][idx], 
                    anchor = 'n'))
                self.yCoords.append(y)
                y += style['y2']
            y += style['gap']
        
        self.animationPath()
 
    def switch(self, idx, e):
        if e == 0:
            return self.switchTo(idx)
        else:
            return self.switchAnimation(idx)

    def switchTo(self, idx):
        self.animation = 0
        if idx == 0:
            id3 = 0
            for id2 in self.lines:
                self.canvas.coords(id2, self.style['x'], 
                self.yCoords[id3] + self.style['stp_in'] + \
                self.row)
                id3 += 1
        elif idx == len(self.steps)+1:
            id3 = 0
            for id2 in self.lines:
                self.canvas.coords(id2, self.style['x'], 
                self.yCoords[id3] - self.style['stp_out'] - \
                self.row*(self.laststep))
                id3 += 1
        else:
            id3 = 0
            for id2 in self.lines:
                self.canvas.coords(id2, self.style['x'], 
                self.yCoords[id3] - self.row*self.steps[idx-1])
                id3 += 1
        self.idx = idx
        return 0

    def switchAnimation(self, idx):
        if self.animation:
            if self.animStep == self.style['path_steps']:
                self.animation = 0
                return 0
            for id2 in self.lines:
                self.canvas.move(id2, 0, self.step*self.path[self.animStep])
            self.animStep += 1
            return 1
            
        else:
            if idx == self.idx:
                return 0
            self.animation = 1
            if self.idx == 0:
                self.step = - self.style['stp_in'] - self.row
            elif self.idx == len(self.steps)+1:
                self.step = self.style['stp_out'] + (self.laststep)*self.row
            else:
                self.step = self.steps[self.idx-1]*self.row
            if idx == 0:
                self.step += self.style['stp_in'] + self.row
            elif idx == len(self.steps)+1:
                self.step -= self.style['stp_out'] + (self.laststep)*self.row
            else:
                self.step -= self.steps[idx-1]*self.row
            self.idx = idx
            self.animStep = 0
            return 1

    def animationPath(self):
        n = self.style['path_steps']
        if self.style['path'] == 'linear':
            fun = lambda x: x
        elif self.style['path'] == 'cubic':
            fun = lambda x: -2*(x)**3 + 3*(x)**2
        elif self.style['path'] == 'sinusoidal':
            fun = lambda x: 0.5*(1-math.cos(x*math.pi))
        elif self.style['path'] == 'poly5':
            fun = lambda x: 6*x**5 - 15*x**4 + 10*x**3
        else:
            fun = lambda x: x
        y0 = 0
        self.path = []
        for x in range(1,n+1):
            y = fun(x/n)
            self.path.append(y - y0)
            y0 = y
        if y != 1:
            self.path = [x/y for x in self.path]

    def switchSource(self, source):
        self.source = source[self.style['source']]
        self.steps = source[self.style['source']+'steps']
        self.laststep = max(self.steps+[-1])+1
        for line in self.lines:
            self.canvas.delete(line)
        self.lines = []
        self.yCoords = []
        self.idx = 0
        y = self.style['y'] - self.style['y1']*0.5
        for _ in self.source[1:]:
            y -= self.style['y2']*0.5
        self.row = self.style['y1'] + (len(self.source)-1)*self.style['y2'] + \
            self.style['gap']
        for idx in range(len(self.source[0])):
            self.lines.append(self.canvas.create_text(self.style['x'], y, 
                fill=self.style['fill'], font=self.fonts[self.style['primaryFont']], 
                text=self.source[0][idx], anchor = 'n'))
            self.yCoords.append(y)
            y += self.style['y1']
            for idx2 in range(1,len(self.source)):
                self.lines.append(self.canvas.create_text(self.style['x'], y, 
                    fill=self.style['fill'], 
                    font=self.fonts[self.style['secondaryFont']], 
                    text=self.source[idx2][idx], anchor = 'n'))
                self.yCoords.append(y)
                y += self.style['y2']
            y += self.style['gap']
            
        self.switchTo(0)

    def widgetRaise2top(self):
        for line in self.lines:
            self.canvas.tag_raise(line)

class Widget_StanzaPaged():
    """
    Statické promítání po slokách/stránkách.
    Na plátně drží n řádků (default 8). Přepíná se stránka,
    když zvolený řádek (stream / long) spadne mimo aktuální stránku.
    """
    def __init__(self, canvas: tk.Canvas, source, style, fonts):
        self.canvas = canvas
        self.style = style
        self.fonts = fonts

        # zdroj dat
        src_key = style.get('source', 'long')
        self.source = source[src_key]                  # [var0][lines], [var1]...
        self.steps  = source[src_key + 'steps']        # 0..N-1
        self.group_lengths = source.get('group_lengths', [])
        self.pairmap = source.get('short2pairmap', [])

        # parametry rozložení
        self.page_size = int(style.get('lines_per_page', 8))
        self.x = style['x']
        self.y = style['y']
        self.y1 = style['y1']          # mezera hlavní řádky
        self.y2 = style['y2']          # mezera mezi variantami
        self.gap = style.get('gap', 12)
        self.fill = style['fill']
        self.primaryFont = fonts[style['primaryFont']]
        self.secondaryFont = fonts[style['secondaryFont']]

        # vypočti začátky stránek podle skupin (slok)
        self._rebuild_page_starts()

        # předkresli textová pole (max page_size řádků × počet variant)
        self._build_text_items()

        # žádná stránka není vykreslená
        self.cur_page = None

    def _rebuild_page_starts(self):
        self.page_starts = []
        pos = 0
        for L in self.group_lengths:
            k = 0
            while k < L:
                self.page_starts.append(pos + k)   # index prvního řádku na stránce
                k += self.page_size
            pos += L
        # sentinel pro hranici konce
        self.page_starts.append(pos)

    def _build_text_items(self):
        self.text_items = []
        n_vars = len(self.source)
        y = self.y - self.y1 * 0.5
        
        # ZMĚNA: Vytvoříme rezervu 100 řádků, aby se tam vešla i celá píseň
        max_rows_to_create = 100 
        
        for _row in range(max_rows_to_create):
            row_ids = []
            row_ids.append(self.canvas.create_text(
                self.x, y, fill=self.fill, font=self.primaryFont,
                text='', anchor='n'
            ))
            y += self.y1
            for _v in range(1, n_vars):
                row_ids.append(self.canvas.create_text(
                    self.x, y, fill=self.fill, font=self.secondaryFont,
                    text='', anchor='n'
                ))
                y += self.y2
            y += self.gap
            self.text_items.append(row_ids)

    def _clear(self):
        for row in self.text_items:
            for cid in row:
                self.canvas.itemconfigure(cid, {'text': ''})

    def _page_of(self, line_idx_0based: int) -> int | None:
        if not self.page_starts or line_idx_0based < 0:
            return None
        # binární hledání by bylo rychlejší, ale lineární stačí
        for i in range(len(self.page_starts) - 1):
            if self.page_starts[i] <= line_idx_0based < self.page_starts[i + 1]:
                return i
        return None

    def _render_page(self, page_i: int):
        if page_i is None or page_i < 0 or page_i >= len(self.page_starts) - 1:
            self._clear()
            self.cur_page = None
            return

        start = self.page_starts[page_i]
        
        # ZMĚNA: Odstraníme "min(..., start + self.page_size)" 
        # a vezmeme prostě vše až do konce aktuální sekce/skupiny
        end = self.page_starts[page_i + 1] 
        
        rows_to_show = max(0, end - start)
        n_vars = len(self.source)

        # Promazání starých textů před vykreslením (důležité!)
        self._clear()

        for r in range(rows_to_show): # Vykreslíme jen tolik řádků, kolik je v sekci
            for v in range(n_vars):
                text = ''
                idx = start + r
                if idx < len(self.source[v]):
                    text = self.source[v][idx]
                # Kontrola, abychom nepřetekli vytvořené položky (pojistka)
                if r < len(self.text_items):
                    self.canvas.itemconfigure(self.text_items[r][v], {'text': text})

        self.cur_page = page_i

    def switch(self, idx, e):
        """
        idx může být:
          - int (kompatibilita: index do steps, 0 = úvod, len+1 = konec)
          - tuple (pair_index, long_index)
        """
        # vyzobej long_index (krok pro 'long'), 0/len+1 = mezistavy
        if isinstance(idx, tuple):
            _, long_idx = idx
        else:
            long_idx = idx

        if long_idx == 0:
            self._clear()
            return 0
        if long_idx >= len(self.steps) + 1:
            self._clear()
            return 0

        # steps = [0,1,2,...] → reálný index řádku
        line_idx = self.steps[long_idx - 1]
        page_i = self._page_of(line_idx)
        if page_i != self.cur_page:
            self._render_page(page_i)
        return 0

    def switchSource(self, source):
        src_key = self.style.get('source', 'long')
        self.source = source[src_key]
        self.steps  = source[src_key + 'steps']
        self.group_lengths = source.get('group_lengths', [])
        self.pairmap = source.get('short2pairmap', [])
        self._rebuild_page_starts()
        self._render_page(None)

    def widgetRaise2top(self):
        for row in self.text_items:
            for cid in row:
                self.canvas.tag_raise(cid)

class Widget_Image():
    def __init__(self, canvas: tk.Canvas, style:dict, win):
        self.canvas = canvas
        source = style['source']
        if source[0] != '\\':
            source = '\\' + source
        source = path.dirname(__file__) + source
        image = Image.open(source)
        if 'resize' in style.keys():
            image = image.resize((style['resize'][0],style['resize'][1]), 1)
            pass
        self.image = ImageTk.PhotoImage(image)
        self.id = canvas.create_image(style['x'], style['y'], 
            anchor=style['anchor'], image=self.image)

    def widgetRaise2top(self):
        self.canvas.tag_raise(self.id)


class ProjWindow():
    COLLECTION_CFG = {
        'source': 'sbirka_qr.png',  # výchozí fallback v kořeni projektu
        'relx': 0.65,
        'rely': 0.30,
        'size': 360,
        'anchor': 'center'
    }

    def __init__(self, master:GUI):
        self.master = master
        self.monitor = 0
        self.style = 0
        self.fullscreen = 1
        self.winPlacement = ''
        self.animation = 0

        # nově:
        self.collection = False
        self.collection_item = None  # canvas image id
        self.collection_img = None 

    def _get_collection_cfg(self):
        stl = self.master.projStyles[self.style]
        if 'collection' not in stl:
            return None
        cfg = dict(self.COLLECTION_CFG)
        cfg.update(stl['collection'])
        return cfg
    
    def project(self):
        stl = self.master.projStyles[self.style]

        self.win = tk.Toplevel(self.master.win)
        self.win.bind('<Shift-Right>', self.master.nextSlideKey)
        self.win.bind('<Shift-Left>', self.master.prevSlideKey)
        self.win.bind('<Right>', self.master.nextStepKey)
        self.win.bind('<Left>', self.master.prevStepKey)
        self.win.bind('<Escape>',self.master.runButtFun)

        self.win.title(f'projector window {stl["name"]}')

        if self.fullscreen:
            mon = self.master.monitors[self.monitor]
            self.win.overrideredirect(1)
            self.win.geometry(f'{mon.width}x{mon.height}+{mon.x}+{mon.y}')
            try:
                self.win.configure(background=stl['win']['background'])
            except:
                pass
            # self.win.attributes('-fullscreen', True)
        elif self.winPlacement == '':
            mon = self.master.monitors[self.monitor]
            self.win.geometry(f'+{mon.x}+{mon.y}')
            self.win.config(stl["win"])
        else:
            self.win.geometry(self.winPlacement)
            self.win.config(stl["win"])
        # if self.fullscreen:
        #     self.win.attributes('-fullscreen', True)

        

        self.canvas = tk.Canvas(self.win)
        self.canvas.config(stl["canvas"])

        self.animated = []
        self.others = []
        self.tops = []
        fonts = {}
        for font in stl['fonts'].keys():
            fnt = stl['fonts'][font]
            fonts[font] = tkFont.Font(
                family=fnt['family'],
                size=fnt['size'],
                weight=fnt['weight'],
                slant=fnt['slant']
            )
        for widget in stl["widgets"]:
            if (style_mode(stl) != 'legacy_scroll'
                    and widget['type'] in ('one_line', 'flow_lines', 'stanza_paged')):
                idx = len(self.animated)
                self.animated.append(StationaryPageWidget(
                    self.canvas, widget, fonts, style_mode(stl)))
                x = 'animated'
            elif widget["type"] == 'one_line':
                if len(self.master.onlineSources) == 0:
                    continue
                idx = len(self.animated)
                self.animated.append(Widget_OneLine(self.canvas,
                    self.master.onlineSources[\
                    self.master.runningSlide].lines, widget, fonts))
                x = 'animated'
            elif widget["type"] == 'flow_lines':
                if len(self.master.onlineSources) == 0:
                    continue
                idx = len(self.animated)
                self.animated.append(Widget_FlowLines(self.canvas,
                    self.master.onlineSources[\
                    self.master.runningSlide].lines, widget, fonts))
                self.animated[-1].switch(0,0)
                x = 'animated'
            elif widget['type'] == 'image':
                idx = len(self.others)
                self.others.append(Widget_Image(self.canvas, widget, self.win))
                x = 'others'
            elif widget["type"] == 'stanza_paged':
                if len(self.master.onlineSources) == 0:
                    continue
                idx = len(self.animated)
                self.animated.append(Widget_StanzaPaged(
                    self.canvas,
                    self.master.onlineSources[self.master.runningSlide].lines,
                    widget,
                    fonts
                ))
                self.animated[-1].switch(0, 0)
                x = 'animated'
            if 'topmost' in widget.keys():
                if widget['topmost']:
                    self.tops.append([x, idx])

        # self.canvas.place(relx=0.5, rely=0.5, anchor='center')
        self.canvas.place(stl["canvas.place"])
        self.collection_item = None
        self.collection_img = None
        self._build_collection_overlay()
        self.set_collection_visible(self.collection)
        self.canvas.bind('<Configure>', self._reposition_collection_overlay)
        self.win.protocol("WM_DELETE_WINDOW", self.master.onProjectorClose)

    def _reposition_collection_overlay(self, *_):
        if self.collection_item is None:
            return
        cfg = self._get_collection_cfg()
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        x = int(float(cfg.get('relx', 0.87)) * w)
        y = int(float(cfg.get('rely', 0.55)) * h)
        self.canvas.coords(self.collection_item, x, y)
        
    def stopProjection(self):
        try:
            self.winPlacement = f'+{self.win.winfo_x()}+{self.win.winfo_y()}'
            self.win.destroy()
            del self.win
        except:
            pass

    def showStationaryPage(self, page):
        for widget in self.animated:
            widget.show_page(page)

    def switch(self, idx, e):
        # idx může být int (zpětná kompatibilita) nebo tuple (pair_idx, long_idx)
        is_tuple = isinstance(idx, tuple)

        if self.animation:
            stillAnimated = []
            for idx2 in self.stillAnimated:
                widget = self.animated[idx2]
                widx = idx
                if not isinstance(widget, Widget_StanzaPaged):
                    if is_tuple:
                        if isinstance(widget, Widget_OneLine) and getattr(widget, "srcType", "") == "short2":
                            widx = idx[0] if idx[0] is not None else idx[1]
                        elif isinstance(widget, Widget_FlowLines):
                            widx = idx[1]
                        else:
                            widx = idx[1]
                a = widget.switch(widx, e)
                if a:
                    stillAnimated.append(idx2)
            self.animation = len(stillAnimated) > 0
            if self.animation:
                self.stillAnimated = stillAnimated
            return self.animation
        else:
            self.stillAnimated = []
            self.animation = 1
            for i, widget in enumerate(self.animated):
                widx = idx
                if not isinstance(widget, Widget_StanzaPaged):
                    if is_tuple:
                        if isinstance(widget, Widget_OneLine) and getattr(widget, "srcType", "") == "short2":
                            widx = idx[0] if idx[0] is not None else idx[1]
                        elif isinstance(widget, Widget_FlowLines):
                            widx = idx[1]
                        else:
                            widx = idx[1]
                a = widget.switch(widx, e)
                if a:
                    self.stillAnimated.append(i)
            self.animation = (len(self.stillAnimated) > 0)
            return self.animation
    
    def switchSource(self):
        for widget in self.animated:
            widget.switchSource(self.master.onlineSources\
                [self.master.runningSlide].lines)
        for x in self.tops:
            if x[0] == 'animated':
                self.animated[x[1]].widgetRaise2top()
            elif x[0] == 'others':
                self.others[x[1]].widgetRaise2top()
        if self.collection_item is not None:
            self.canvas.tag_raise(self.collection_item)
            
    def _build_collection_overlay(self):
        from PIL import Image, ImageTk
        cfg = self._get_collection_cfg()
        if cfg is None:
            return  # tento styl sbírku nepodporuje

        src = cfg.get('source', 'sbirka_qr.png')
        if not path.isabs(src):
            src = path.join(self.master.dir, src.lstrip('\\/'))
        src = path.normpath(src)

        img = Image.open(src)
        sz = int(cfg.get('size', 360))
        if sz > 0:
            img = img.resize((sz, sz), Image.LANCZOS)

        self.collection_img = ImageTk.PhotoImage(img)

        self.canvas.update_idletasks()
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        x = int(float(cfg.get('relx', 0.87)) * w)
        y = int(float(cfg.get('rely', 0.55)) * h)
        anchor = cfg.get('anchor', 'center')

        if self.collection_item is not None:
            try:
                self.canvas.delete(self.collection_item)
            except Exception:
                pass

        self.collection_item = self.canvas.create_image(
            x, y, image=self.collection_img, anchor=anchor, state='hidden'
        )
        self.canvas.tag_raise(self.collection_item)

    def set_collection_visible(self, show: bool):
        """Zapne/vypne QR jen u stylů, které ho mají definovaný."""
        if self._get_collection_cfg() is None:
            return  # pro tento styl ignoruj přepínač
        self.collection = bool(show)
        if self.collection_item is None:
            self._build_collection_overlay()
            if self.collection_item is None:
                return
        self.canvas.itemconfigure(self.collection_item,
                                  state=('normal' if self.collection else 'hidden'))
        try:
            self._reposition_collection_overlay()
        except Exception:
            pass
        self.canvas.tag_raise(self.collection_item)
        self.canvas.update_idletasks()

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
                    except:
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
                        except:
                            out.append({var:val})
                        return out
                    a = tag[idx]
                try:
                    numval = float(val)
                    out.append({var:numval})
                except:
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

def doNothing(*e):
    pass

def main():
    gui = GUI()
    gui.song_editor_widget.start_recovery(on_restored=gui.on_editor_restored)
    
    # gui._testProj()

    gui.run()

if __name__ == '__main__':
    main()
