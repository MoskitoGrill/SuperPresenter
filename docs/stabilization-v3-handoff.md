# Stabilizace SuperPresenter 3.0.0 — plán a předávání

## Rozsah a pravidla pro všechny etapy

Cíl: uzavřít stabilní verzi 3.0.0 bez nových funkcí a bez velkých refaktorů.
`presentation_presenter.py` je mimo rozsah; kontrolovat pouze jeho případný
dopad na zavírání a běh hlavní aplikace. Neměnit číslo verze.

Na začátku každého chatu přečíst tento soubor, případné AGENTS.md a aktuální
git status/diff. Ověřit skutečný stav kódu; audit níže je výchozí hypotéza,
nikoli náhrada kontroly. Zachovat cizí a uživatelské změny.
Etapy provádět postupně ve stejném checkoutu. Nespouštět současně více chatů,
které upravují tyto soubory. Automaticky necommitovat ani nepublikovat.

Každá etapa smí doplnit cílené regresní testy a opravy nutné k dokončení
svého rozsahu. Pokud je navržená změna zbytečná nebo rizikovější než původní
stav, zdokumentovat důvod a použít menší řešení. Neopravovat testy pouhým
odstraněním kontrol. Nezatěžovat GUI ani paměť skutečně obrovským vstupem:
hranice ověřovat bezpečnými testy.

Na konci aktualizovat stav etapy a předávací záznam v tomto souboru.
Uvést přesné příkazy, výsledky, změněné soubory, zbývající problémy a další krok.
Neoznačit etapu za hotovou, pokud její povinné ověření neproběhlo; uvést omezení.

## Výchozí audit (8. 10. 2026)

- Celá sada: 290 testů, čtyři selhání kompatibility konstruktu `@r1`
  v písni `k_panu_ruce_pozvedam.xml`. Pravděpodobně zastaralé očekávání starého
  parseru; před úpravou testů potvrdit zamýšlenou sémantiku.
- Opakované Tcl/Tk hlášení `invalid command name ..._fit_visible_card`.
  `projection_editor.py` plánuje callbacky přes `after`, při zavření je neruší.
- Konstrukty nemají praktický limit výsledných řádků/kroků; velká opakování,
  jejich vnoření a rozsahy mohou zahltit synchronní sestavování prezentace.
- Odebrání písně mění `sourceList`, ale zanechává objekty v `sources`.
- Globální obsluha chyby GUI při aktivní projekci zastaví všechny výstupy.
  Nutné posoudit bezpečnost oddělení chyb editorů od projekčního běhu.
- Prověřit zavírání obrázků, prostředků projektorů a časování přes `time.time`.
- Hledání: index 858 písní přibližně 1,06 s, dotazy přibližně 2–92 ms
  bez vykreslení. Vykreslování pro každý výsledek znovu kontroluje cesty playlistu.
- Validátor: 859 souborů, jedna chyba názvu (`songs/.xml`), 76 varování.
  Varování o konstruktech nejsou automaticky vadná data. Uživatelské písně
  nemažte ani obsahově neopravujte bez opory v datech nebo zadání.
- Audit zdrojů není potvrzení stability distribuovaného EXE ani dlouhého běhu.

## Etapa 1 — ochrana před zahlcením konstruktem

Stav: hotovo (8. 10. 2026). Cílené ověření dokončeno; známé čtyři
kompatibilitní nálezy `@r1` zůstávají pro etapu 4.

Zkontrolovat celý řetězec parser → legacy konstrukce → stacionární plán.
Zvolit a zdůvodnit rozumné limity; chránit celkovou expanzi, nejen jednotlivý
násobitel. Zahrnout vnořená opakování, rozsahy, délku/vnoření vstupu podle
skutečných rizik. Kontrolu provést před velkou alokací a dlouhým průchodem.
Chyba má být srozumitelná a nesmí zanechat otevřené projektory nebo zamčené UI.
Zachovat běžné konstrukty, připínání `@` a platnou legacy sémantiku.

Ověření: hranice limitu, jejich překročení, vnoření, rozsahy, běžné konstrukty,
oba režimy sestavování a návrat do použitelného stavu po odmítnutí vstupu.
Předat konkrétní limity a místo jejich vynucení.

## Etapa 2 — životní cyklus oken a prostředků

Stav: hotovo (9. 10. 2026). Povinné ověření životního cyklu dokončeno,
77 testů OK bez Tcl/Tk chyb. Širší sada má nestabilní nález kolečka editoru;
podrobnosti a srovnávací běhy jsou v předání níže.

Opravit vlastnictví a rušení callbacků `_fit_visible_card` ve všech místech
plánování. Prověřit další časovače při zavření hlavního okna a podoken.
Prověřit opakované start/stop, částečně neúspěšný start, obrázky a reference
na zničené projektory. Zajistit explicitní zavírání obrázkových souborů tam,
kde chybí. Vyřešit ponechávání odstraněných písní v paměti bez narušení indexů,
duplicit playlistu, editoru, řazení a snímku probíhající projekce.

Ověření: zavření s čekajícím callbackem, opakované otevření/zavření, start/stop,
selhání startu a přidávání/odebírání písní. Testy nesmí zanechávat Tcl/Tk chyby.
Předat změny ve vlastnictví zdrojů a případné zbývající úniky.

## Etapa 3 — obsluha chyb a drobná optimalizace

Stav: hotovo (9. 10. 2026). Hranice chyb, monotónní intervaly a hledání
ověřeny společnou sadou 82 testů OK bez Tcl/Tk chyb; metodika měření níže.

