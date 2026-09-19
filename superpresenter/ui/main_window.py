"""Main application window and presentation controls."""
import os
from copy import deepcopy
import tkinter as tk
import json
import logging
from tkinter import font as tkFont
from tkinter import ttk, filedialog
from tkinter import messagebox as tkmsg
import time
from superpresenter.paths import PROJECT_ROOT
from superpresenter.version import VERSION
from pathlib import Path
from superpresenter.services.projection_config import ConfigError, load_styles, default_monitor
from superpresenter.ui.projection_profiles import ProjectionProfiles
from superpresenter.services.song_edit_session import validate_editor_fields
from superpresenter.services.construct_parser import ConstructError
from superpresenter.services.stationary_navigation import CueNavigation, build_plan, style_mode
from superpresenter.services.presentation_session import WidgetSource
from superpresenter.ui.source_sorter import SortingWin
from superpresenter.ui.projector_window import ProjWindow
from superpresenter.ui.song_editor_panel import SongEditorPanel

logger = logging.getLogger(__name__)


def doNothing(*e):
    pass


class GUI(ProjectionProfiles, SongEditorPanel):
    def __init__(self):
        self.title = 'SuperPresenter ' + VERSION
        self.dir = PROJECT_ROOT
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
        self.win.report_callback_exception = self._report_callback_exception
        self.initWins()
        try:
            self.setStyle()
        except:
            logger.exception('GUI style loading failed')
            tkmsg.showerror('Error loading styles',
                'Unknown error occured while loading GUI styles\n'+\
                    'Check "gui_styles.json" file.')
        self.placeWidgets()

        self.getMonitors()
        self.getProjectorStyles()

        self.newProjector()
        self.init_profiles()

        self.assign()
        self.start_monitor_watch()

        self.draft_open = False

    def _report_callback_exception(self, exc_type, exc, traceback):
        logger.error('UI callback failed', exc_info=(exc_type, exc, traceback))
        try:
            if self.runState:
                self.runState = False
                self._cleanup_after_stop()
        finally:
            # Preserve Tk's existing error reporting; do not introduce a dialog.
            tk.Tk.report_callback_exception(self.win, exc_type, exc, traceback)

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
        self.addLangBtn.config(style['projButton'], width=18)

        ### source
        ## navigation
        self.sourceNum.config(style['stepsLabel'])
        self.prevSource.config(style['projButton'])
        self.nextSource.config(style['projButton'])
        self.openSource.config(style['projButton'])
        self.closeSource.config(style['projButton'])
        self.newSource.config(style['projButton'])
        self.changeOrder.config(style['projButton'], width=8)
        self.openPresentation.config(style['projButton'], width=5)
        self.sourceLab.config(style['sourcesLabel'])
        self.dirtyLabel.config(style['sourcesLabel'], width=2)
        try:
            lab_bg   = self.sourceLab.cget("background")
            lab_fg   = self.sourceLab.cget("foreground")
            lab_font = self.sourceLab.cget("font")
        except tk.TclError:
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
        self.stepsXScroll = tk.Scrollbar(self.stepsFrame, orient='horizontal', command=self.stepsList.xview)
        self.stepsList['xscrollcommand'] = self.stepsXScroll.set
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
        self.saveProjs = tk.Button(self.projNav, text='edit')
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
        self.openPresentation = tk.Button(self.sourceNav, text='prez')
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
        self.addSlokaBtn, self.addRefrenBtn, self.addBridgeBtn = self.song_editor_widget.section_buttons
        self.addLangBtn = tk.Button(self.variants, text="Přidat variantu", command=self.song_editor_widget.open_language_dialog)
        self.dirtyLabel = tk.Label(self.sourceNav, text='')
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
        self.stepsXScroll.grid(column=0, row=2, sticky='ew')
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

        self.explainLabel = self.song_editor_widget.explain_label
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
        self.dirtyLabel.grid(column=8, row=2, sticky='w')
        # variants
        self.var1Lab.grid(column=0, row=0, padx=10, pady= 3)
        self.var2Lab.grid(column=0, row=1, padx=10, pady= 3)
        self.var3Lab.grid(column=0, row=2, padx=10, pady= 3)
        self.var1Combo.grid(column=1, row=0, padx=4, pady= 3)
        self.var2Combo.grid(column=1, row=1, padx=4, pady= 3)
        self.var3Combo.grid(column=1, row=2, padx=4, pady= 3)

        self.addLangBtn.grid(column=2, row=1, padx=(20, 4))

    def on_closing(self):
        if not self._prepare_song_transition():
            return
        # Zavřít editor prezentací, pokud běží
        if hasattr(self, "presentation_editor_win"):
            if self.presentation_editor_win.poll() is None:
                self.presentation_editor_win.terminate()

        self.stop_monitor_watch()
        if self.runState:
            self.runState = False
            self._cleanup_after_stop()
        self.persist_layout(explicit=False)
        self.win.destroy()

    def assign(self):
        # projectors options
        self.openProjs.configure(command=self.runButtFun)
        self.addProj.configure(command=self.newProjector)
        self.delProj.configure(command=self.delProjector)
        self.nextProj.configure(command=self.nextProjector)
        self.prevProj.configure(command=self.prevProjector)
        #sources options
        self.openSource.configure(command=self.openSongSearch)
        self.prevSource.configure(command=self.prevSourceFun)
        self.nextSource.configure(command=self.nextSourceFun)
        self.closeSource.configure(command=self.closeSourceFun)
        self.newSource.configure(command=self.newSongFun)
        self.changeOrder.configure(command=self.sortSources)
        self.openPresentation.configure(command=self.openPresentationEditor)


        self.saveProjs.configure(command=self.edit_profiles)
        self.loadProjs.configure(command=self.load_profile)
        # self.changeOrder.configure(state='disabled')
        self.repExp.configure(state='disabled')
        self.repImp.configure(state='disabled')

        self.stepsList.bind('<<ListboxSelect>>',self.stepSelect)
        self.stepsList.bind('<Button-1>', self._stationary_click)
        self.chooseProj.configure(postcommand=self.refresh_monitor_choices)
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










    def run(self):
        tk.mainloop()


    def openPresentationEditor(self):
        import subprocess
        from superpresenter.processes import tool_command
        if hasattr(self, "presentation_editor_win") and self.presentation_editor_win.poll() is None:
            return  # Prezentace už běží
        self.presentation_editor_win = subprocess.Popen(
            tool_command('presentation_presenter.py'), cwd=self.dir)

    def getProjectorStyles(self):
        try:
            data = load_styles(Path(self.dir) / 'projectors_styles.json', self.dir)
        except ConfigError as exc:
            tkmsg.showerror('Chyba projekčních stylů', str(exc))
            self.win.destroy()
            raise
        self.animationParams = data['animation']
        self.projStyles = data['styles']
        self.chooseStyle['values'] = [style['name'] for style in self.projStyles]

    # projectors options
    def newProjector(self,*e):
        l = len(self.projectors)
        if l < 5:
            new_proj = ProjWindow(self)

            new_proj.monitor = default_monitor(self.monitors)

            self.projectors.append(new_proj)
            self.projectorID = l
            self.openProjector()
            self.persist_layout()

    def openProjector(self):
        if not self.projectors:
            self.projsLabel.configure(text='0 / 0')
            self.chooseProj.set('')
            self.chooseStyle.set('')
            self.fullscreenCheck.deselect()
            self.collectionCheck.deselect()
            return
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
            self.persist_layout()

    def changeProjector(self, *e):
        if self.projectorID >=0:
            self.projectors[self.projectorID].monitor = \
                self.chooseProj.current()
            self.projectors[self.projectorID].winPlacement = ''
            self.projectors[self.projectorID].window_position = None
            self.persist_layout()

    def changeFullscreen(self, *e):
        if self.projectorID >= 0:
            proj = self.projectors[self.projectorID]
            fullscreen = self.fullscreenState.get()
            if self.runState and hasattr(proj, 'win'):
                mon = self.monitors[proj.monitor]
                if fullscreen and not proj.fullscreen:
                    proj.windowed_geometry = proj.win.geometry()
                proj.win.overrideredirect(fullscreen)
                if fullscreen:
                    proj.win.geometry(f'{mon.width}x{mon.height}{mon.x:+d}{mon.y:+d}')
                else:
                    geometry = getattr(proj, 'windowed_geometry', None)
                    if geometry is None:
                        geometry = f'{int(mon.width * 0.8)}x{int(mon.height * 0.8)}{mon.x:+d}{mon.y:+d}'
                    proj.win.geometry(geometry)
            proj.fullscreen = fullscreen
            self.persist_layout()
    def delProjector(self, *e):
        l = len(self.projectors)
        if l > 1:
            self.projectors.pop(self.projectorID)
            self.projectorID = min(self.projectorID, l - 2)
            self.openProjector()
            self.persist_layout()

    def nextProjector(self, *e):
        if self.projectorID < len(self.projectors)-1:
            self.projectorID += 1
            self.openProjector()

    def prevProjector(self, *e):
        if self.projectorID > 0:
            self.projectorID -= 1
            self.openProjector()

    # source options
    def openSongSearch(self):
        from superpresenter.ui.song_search_window import SongSearchWindow
        window = getattr(self, '_song_search_window', None)
        if window is not None and window.win.winfo_exists():
            window.win.lift()
            window.entry.focus_set()
            return
        self._song_search_window = SongSearchWindow(self)

    def addSource(self, *e):
        paths = filedialog.askopenfilenames(title='Otevřít píseň', initialdir=os.path.join(self.dir, "songs"),
            filetypes=(('Textové soubory', ('*.xml', '*.txt')), ('Všechny soubory', ('*.*'))))
        for path in paths:
            if not self.loadSource(path):
                break

    def loadSource(self, path):
        src = WidgetSource(path)
        if src.err:
            logger.error('Source loading failed: %s: %s', path, src.load_warning)
            tkmsg.showerror('Chyba načítání', f'Nelze načíst {path}:\n{src.load_warning or "Soubor není dostupný."}')
            return False
        try:
            validate_editor_fields(src.song)
        except ValueError as exc:
            logger.exception('Invalid song: %s', path)
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
            self._update_song_caption()
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
        if not self.runState and not self.projectors:
            tkmsg.showinfo('Promítání', 'Není zapnutý žádný výstup. Vyberte styl v editoru monitorů (edit).')
            return
        if not self.runState and not self._prepare_song_transition():
            return
        if not self.runState and getattr(self, '_profiles_ready', False):
            if not self.restore_profile(None, data=self.layout_snapshot()):
                return
        # Tlačítko dočasně vypnout – ale VŽDY ho na konci znovu povolit
        self.openProjs.configure(state='disabled')
        try:
            self.runState = not self.runState

            if self.runState:
                # --- START PREZENTACE ---
                self.openProjs.config(self.onStyle)
                self.win.bind('<Escape>', self.runButtFun)

                self._lock_editing()

                # 1. Načti typy zdrojů podle stylů
                try:
                    types = self.getSourceTypes()
                except Exception:
                    logger.exception('Projector style loading failed')
                    tkmsg.showerror('Error in projector styles',
                                    'Error occurred while loading styles for projectors\n'
                                    'Check "projectors_styles.json"')
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
                        logger.exception('Source construction failed: %s', src.path)
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
                        logger.exception('Projector startup failed')
                        tkmsg.showerror('Error in projector styles',
                            f'Error occurred while constructing "{self.projStyles[proj.style]["name"]}"\n'
                            'Check "projectors_styles.json"\n\n' + str(e))
                        self.runState = False
                        self._cleanup_after_stop()
                        return

                self.previewSlide()

            else:
                # --- STOP PREZENTACE ---
                self._cleanup_after_stop()

        except Exception:
            logger.exception('Presentation state change failed')
            self.runState = False
            self._cleanup_after_stop()
            raise
        finally:
            # VŽDY povolit tlačítko zpět, i když kód spadne
            self.openProjs.configure(state='normal')

    def _display_construct_error(self, slide_name, err):
        """Pomocná metoda pro zobrazení chyb v konstruktu"""
        logger.error('Invalid construct in %s: %s', slide_name, err)
        tkmsg.showerror('Error constructing text',
                        f'Error in source "{slide_name}"\n'
                        'Check construct input.\n' + str(err))

    def _lock_editing(self):
        """Remember exact states, including readonly and already disabled controls."""
        if getattr(self, '_editing_states', None) is not None:
            return
        self._editing_states = []

        def lock(widget):
            if 'state' in widget.keys():
                self._editing_states.append((widget, str(widget.cget('state'))))
                widget.configure(state='disabled')
            for child in widget.winfo_children():
                lock(child)
        for widget in (self.projNav, self.projSet):
            lock(widget)
        # Only projection settings are frozen; song edits target the next run.
        editor = getattr(self, '_projection_editor', None)
        if editor is not None and editor.win.winfo_exists():
            lock(editor.win)

    def _unlock_editing(self):

        for widget, state in getattr(self, '_editing_states', None) or ():
            if widget.winfo_exists():
                widget.configure(state=state)
        self._editing_states = None

    def _cleanup_after_stop(self):
        timer = getattr(self, '_animation_timer', None)
        if timer is not None:
            self.win.after_cancel(timer)
            self._animation_timer = None
        self.openProjs.config(self.offStyle)
        self.win.bind('<Escape>', doNothing)

        self._unlock_editing()

        self.stepsList.delete(0, 'end')
        self.stepsLabel.configure(text='0 / 0')
        self.slideLabel.configure(text='0 / 0')

        # zavři okna projektorů
        for proj in self.projectors:
            try:
                proj.stopProjection()
            except Exception:
                logger.exception('Projector shutdown failed')
        self.persist_layout(explicit=False)

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

        # These are Listbox row indices, not compressed pair/page indices.
        self.noOfSteps = len(src.lines.get('longsteps', [])) + 1

        # 6) naplň náhled
        self.stepsList.insert('end','-----')
        for line in src.lines['long'][self.prevVars[self.runningSlide][0]]:
            self.stepsList.insert('end', line)
        self.stepsList.insert('end','-----')
        self.stepsList.selection_set(self.currentStep)
        self.stepUpdate()

    def stepsLangUpdate(self, *e):
        if not self.runState or not self.onlineSources:
            return
        self.prevVars[self.runningSlide][0] = self.stepsLang.current()
        self.loadSteps()

    def stepUpdate(self):
        self.stepsList.xview_moveto(0)
        if getattr(self, 'stationary_active', False):
            nav = self.stationary_navigation
            total = max(0, nav.last_step - 1)
            current = nav.step
            end = bool(nav.plans) and current == nav.last_step
        else:
            current = self.currentStep
            end = current > 0 and current >= self.noOfSteps
            if getattr(self, 'pair2_active', False):
                total = len(self.pair2_map)
                pair = self._pair_index_for_list_index(current)
                current = pair + 1 if current > 0 and pair is not None else 0
            elif getattr(self, 'paged_active', False):
                total = len(self.paged_starts)
                current = sum(start < current for start in self.paged_starts) if current else 0
            else:
                total = max(0, self.noOfSteps - 1)
        self.stepsLabel.configure(text='Konec' if end else f'{current} / {total}')

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
            self._animation_timer = self.win.after(self.animationParams['dt'], self.animmator)

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
            logger.info('[stationary] %s', nav.diagnostic())

    def _legacy_step_indices(self):
        # Shared indices for immediate and animated legacy updates.
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

        return send_idx

    def _update_projectors(self, anim=1):
        indices = self._legacy_step_indices()
        for proj in self.projectors:
            proj.switch(indices, anim)

    def animmator(self):
        self._animation_timer = None
        if self.animation != 1:
            return
        stillanimated = []
        send_idx = self._legacy_step_indices()

        for idx in self.animated:
            a = self.projectors[idx].switch(send_idx, 1)
            if a:
                stillanimated.append(idx)
        if not stillanimated:
            self.animation = 0
            return
        self.animated = stillanimated
        self._animation_timer = self.win.after(self.animationParams['dt'], self.animmator)

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
            self.stationary_navigation.move(-1, restart_previous_section=True)
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
            self.persist_layout()

            # je-li okno/Canvas už otevřený, zkus rovnou přepnout
            try:
                proj.set_collection_visible(show)
            except Exception:
                # okno zatím neběží → nic, stav je uložený a promítne se při startu
                pass
