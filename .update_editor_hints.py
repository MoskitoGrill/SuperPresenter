from pathlib import Path
p=Path('song_editor.py'); s=p.read_text(encoding='utf-8')
pos=s.index('class SongEditor:')
s=s[:pos]+'''def add_title_placeholder(entry, variable):
    """Display a hint without inserting it into the song's title variable."""
    hint = tk.Label(entry, text="Název zde", cursor="xterm", takefocus=False)
    active = False

    def refresh(*_):
        if not variable.get() and not active:
            hint.configure(background=entry.cget("background"),
                           foreground=entry.cget("foreground"), font=entry.cget("font"))
            hint.place(x=3, rely=0.5, anchor="w")
        else:
            hint.place_forget()

    def focus_in(event=None):
        nonlocal active
        active = True
        hint.place_forget()

    def focus_out(event=None):
        nonlocal active
        active = False
        refresh()

    def click(event):
        focus_in()
        entry.focus_set()
        return "break"

    hint.bind("<Button-1>", click)
    entry.bind("<Button-1>", focus_in, add="+")
    entry.bind("<FocusIn>", focus_in, add="+")
    entry.bind("<FocusOut>", focus_out, add="+")
    entry.bind("<Configure>", refresh, add="+")
    trace = variable.trace_add("write", refresh)
    entry.bind("<Destroy>", lambda event: variable.trace_remove("write", trace)
               if event.widget == entry else None, add="+")
    refresh()
    return hint


'''+s[pos:]
s=s.replace("            self.title_entry.pack(fill='x', padx=5)", "            self.title_entry.pack(fill='x', padx=5)\n            add_title_placeholder(self.title_entry, self.title_variable)",1)
s=s.replace('            self.session.save(target, overwrite=overwrite, rename=rename)', '''            missing = self.session.omitted_sections()
            if missing:
                def section_label(sid):
                    match = re.fullmatch(r"([vrb])([0-9]+)", sid)
                    return f"{ {'v': 'Sloka', 'r': 'Refrén', 'b': 'Bridge'}[match[1]]} {match[2]} ({sid})" if match else sid
                details = "\\n".join(f"{name}: {', '.join(section_label(sid) for sid in sections)}"
                                    for name, sections in missing.items())
                if not messagebox.askyesno(
                        "Vynechané sekce v opakování",
                        "V těchto opakováních nejsou použity některé sekce písně:\\n\\n"
                        + details + "\\n\\nVynechání může být záměrné. Přesto uložit?",
                        icon="warning", parent=self.root):
                    return False
            self.session.save(target, overwrite=overwrite, rename=rename)''',1)
p.write_text(s,encoding='utf-8')
p=Path('super_presenter.py'); s=p.read_text(encoding='utf-8')
s=s.replace('        from song_editor import SongEditor', '        from song_editor import SongEditor, add_title_placeholder',1)
s=s.replace('        self.sourceTitleEntry = tk.Entry(self.sourceNav, width=40, textvariable=self.song_title)', '        self.sourceTitleEntry = tk.Entry(self.sourceNav, width=40, textvariable=self.song_title)\n        add_title_placeholder(self.sourceTitleEntry, self.song_title)',1)
p.write_text(s,encoding='utf-8')
p=Path('superpresenter/services/song_edit_session.py'); s=p.read_text(encoding='utf-8'); pos=s.index('    def remove_section')
s=s[:pos]+'''    def omitted_sections(self):
        """Advisory coverage of every named repetition, without expanding loops.

        Section IDs are whole tokens; line/range suffixes and repeat counts do
        not form section references. This is not a construct syntax validator.
        """
        sections = list(dict.fromkeys(sid for variant in self.song.variants.values() for sid in variant))
        missing = {}
        for name, guide in (self.song.repetitions or {"(žádné opakování)": ""}).items():
            tokens = re.findall(r"\\*[0-9]+|\\.[0-9]+(?::[0-9]+)?|[^\\s().:*]+", guide)
            used = {token for token in tokens if not token.startswith(('*', '.'))}
            omitted = [sid for sid in sections if sid not in used]
            if omitted:
                missing[name] = omitted
        return missing

'''+s[pos:]; p.write_text(s,encoding='utf-8')