Posoudit `_report_callback_exception` a hranice jednotlivých operací.
Bezpečně izolovat chyby pomocných editorů, pokud jejich stav neohrožuje projekci;
při chybě projekce zachovat spolehlivý úklid. Nezavést pokračování s poškozeným
sdíleným stavem ani tiché polykání výjimek. Zvážit cílené zachytávání u operací
místo oslabení globální pojistky. Zachovat diagnostiku.
Převést časové intervaly animací na monotónní hodiny a přizpůsobit relevantní
testy. Ve výsledcích hledání předpočítat cesty playlistu pro jeden refresh;
nezavádět nový systém cache ani nové ovládání. Změřit přiměřený dopad.

Ověření: chyba pomocné operace během promítání, chyba projekčního běhu,
obnovení ovládání, animace a hledání s duplicitami/změnami playlistu.
Předat rozhodnutí o hranicích chyb a srovnání výkonu s metodikou měření.

## Etapa 4 — regresní uzavření zdrojové verze

Stav: hotovo (9. 10. 2026). Celá sada 305 testů OK, validátor dokončen,
omezený provozní test 40 cyklů OK. Zdrojová verze připravena k sestavení;
datový nález prázdného názvu v `songs/.xml` zůstává odděleně. Distribuce
a dlouhý provoz na skutečném projektoru čekají na etapu 5.

Ověřit zamýšlenou sémantiku `@r1`; upravit zastaralé databázové kompatibilitní
testy pouze pro úmyslné rozšíření syntaxe. Zachovat kontrolu původního chování
a přidat explicitní kontrolu nového chování. Prověřit `songs/.xml` a ostatní
diagnostiku bez automatického mazání uživatelských dat; případný nevyřešený
datový problém uvést odděleně od chyb aplikace.
Spustit celou testovací sadu a validátor. Provést omezený opakovaný provozní
test zdrojů; sledovat nečekané výjimky, časovače a růst paměti. Opravovat jen
regrese a stabilitu; větší nově nalezenou práci jasně předat.

Ověření: přesný souhrn všech testů, očekávaných diagnostických výpisů,
datových nálezů a zbývajících omezení. Úspěch unittest sám o sobě neznamená
absenci Tcl/Tk chyb na stderr. Výsledný diff zkontrolovat vůči rozsahu.
Předat verdikt připravenosti k sestavení a seznam kontrol pro distribuci.

## Etapa 5 — sestavení a ověření finální distribuce

Stav: částečně (9. 10. 2026). Nová distribuce 3.0.0 sestavena a dostupné
automatické kontroly EXE i přenosu prošly. Fyzický projektor, hotplug,
čtyřhodinový provoz a uživatelské kontroly čekají; verze není finálně ověřena.
Přesný scénář: `docs/stage5-hardware-scenario.md`. Artefakt a výsledky níže.

Přečíst `docs/windows-release.md`, `docs/release-v3-verification.md`
a sestavovací skripty. Sestavit nový artefakt 3.0.0 do nové složky;
nepřepisovat předchozí distribuci. Zaznamenat prostředí, příkazy, revizi nebo
stav změn a přesnou cestu artefaktu. Před testováním chránit reálná uživatelská
data; použít izolovaná testovací data/config podporovaným způsobem.
Ověřit EXE mimo pracovní adresář projektu, styly a prostředky, start/stop,
rychlé přepínání, editaci během projekce, zavírání a odmítnutí chybných vstupů.

S reálným projektorem a součinností uživatele ověřit odpojení/připojení monitoru
a několikahodinový provoz. Sledovat paměť, odezvu a logy. Pokud hardware nebo
čas nejsou dostupné, připravit přesný ruční scénář a označit ověření jako
čekající; nenahrazovat ho tvrzením, že vše prošlo.

Verzi označit za finálně ověřenou teprve po splnění dostupných automatických
i požadovaných reálných kontrol. Předat cestu ZIP/EXE, výsledky a zbývající
omezení. Nepublikovat ani instalovat do produkčního umístění bez zadání.

## Předávací záznamy

Každý chat připojí záznam v tomto tvaru a aktualizuje stav příslušné etapy:

### Etapa N — datum

- Stav: hotovo / částečně / blokováno konkrétní podmínkou.
- Výchozí stav checkoutu a relevantní uživatelské změny:
- Provedené změny a důvody:
- Změněné soubory:
- Ověření: přesné příkazy, počty testů, výsledky, stderr/logy:
- Neprovedené kontroly a důvod:
- Zbývající rizika a nálezy mimo rozsah:
- Pro další chat: co přečíst, na co navázat, co neopakovat:
- Commit/revize, pokud existuje; jinak výslovně necommitováno:

### Etapa 1 — 8. 10. 2026

- Stav: hotovo.
- Výchozí checkout: jediný netrackovaný soubor `docs/stabilization-v3-handoff.md`,
  žádný tracked diff. AGENTS.md v projektu nenalezen. Předávací dokument zachován.
- Limity: 16 384 znaků vstupu, 32 úrovní závorek, 4 096 rozbalených
  řádků/kroků na píseň. Rozpočet řádků je společný pro vybrané jazyky.
  Jsou výrazně nad běžnou písní, ale omezují synchronní práci i seznamy
  rendererů. Nejde o limit celého playlistu ani velikosti XML/textových souborů.
- Vynucení: `parse_construct` kontroluje délku, hloubku a strukturální expanzi;
  `check_expansion` počítá každý mezivýsledek stromu včetně rozsahů, vnořeného
  násobení a prázdných skupin. Kontroluje i potomky skupiny s násobitelem 0,
  protože legacy renderer je nejprve sestaví. Neomezuje pouze jeden násobitel.
  `constructLines` kontroluje skutečné délky před `_build_group_lengths`,
  `longText` a `shortText`; pro celé sekce používá konzervativně nejdelší
  jazyk × počet jazyků kvůli paddingu. `build_plan` kontroluje součet jazyků
  před materializací `resolve_sections`; samotný resolver rovněž kontroluje
  délky před expanzí. Rozsahy se počítají včetně neexistujících prázdných řádků.
- `ConstructLimitError` zachovává pozici a srozumitelnou českou zprávu.
  GUI nově hlásí i chyby konstruktu při sestavování jako chybu vstupu a provede
  existující úklid před otevřením projektorů. Běžná syntaxe, `@`, legacy
  pořadí a navigace se nemění. Původní testy velkého násobitele/hloubky nyní
  ověřují bezpečnou hranici, nové testy explicitně ověřují její překročení.
- Změněné soubory: `superpresenter/services/construct_parser.py`,
  `presentation_session.py`, `stationary_navigation.py`, `stationary_pages.py`
  (v témže adresáři services), `superpresenter/ui/main_window.py`,
  `tests/test_construct_parser.py`, nový `tests/test_construct_limits.py`,
  tento dokument a diagnostický `stage1-tests.log`.
- Ověření (PowerShell, projektový Python; spuštění vyžadovalo povolení mimo
  sandbox, protože Windows Store runtime nebyl přístupný):
  - `.venv/Scripts/python.exe -m unittest discover -s tests -p test_construct_limits.py -v`
    — finální běh 3 testy, OK. Hranice délky/hloubky/expanze, vnoření,
    rozsahy, nulové/prázdné skupiny, více jazyků, oba buildry (long/short/short2
    i stacionární plán), odmítnutí před expanzí, GUI v legacy a stacionárním
    režimu: runState false, odemčené ovládání, žádná okna projektorů a úspěšný
    následný start/stop s `v1 @v1.1`. Test GUI dosazuje konstrukty do snapshotů
    zdrojů a obchází potvrzení neuložené editace, pracuje s izolovanými daty.
  - `$env:PYTHONPATH='tests'; .venv/Scripts/python.exe -m unittest test_construct_parser test_construct_limits test_pinned_lines test_stationary_pages test_stationary_navigation -v > stage1-tests.log 2>&1`
    — 61 testů, 4 známá selhání (1 test a 3 subtesty) pro `@r1` v
    `k_panu_ruce_pozvedam.xml`; ostatní kontroly prošly, žádné nové selhání.
    Log obsahuje čtyři očekávaná hlášení odmítnutého konstruktu, žádné
    `invalid command name` ani Tcl/Tk výjimky. Dřívější neúspěšné pokusy
    odhalily chyby testovacích očekávání; opraveny bez oslabení kontroly.
  - `git diff --check` — OK, pouze upozornění Git na převod LF → CRLF.
- Neprovedeno: celá sada/validátor (etapa 4), EXE a skutečný projektor
  (etapa 5), dlouhý provoz. Obrovské vstupy se v GUI nerozbalovaly.
- Zbývající rizika mimo rozsah: velký playlist a velikost samotných textových
  dat nejsou touto ochranou omezeny; callbacky editoru a další nálezy auditu
  zůstávají. Čtyři známá selhání kompatibility nebyla změněna.
- Pro další chat: přečíst tento dokument, status/diff; pokračovat etapou 2.
  Limity a regresní testy zachovat, nepřepisovat `@r1` kompatibilitní očekávání
  před etapou 4. `presentation_presenter.py`, číslo verze a uživatelské písně
  nebyly změněny.
- Necommitováno, nic nepublikováno.

### Etapa 2 — 9. 10. 2026

- Stav: hotovo v rozsahu životního cyklu. Širší regresní sada není plně zelená;
  jeden nestabilní test kolečka je výslovně předán do etapy 4.
- Výchozí checkout: HEAD `00b24e8`, necommitované změny etapy 1 v šesti
  tracked souborech a netrackované předání, `stage1-tests.log`,
  `tests/test_construct_limits.py`. Status a diff ověřeny proti předání;
  AGENTS.md v projektu nenalezen. Všechny změny etapy 1 zachovány.
- Časovače: všechna tři plánování `_fit_visible_card` používají jeden
  vlastněný `_fit_timer`, další požadavek ruší předchozí. Callback i přímé
  volání uklidí ID; Destroy ruší čekající práci a uvolňuje referenci ownera
  na editor. Sorter vlastní `_drag_timer`, ruší jej při puštění i zničení.
  Opakované otevření řazení zvedá existující okno místo vytváření osiřelých
  oken. FloatingControls a QR editor ruší časovače i při přímém zničení
  nebo zničení rodiče. Hlavní okno při Destroy ruší monitorový a animační
  časovač; běžné zavření navíc explicitně zavře editor monitorů.
  SongEditor nyní vlastní a ruší i úvodní `after_idle` nabídku obnovy.
  Debounce/poll hledání a průběžná záloha již měly Destroy úklid.
- Projektory: `stopProjection` je opakovatelný a uklízí i částečně sestavený
  nebo již zničený výstup. Zachovává polohu okna, odstraňuje `win`/`canvas`,
  vyprazdňuje renderery a animační seznamy, uvolňuje PhotoImage a zavírá
  `_collection_source`. Renderery po stopu přestávají držet texty/plány.
  Konfigurační objekt ProjWindow zůstává pro další start; jeho běhové
  prostředky se pokaždé vytvářejí znovu.
- Obrázky: `Widget_Image` a legacy overlay používají `with Image.open`
  i pro chybu při resize/PhotoImage; dočasné resizované/renderované obrázky
  mají explicitní close. QR editor zavírá nahrazovaný obrázek i obrázek
  při zničení a uvolňuje náhled/cache. Při výměně/resetu invaliduje cache,
  aby PIL neporovnával již zavřený obrázek. Ostatní otevírání obrázkových
  souborů už mělo context manager.
- Playlist: po odebrání položky se `sources` zkompaktuje podle skutečně
  používaných indexů a `sourceList` se přemapuje včetně duplicit. Píseň se
  uvolní až po odstranění posledního výskytu jejího indexu. Otevřený sorter
  odstraní odpovídající výskyt, přemapuje draft a přeruší drag; prázdné
  řazení zavře. Zachová se vybraná položka, editor naváže na zbývající píseň
  nebo prázdný draft. `onlineSources` a stacionární plán mají nezávislé
  snímky a odebrání je nemění. Uložení editoru a hledání dále pracují
  s platnými kompaktními indexy; index písní na disku není dotčen.
- Změněné soubory této etapy: `song_editor.py`,
  `superpresenter/ui/main_window.py`, `projection_editor.py`,
  `source_sorter.py`, `floating_controls.py`, `collection_qr_editor.py`,
  `projector_window.py`, `projector_widgets.py` (všechny poslední soubory
  pod `superpresenter/ui`), nový `tests/test_window_lifecycle.py`,
  `tests/test_projection_editor.py`, `tests/test_editor_rendering.py`,
  tento dokument, `stage2-wheel-baseline.py` a diagnostické
  `stage2-tests.log`, `stage2-lifecycle-tests.log`, `stage2-wheel-*.log`.
  Sledovaný bytecode `__pycache__/song_editor.cpython-313.pyc` přegenerovaný
  prvním během byl obnoven z HEAD; další běhy používají `-B`.
- Ověření (PowerShell, projektový Python 3.13; runtime Windows Store
  vyžaduje spuštění mimo sandbox):
  - `.venv/Scripts/python.exe -m unittest discover -s tests -p test_release_stability.py -v > stage2-tests.log 2>&1`
    — první kontrola 15 testů OK (log později nahrazen širší sadou).
  - `$env:PYTHONPATH='tests'; .venv/Scripts/python.exe -B -m unittest test_window_lifecycle test_projection_editor test_release_stability test_construct_limits test_song_editor_integration test_collection_qr test_song_search_window test_editor_rendering -v > stage2-tests.log 2>&1`
    — finální širší běh 106 testů za 32,077 s: 105 OK, 1 FAIL
    `test_wheel_over_expanding_verse_scrolls_editor`, žádné ERROR.
    Žádné `invalid command name` ani TclError. Log obsahuje očekávané
    diagnostiky testů odmítnutého konstruktu, neúspěšného ukládání,
    načtení neexistujícího souboru a selhání callbacku uložení.
  - `$env:PYTHONPATH='tests'; .venv/Scripts/python.exe -B -m unittest test_window_lifecycle test_projection_editor test_release_stability test_construct_limits test_collection_qr test_song_search_window test_editor_rendering -v > stage2-lifecycle-tests.log 2>&1`
    — 77 testů za 24,297 s, všechny OK. Čekající callbacky, slučování
    požadavků, opakované otevření/zavření, Destroy rodiče, obnovovací idle,
    monitorový/animační timer, všechny dodávané styly, opakované start/stop,
    slabé reference rendererů, částečné selhání druhého projektoru a následný
    úspěšný start, zavření souborů i při chybě PhotoImage, odebrání s duplicitami,
    sorterem a běžícím snímkem, opakované přidávání/odebírání, integrace hledání,
    QR a limity etapy 1. Testy odchytávají Tcl `bgerror` i Python callbackové
    výjimky; žádné nečekané callbacky, Tcl/Tk chyby ani `invalid command name`
    v logu. Test explicitního close QR zachoval původní kontrolu after_cancel
    a přidal kontrolu zavření obrázku.
  - `.venv/Scripts/python.exe -B stage2-wheel-baseline.py > stage2-wheel-baseline.log 2>&1`
    — 3/3 OK s původním `song_editor.py` načteným z HEAD do paměti,
    bez změny checkoutu.
  - `.venv/Scripts/python.exe -B stage2-wheel-baseline.py current > stage2-wheel-current.log 2>&1`
    — 3/3 OK s aktuálním editorem. Samostatný dřívější unittest běh
    jednoho testu selhal (`stage2-wheel-check.log`), diagnostický běh
    s výpisem cíle `winfo_containing` prošel (`stage2-wheel-diagnostic.log`).
    Tedy závislost na prostředí/pořadí je podezření, nikoli prokázaná příčina;
    test ani obsluhu kolečka tato etapa nemění a širší FAIL není skryt.
  - `git diff --check` — OK, pouze obvyklá upozornění LF → CRLF.
- Při iteraci byly opraveny skutečná chyba cache zavřeného QR obrázku
  a testovací předpoklady (absolutní cesta místo validované relativní,
  úklid již zničeného kořene, sentinel bez metody close). Neúspěšné
  meziběhy nenahrazují výše uvedené finální výsledky.
- Neprovedeno: celá sada/validátor a sledování dlouhodobého RSS (etapa 4),
  EXE/skutečný projektor a několikahodinový provoz (etapa 5). Slabé reference
  potvrzují uvolnění konkrétních objektů; nejsou měřením celé procesové paměti.
- Zbývající rizika: nestabilní test kolečka ověřit při regresním uzavření
  včetně hit-testu, geometrie a překrytí oken. Čtyři známé kompatibilitní
  nálezy `@r1` zůstávají pro etapu 4. Žádný další trvalý únik v ověřovaném
  cyklu nebyl potvrzen; allocator/PIL/Tk cache a doběh workeru hledání
  po `shutdown(wait=False)` nejsou důkazem uvolnění veškerého RSS.
- Pro další chat: přečíst toto předání a aktuální diff; pokračovat etapou 3
  (hranice chyb, monotónní intervaly, cesty playlistu při refresh hledání).
  Zachovat vlastnictví timerů, kompaktní indexy a nezávislý projekční snímek.
  Nepřepisovat kompatibilitu `@r1` před etapou 4. Neopakovat diagnostické
  meziběhy bez nového důvodu. `presentation_presenter.py`, číslo verze
  a uživatelské písně nebyly změněny.
- Necommitováno (HEAD `00b24e8`), nic nepublikováno.

### Etapa 3 — 9. 10. 2026

- Stav: hotovo v rozsahu obsluhy chyb a drobné optimalizace.
- Výchozí checkout: HEAD `00b24e8`, 15 změněných tracked souborů a
  netrackované testy/logy/předání etap 1–2. Status a relevantní diff přečteny,
  AGENTS.md v projektu nenalezen. Předchozí změny zachovány.
- Hranice chyb: `_report_callback_exception` zůstává beze změny včetně
  logování, úklidu všech výstupů při běhu a původní diagnostiky Tk.
  Výjimku nelze bezpečně klasifikovat podle okna nebo tracebacku; neznámý
  callback může již změnit sdílený stav. Editor monitorů je za běhu blokován
  (ověřuje existující test), proto se jeho callbacky obecně neizolují.
  Hledání/indexace jsou čtecí pomocné operace, jejich existující lokální
  logování a zprávy zůstávají. Po chybě refresh se nově odstraní výsledky
  i částečné řádky a zakáže Přidat, aby starý výběr nepřidal jinou píseň.
  Další refresh obnoví použitelnost bez zásahu do projekčního snímku.
  Neočekávané chyby `add_result`/`gui.addSource` už nejsou v hledacím okně
  polykány: mění sdílený playlist a musí dosáhnout globální pojistky.
  Běžné odmítnutí vstupu/zrušení dialogu se stále vrací stávajícím způsobem.
  Existující lokální hlášení ukládání editoru zachována: synchronizace
  publikuje nové objekty pro příští běh, běžící `onlineSources` nemění;
  neúspěšné oznámení uchová pending snapshot, hlásí chybu a vrací False.
- Animace: inicializace `GUI.t` a intervaly `stepGoTo` používají
  `time.monotonic()`, jeden vzorek na rozhodnutí. Plánování Tk přes `after`
  a animátor beze změny. `source_sorter.py` obsahuje pouze nepoužívaný
  timestamp kliknutí, žádné počítání intervalu; další úprava není potřebná.
- Hledání: `path_key` zachovává původní resolve/normcase; `playlist_paths`
  předpočítá množinu cest jednou pro refresh, každý použitý index jednou
  i při duplicitách. Žádná trvalá cache. Kontrola Přidat/výběru čte aktuální
  playlist, takže změny mezi refreshi nejsou důvodem přidat duplicitu.
- Cílená oprava vlastnictví poll: `check_index` před resetem ID ruší dosud
  čekající callback. Ruční dokončení indexace (testy, včetně již existujících)
  dříve zahodilo ID a po zavření zanechalo Tcl `invalid command name`.
  První meziběhy měly testy OK, ale tuto diagnostiku na stderr; nepočítají
  se jako čisté ověření. Finální běh po opravě je bez těchto hlášení.
- Změněné soubory této etapy: `superpresenter/ui/main_window.py`,
  `superpresenter/ui/song_search_window.py`, nový `tests/test_stage3_stability.py`,
  tento dokument, reprodukovatelný `stage3-search-benchmark.py` a logy
  `stage3-tests.log`, `stage3-regression-tests.log`, `stage3-search-benchmark.log`.
- Ověření (PowerShell, `.venv` Python 3.13.14, `-B`, izolovaná testovací
  data a výstupy mimo obrazovku; Windows Store runtime vyžaduje povolení
  mimo sandbox):
  - `$env:PYTHONPATH='tests'; .venv/Scripts/python.exe -B -m unittest test_stage3_stability test_window_lifecycle test_projection_editor test_release_stability test_construct_limits test_collection_qr test_song_search_window test_editor_rendering -v > stage3-regression-tests.log 2>&1`
    — finální běh 82 testů za 40,558 s, všechny OK. Bez `invalid command name`,
    TclError, tracebacků nebo nečekaných callbacků. Nové testy odchytávají Tcl
    bgerror; testy očekávaných Python chyb kontrolují log i Tk fallback.
    Ověřena čtecí chyba během projekce a obnova hledání, chyby obou vstupů
    mutace playlistu, skutečně naplánovaný chybný projekční callback,
    odemčení ovládání, úklid výstupů/timeru a následný start; monotónní
    časování, duplicitní indexy a změna playlistu mezi refreshi. Sada navíc
    zachovává kontroly životního cyklu, stylů, konstrukčních limitů a QR.
    Očekávané diagnostiky odmítnutých konstruktů jsou součástí testů.
  - `$env:PYTHONPATH='tests'; .venv/Scripts/python.exe -B -m unittest test_stage3_stability -v > stage3-tests.log 2>&1`
    — finální cílený běh 5 testů za 12,548 s, všechny OK, bez Tcl/Tk
    diagnostiky nebo nečekaných callbacků.
  - `.venv/Scripts/python.exe -B stage3-search-benchmark.py > stage3-search-benchmark.log 2>&1`
    — 100 syntetických výsledků, 50 unikátních zdrojů a 100 položek
    playlistu včetně duplicit; dočasné cesty, žádné obrovské XML.
    Porovnání skutečné metody refresh z HEAD (před etapou 3) a aktuální
    metody ve stejném okně: mazání/vkládání řádků, značky, stav a Tk idle
    layout. Indexace/dotaz mockovány shodně, nezahrnuty do intervalu.
    Jeden zahřívací pár, sedm měřených párů se střídáním pořadí,
    `perf_counter`, medián a min/max. Před: 1 552,176 ms
    (1 282,786–1 872,453); po: 42,163 ms (38,971–50,619), přibližně
    36,8× rychleji v tomto scénáři. Není to garance odezvy celé aplikace
    ani měření reálného dotazu/indexace; hlavní úspora je resolve cest.
  - `git diff --check` — bez whitespace chyb, běžná upozornění LF → CRLF.
- Neprovedeno: celá sada a validátor (etapa 4), dlouhý provoz/RSS,
  distribuované EXE a skutečný projektor (etapa 5).
- Zbývající nálezy mimo rozsah: čtyři známé kompatibilitní nálezy `@r1`,
  datový nález `songs/.xml`, nestabilní test kolečka předaný etapou 2.
  Globální pojistka úmyslně může zastavit projekci i kvůli neznámé chybě
  pomocného callbacku; bezpečnost sdíleného stavu má přednost.
- Pro další chat: pokračovat etapou 4, přečíst předání a aktuální diff;
  zachovat lokální čtecí hranici, globální pojistku, monotónní intervaly,
  nezávislé projekční snímky a rušení poll. Benchmark lze reprodukovat,
  ale není nutné jej opakovat bez změny hledání. `presentation_presenter.py`,
  číslo verze a uživatelské písně touto etapou nezměněny.
- Necommitováno (HEAD `00b24e8`), nic nepublikováno.

### Etapa 4 — 9. 10. 2026

- Stav: hotovo v rozsahu regresního uzavření zdrojové verze. Verdikt:
  připraveno k sestavení nové testovací distribuce 3.0.0 v etapě 5;
  nejde o finální ověření distribuovaného EXE.
- Výchozí checkout: HEAD `00b24e8`, 16 změněných tracked souborů,
  netrackované předání, testy, skripty a logy etap 1–3. Celé předání,
  status a diff přečteny; AGENTS.md v projektu nenalezen. Předchozí změny
  zachovány. Etapa 4 nemění produkční kód, číslo verze ani uživatelské písně.
- Sémantika `@r1` potvrzena podle `docs/construct_syntax.md` a existujících
  testů připínání: celá sekce se připojuje k předchozímu bloku do kapacity.
  Oba databázové testy nadále porovnávají původní přijetí/odmítnutí a přesné
  legacy instrukce; pouze úmyslné rozšíření s `@` porovnávají s neměnným
  historickým parserem po odstranění markeru. Nový explicitní test skutečné
  písně `k_panu_ruce_pozvedam.xml` kontroluje oba jazyky, příznak pinned,
  shodné legacy pořadí a stránky [6, 4, 6], včetně závěrečných 4 řádků v1
  a 2 připnutých řádků r1. Opakované r1 se podle stávajících pravidel spojují.
- Test kolečka: skutečný hit-test závisí na překrytí okna na desktopu.
  Test nyní zvedá své okno a nastavuje topmost; před syntetickou událostí
  explicitně ověřuje, že souřadnice míří na testovaný Text. Původní kontroly
  posunu canvasu a neposunutí textu zachovány; produkční handler beze změny.
- Test startupu dříve předával Mock okna do skutečného ctypes Windows API,
  což logovalo dvě RecursionError přes ArgumentError, přestože test prošel.
  Nativní configure_window je nyní mockováno na hranici a jeho zavolání
  s gui.win je explicitně ověřeno. Kontrola pořadí recovery/run zachována.
- Změněné soubory této etapy: `tests/test_construct_parser.py`,
  `tests/test_module_boundaries.py`, `tests/test_song_editor_integration.py`,
  tento dokument; nový reprodukovatelný `stage4-runtime-check.py` a logy
  `stage4-tests.log`, `stage4-tests-final.log`, `stage4-validator.log`,
  `stage4-runtime.log`, `stage4-wheel.log`.
- Ověření: PowerShell, projektový Python 3.13, `-B`; runtime Windows Store
  vyžadoval spuštění mimo sandbox. GUI fixture používají dočasná data,
  projekční monitory na souřadnicích mimo obrazovku a izolované profily.
  - `.venv/Scripts/python.exe -B -m unittest discover -s tests -v > stage4-tests-final.log 2>&1`
    — finální běh 305 testů za 77,346 s, OK, návratový kód 0.
    Bez `invalid command name`, TclError, nečekaných callbacků či nativních
    Windows chyb. Šest očekávaných tracebacků: dvakrát callback failure
    při synchronizaci uložení, PermissionError locked při ukládání,
    FileNotFoundError a navazující SongLoadError pro absent.xml,
    RuntimeError failed při opakování oznámení uložení. Tyto diagnostiky
    pocházejí z explicitních negativních testů, které prošly; log kontrolován.
  - `.venv/Scripts/python.exe -B scripts/validate_songs.py --details > stage4-validator.log 2>&1`
    — 859 XML, 1 chyba title (`songs/.xml`), 76 varování:
    12 repetition_missing a 64 repetition_unchecked; návratový kód 1
    je důsledkem prázdného názvu, nikoli pádu validátoru. `songs/.xml` je
    dobře formované XML se dvěma číslovanými slokami a prázdným názvem.
    Bez opory pro zamýšlený název nepřejmenováno ani smazáno.
    repetition_unchecked znamená syntaxi mimo omezenou kontrolu validátoru
    (závorky, rozsahy, násobení či vnořené XML), nikoli automaticky vadný
    konstrukt; databázové testy parseru běží zvlášť. Chybějící repetition
    zůstává varováním. Úplný seznam cest je v logu; žádná nová kategorie nálezu.
  - `.venv/Scripts/python.exe -B stage4-runtime-check.py > stage4-runtime.log 2>&1`
    — 1 provozní test OK, návratový kód 0, 40 cyklů za 11,273 s
    (celý test 11,800 s). Kombinace stylů [0,1], [2], [3], [4], [5],
    start/stop, navigace tam/zpět, update Tk a otevření/zničení sorterů.
    Každý cyklus kontroluje odstranění projekčních oken, prázdný snapshot
    a nepřítomnost animačního timeru. Zachyceny Python callbacky i Tcl bgerror;
    žádná chyba či chybový dialog. Po každém cyklu gc.collect a Windows
    GetProcessMemoryInfo WorkingSetSize: 56,262–66,738 MiB, první 56,480,
    poslední 56,922 MiB, rozsah posledních deseti 10,453 MiB.
    Bez soustavného růstu v tomto vzorku; rozdíly allocatoru/cache a stylů
    nejsou měřením úniku a krátký běh nevylučuje dlouhodobý problém.
  - `$env:PYTHONPATH='tests'; .venv/Scripts/python.exe -B -m unittest test_song_editor_integration.EditorIntegrationTests.test_wheel_over_expanding_verse_scrolls_editor test_song_editor_integration.EditorIntegrationTests.test_wheel_over_expanding_verse_scrolls_editor test_song_editor_integration.EditorIntegrationTests.test_wheel_over_expanding_verse_scrolls_editor -v > stage4-wheel.log 2>&1`
    — 3/3 OK za 2,236 s, bez tracebacků či Tcl/Tk diagnostiky.
  - `git diff --check` — bez whitespace chyb, obvyklá upozornění LF → CRLF.
    Finální diff zkontrolován vůči rozsahu; žádný nový produkční refaktor.
- Meziběhy: výchozí sada 304 testů / 4 známé FAIL (75,889 s) v
  stage4-tests.log. Následný běh 305 / 2 FAIL (69,365 s): nesprávné nové
  očekávání samostatných opakovaných r1 a předané nestabilní kolečko.
  Opraveny testovací předpoklady, kontroly zachovány. První provozní pokus
  měl AttributeError pro dosud nevytvořený animační timer; finální skript
  kontroluje i tento platný stav a při neúspěchu vrací nenulový exit code.
  Meziběhy nejsou vydávány za úspěšnou validaci.
- Neprovedeno: nové sestavení, smoke-test distribuovaného EXE, několikahodinový
  běh, fyzické odpojení/připojení projektoru a cílový počítač — etapa 5.
  Známé historické meze importeru a short2 popsané v construct_syntax.md
  zůstávají mimo nové regresní opravy; sada zachovává kompatibilitu i jejich
  původních chybových stavů. Zelená sada není garance všech legacy konstruktů.
- Pro další chat: přečíst toto předání, `docs/windows-release.md`,
  `docs/release-v3-verification.md` a sestavovací skripty, ověřit status/diff.
  Sestavit do nové složky, zaznamenat prostředí, HEAD i dirty stav a cestu
  artefaktu. Chránit profily/logy v APPDATA a reálná data izolovanými kopiemi.
  Ověřit EXE z jiného pracovního adresáře, smoke-test, styly/prostředky,
  rychlou navigaci, editaci za projekce, start/stop, odmítnutí chybných
  konstruktů a zavírání. Na cílovém hardware provést hotplug a několikahodinový
  běh se sledováním paměti, odezvy a logů; nedostupné kontroly označit čekající.
  Datový nález prázdného názvu uvést u distribuce; uživatelská data neupravovat
  bez zadání. Starší ověření ze září neplatí pro nově sestavený artefakt.
- Necommitováno (HEAD `00b24e8`), nic nesestaveno ani publikováno touto etapou.

### Etapa 5 — 9. 10. 2026

- Stav: částečně. Sestavení a dostupné automatické ověření distribuce OK;
  finální ověření čeká na hardware a součinnost podle
  `docs/stage5-hardware-scenario.md`. Nejde o finálně ověřenou verzi.
- Výchozí checkout: HEAD `00b24e84feff730c841452d27937b071177f44e2`,
  18 změněných tracked souborů a netrackované výsledky/testy etap 1–4.
  Přečteno předání, výsledky etapy 4, oba release dokumenty, build skript,
  spec, vstupní skript a diagnostika. AGENTS.md nenalezen. Status/diff
  zkontrolován, předchozí změny zachovány. Verze a presentation_presenter.py
  beze změn; žádná obsahová změna uživatelských dat.
- Změny: rozšíření pouze opt-in `--smoke-test` v
  `superpresenter/release_check.py`. Reálný save editoru do dočasné písně,
  rychlá navigace, opakovaný start/stop, odmítnutí vstupů, zotavení,
  zavření za projekce a zachycení Tcl bgerror. Potvrzení přejmenování
  testovací písně je automatizováno; při negativních vstupech se dosazuje
  konstrukt do source, aby jej nepřepsal editor, a odchytí se očekávaný dialog.
  Nejde o test skutečného klikání uživatele ani fyzického výstupu.
- Změněné soubory etapy: `superpresenter/release_check.py`,
  `docs/release-v3-verification.md`, tento dokument. Nové:
  `scripts/verify_stage5.ps1`, `docs/stage5-hardware-scenario.md`,
  `stage5-build.log`, `stage5-source.json`, `stage5-verification.log`;
  ignorované artefakty v dist/build a JSON/copie v release-checks.
- Prostředí: Windows 11 10.0.26200, Python 3.13.14 64bit AMD64,
  PyInstaller 6.22.2, Tcl/Tk 8.6.15. `build-dependencies.txt` nového
  artefaktu odpovídá všem deseti pinům requirements-build.txt; instalace
  nebyla potřeba. Projektový Windows Store runtime byl v sandboxu nepřístupný,
  skutečné Python/build/GUI příkazy provedeny se schváleným spuštěním mimo něj.
- Příkazy a výsledky (PowerShell):
  - `.venv/Scripts/python.exe -B scripts/standalone_entry.py --smoke-test stage5-source.json`
    — finálně exit 0, ok=true. První meziběh skončil AssertionError:
    test nepotvrdil dialog přejmenování dočasné písně; diagnostika opravena
    automatickým potvrzením, aplikační chování se neměnilo. Finální JSON
    nahradil mezivýsledek. Šest očekávaných hlášení odmítnutí konstruktu
    na stderr; žádné nečekané callbacky/Tcl chyby.
  - `.venv/Scripts/python.exe -B scripts/build_release.py > stage5-build.log 2>&1`
    — exit 0. Nová samostatná složka, předchozí zářijové vydání zachováno.
    PyInstaller onedir Windows x64 bez UPX. Build warning soubor prohlédnut:
    volitelné/platformní importy, ne selhání sestavení; smoke pokrývá
    používané styly/prostředky, ne všechny volitelné obrazové formáty.
  - `./scripts/verify_stage5.ps1 -ReleaseDirectory dist/3.0.0-20261009-140605 > stage5-verification.log 2>&1`
    — exit 0, prázdný log. Všech 2010 souborů manifestu má správný SHA-256.
    Zabalené i přenesené EXE: exit 0, ok=true, šest stylů, 31 úspěšných
    projekčních běhů, 120 navigačních dvojic, šest uložení názvu při projekci
    se zachováním běžícího snímku, šest odmítnutých konstruktů a restart,
    zavření za projekce, žádné callback chyby. Přenosový ZIP rozbalen do
    `release-checks/stage5-20261009/Přenos s mezerami a diakritikou`.
    Smoke i normální start z `C:\Users\moski\AppData\Local\Temp`, přenos
    s PATH `C:\Windows\System32;C:\Windows`. Normální okno mělo titul
    SuperPresenter 3.0.0, CloseMainWindow/WM_CLOSE skončilo exit 0,
    izolovaný standalone-console.log je prázdný. EXE metadata 3.0.0 / 13B.
  - `git diff --check` — exit 0, pouze obvyklá LF → CRLF upozornění.
    Nový diff ověřen vůči rozsahu: pouze diagnostika, reprodukovatelná
    kontrola a dokumentace. Celá sada nebyla opakována; etapou 4 doložených
    305 OK zůstává zdrojovým regresním výsledkem před rozšířením diagnostiky.
- Izolace: smoke používá vlastní TemporaryDirectory pro APPDATA a píseň,
  odpojené testovací monitory na souřadnicích 30000/30000. Normální spuštění
  používá rozbalenou testovací kopii a
  `release-checks/stage5-20261009/isolated-appdata`. Ostré profily/logy
  se nepoužívají. Artefakt obsahuje všech 859 XML včetně známého prázdného
  názvu songs/.xml (etapa 4: 1 datová chyba, 76 varování); bez opravy/mazání.
- Artefakt:
  - ZIP `C:\Users\moski\Documents\Prográmky\SuperPresenter\dist\3.0.0-20261009-140605\SuperPresenter-3.0.0-win64.zip`
    — 28 537 890 B, SHA-256
    `3CF5F8567C4D1C2FB1DB0C3C27AF1DC39863FEF5764D7C44CB893477A8EDDB38`.
  - EXE `C:\Users\moski\Documents\Prográmky\SuperPresenter\dist\3.0.0-20261009-140605\SuperPresenter-v3\SuperPresenter.exe`,
    SHA-256 `4F1C5BDBB4320C401C5F7C2F7180D714AFFB92814664C76404833CE2DD9E02D1`.
  - release.json: HEAD výše, dirty=true, built_utc=20261009-140605
    (16:06:05 Europe/Prague). Nový ověřovací skript a závěrečné dokumenty
    vznikly po buildu; ZIP obsahuje hotový rozšířený smoke-test, ne tyto
    následné dokumentační záznamy. Manifest ani ZIP po ověření neupravovány.
- Doklady: `release-checks/stage5-20261009/packaged.json`, `portable.json`,
  `verification.json`, build/source logy výše. Každý report je pro nový artefakt;
  starší zářijové výsledky nejsou převzaty jako jeho ověření.
- ČEKÁ a důvod: skutečný projektor/hotplug (není testovaná fyzická sestava),
  čtyřhodinový provoz s pamětí/odezvou/logy (krátký automatický běh jej
  nenahrazuje), čistý druhý PC, skutečné připnutí a tlačítko Bitfocus/Stream
  Deck, antivirus na cílovém PC (vyžadují cílové prostředí/součinnost).
  Přesná izolace, pět cyklů hotplug v obou režimech, čtyřhodinový harmonogram,
  vzorkování working set/private memory/handles a kritéria jsou v ručním scénáři.
- Další krok: provést a doložit ruční scénář pro tento konkrétní ZIP;
  aktualizovat oba záznamy až podle skutečných výsledků. Pokud bude nutná
  oprava kódu, vytvořit další nový artefakt a zopakovat jeho kontroly.
- Necommitováno, nic nepublikováno ani instalováno do produkčního umístění.
