# SuperPresenter

Desktopová aplikace v Pythonu/Tkinteru pro promítání textů písní a dalších
podkladů na projektor. Součástí je editor písní s podporou jazykových variant,
sekcí a pořadí opakování.

## Požadavky a instalace

Pro další vývoj používejte **Python 3.10 nebo novější** s Tkinterem a Tcl/Tk.
Jde o zvolenou vývojovou základnu, nikoli ověřenou nejnižší verzi původní aplikace.
Aplikace je zaměřena na Windows; některé její stávající cesty jsou specifické
pro Windows. Pro používání GUI je nutné grafické prostředí.

V instalátoru Pythonu pro Windows ponechte podporu Tcl/Tk a zapněte přidání
Pythonu do PATH. V terminálu ve složce projektu spusťte:

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Pokud máte místo příkazu `python` dostupný pouze launcher `py`, použijte pro
vytvoření prostředí `py -3 -m venv .venv`. Aktivace prostředí není nutná.

Externí závislosti hlavní aplikace jsou **Pillow** (import `PIL`, obrázky)
a **screeninfo** (seznam monitorů). Editor `song_editor.py` další externí
balíčky nepotřebuje. Tkinter, XML, JSON a ostatní použité moduly jsou součástí
standardní knihovny; Tkinter se neinstaluje přes pip. Na systémech, které jej
distribuují zvlášť, je potřeba doinstalovat systémový balíček pro Tkinter.
Závislosti starého modulu `presentation_presenter.py` nejsou do tohoto seznamu
zahrnuty. Verze balíčků zatím nejsou uzamčené.

## Spuštění

Na Windows spusťte `spustit_super_presenter.bat`, například dvojklikem.
Skript nastaví pracovní adresář podle své vlastní složky a upřednostní Python
z místního `.venv`; pokud prostředí neexistuje, použije `python` z PATH.
Funguje i při zavolání z jiného adresáře. Při chybě ponechá zprávu viditelnou.

Přímé spuštění z kořene projektu:

```bat
.venv\Scripts\python.exe super_presenter.py
```

Samostatný editor:

```bat
.venv\Scripts\python.exe song_editor.py
```

Bez virtuálního prostředí lze použít `python super_presenter.py`, pokud jsou
závislosti nainstalované v daném Pythonu. Další PowerShell spouštěč není potřeba;
soubor BAT lze použít i z PowerShellu jako `./spustit_super_presenter.bat`.
Existující EXE zůstává zachované, ale tento postup spouští aktuální zdrojový kód.

## Struktura projektu

- `super_presenter.py` – hlavní aplikace a promítání.
- `song_editor.py` – samostatný i vložený editor písní.
- `presentation_presenter.py` – starý modul, mimo rozsah této přípravy.
- `songs/` – soubory písní.
- `bible/` – biblické podklady.
- `images/` – obrázky.
- `presentations/` – uložené prezentace.
- `tests/` – základ automatických testů.
- `settings.json`, `gui_style.json`, `projectors_styles.json` – nastavení a styly.
- PDF návody a existující EXE – původní dokumentace a spouštěcí soubor.

Uživatelská data i původní soubory zůstávají zachované.

## Testy

Z kořene projektu po instalaci závislostí:

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Test používá vestavěný `unittest` a importuje oba aktivní moduly v oddělených
procesech. Zablokuje vytváření kořenového okna Tk a spuštění hlavní smyčky;
nepotřebuje displej, ale potřebuje dostupný modul Tkinter a skutečné externí
závislosti. Chybějící závislost znamená selhání testu. Test neověřuje promítání
ani interakce v GUI a neimportuje starý `presentation_presenter.py`.


## Etapa 2 – validace databáze XML písní

Samostatný nástroj `scripts/validate_songs.py` rekurzivně a pouze pro čtení
kontroluje XML, kořen `slide`, atribut názvu písně, přítomnost a názvy variant,
identifikátory a text sekcí, duplicity sekcí v jedné variantě a jednoduché
odkazy opakování. Používá pouze standardní knihovnu, neimportuje aplikaci.
Výchozí složku `songs` určuje podle umístění skriptu, nikoli pracovního adresáře.

```bat
.venv\Scripts\python.exe -B scripts/validate_songs.py
.venv\Scripts\python.exe -B scripts/validate_songs.py --details
.venv\Scripts\python.exe -B scripts/validate_songs.py cesta\k\pisnim
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Bez `--details` vypíše jen souhrn kategorií, žádný log nezapisuje. Návratový
kód 0 znamená žádné chyby (varování jsou přípustná), 1 nalezené chyby,
2 neplatnou či prázdnou vstupní složku / chybu použití.
Nezobrazitelné Unicode znaky při přímém spuštění bezpečně vypisuje escapované.

Identifikátor sekce odpovídá `[A-Za-z][A-Za-z0-9_-]*`; staré identifikátory
`r`, `b`, `r0`, `v1a` a `v1b` jsou zachované. To nezaručuje kompatibilitu
každého identifikátoru s editorem, který očekává číslo za prvním znakem.
Bezpečně se analyzuje pouze celý seznam identifikátorů oddělených bílými znaky.
Závorky, násobení, výběr řádků a jiná syntaxe dostanou varování
`repetition_unchecked`, bez dílčích závěrů o odkazech. Výrazy se nevyhodnocují.
Odkaz chybějící ve všech variantách je chyba; chybí-li jen v některé variantě,
je varováním. Chybějící nebo prázdné `repetition` je také pouze varování.

### Provedené minimální opravy

- `songs/hlas_tvuj_kdyz_vola_mne.xml` a `songs/Jen v tebe důvěr mám.xml`:
  doplněno `</section>` za textem `v3` před `</variant>` v obou jazycích.
  Původní otevřené sekce a bezprostřední uzavření variant určují místo opravy.
- `songs/jsi_slavy kral.xml` (mezera v názvu je U+00A0): doplněno
  `<repetition>` před původním výrazem, který již měl `</repetition>`.
  Název opakování nebyl domýšlen; původní výraz zůstal beze změny.
- `songs/odpustils_mi_(suchdol_version).xml`: vadné `<slide 'Odpustils mi>`
  změněno na `<slide name="Odpustils mi">`; zachován původní text názvu.

Texty písní, jazyky, identifikátory sekcí, pořadí a názvy souborů nebyly měněny.
Žádné hromadné přeformátování; starý `oprava_xml_tagu.py` nebyl spuštěn.
`super_presenter.py`, `song_editor.py` a `presentation_presenter.py` beze změn.
Při zahájení už existovala změna sledovaného
`__pycache__/song_editor.cpython-312.pyc`; byla ponechána.

### Výsledek kontroly 6. 9. 2026

Celkem **858 souborů, 0 syntaktických XML chyb, 5 významových chyb,
76 varování** (13 chybějících opakování, 63 neověřených výrazů).
Počet diagnostik nemusí odpovídat počtu souborů. Validátor nyní končí kódem 1
kvůli níže uvedeným významovým chybám, které nebyly opravovány odhadem:

- `songs/.xml`: `title` – Song name is empty or missing.
- `songs/chci_oslavovat+hevenu_salom.xml`: `section_text` – variant 2 (український - auto): section 'v3' has no text.
- `songs/je_jeden_hlas_co_mel_by_znit.xml`: `repetition_reference` – repetition 2 (JančaDada): unknown section 'r1'.
- `songs/Kancionálky/110 - Pán Jeºíτ p²ijde zas.xml`: `repetition_reference` – repetition 1 (default): unknown section 'v4'.
- `songs/moc_cest_a_slava.xml`: `repetition_reference` – repetition 1 (default): unknown section 'r1'.

Soubory bez `repetition`:

- `songs/buh_vsech_narodu.xml`
- `songs/chci_oslavovat+hevenu_salom.xml`
- `songs/haleluja.xml`
- `songs/jak_vzacna_milost_otcova.xml`
- `songs/jezis_kristus_on_je_kral.xml`
- `songs/krali_ze_vseho_nejvic_touzim_znat_te.xml`
- `songs/laska_tva_na_vsech_mistech_zari.xml`
- `songs/o_pane_tobe_cele_chci_slouzit.xml`
- `songs/spoj_nas_v_jedno_pane.xml`
- `songs/taky_aky_som_dviham_ruky.xml`
- `songs/ti_kdo_pana_cekaji.xml`
- `songs/ty_naplnas_chvalou_nase_usta.xml`
- `songs/ty_si_moj_pastier.xml`

Ověřeno Pythonem 3.12.14 z `.venv` (příkaz `python` není v PATH):
14 testů `unittest` prošlo, včetně existujícího testu importů bez GUI.
Nové testy pokrývají požadovaných pět případů, starší ID, názvy a text,
duplicity, varování, rekurzi, Unicode cesty, návratové kódy a nezměněný obsah.
Provedena také syntaktická kompilace aktivních Python souborů v paměti,
`git diff --check` a kontrola minimálního XML diffu. Projekt nemá konfiguraci
samostatného linteru. GUI a promítání se v této etapě interaktivně netestovaly.
Kompilace upozornila na dvě existující `SyntaxWarning` pro escape `\H`
v `super_presenter.py` (řádky 1553 a 1563); mimo zadání zůstaly beze změny.

Navazující etapa: ručně rozhodnout pět významových nálezů se správcem písní,
poté doplnit bezpečnou analýzu složených opakování a řešit podporu starších ID
v editoru. Varování neznamenají, že výraz je chybný; jen není plně ověřen.

## Etapa 3 – společný model a XML repository

Přidány datové třídy `Song`, `SongVariant`, `SongSection` a `SongRepetition`
v `superpresenter/domain/song.py` a nezávislé `SongRepository` v
`superpresenter/services/song_repository.py`. Balíček má vlastní `__init__.py`
v kořeni i obou podsložkách. Nevyžaduje GUI ani externí závislosti.

API:

```python
from superpresenter.services.song_repository import SongRepository

repository = SongRepository()
song = repository.load("songs/haleluja.xml")
repository.validate(song)
# Uložení je explicitní; načtení soubor nemění.
repository.save(song, "kopie.xml")
```

- Seznamy zachovávají pořadí variant, sekcí a opakování. `selected_repetition`
  vrací první opakování s `main="1"`, jinak první dostupné, nebo `None`.
  Více hlavních opakování se při načtení neopravuje a příznaky se zachovají.
- Text sekcí se dělí pouze na LF, bez stripování. Zachovává prázdné řádky,
  odsazení, koncové mezery, Unicode a Unicode oddělovače. Prázdná sekce se
  načítá jako `[""]`. `guide` zůstává původním textem, bez vyhodnocení výrazů.
- Použit je standardní `xml.etree.ElementTree`. DTD jsou odmítnuté, stejně jako
  neznámé elementy a vnořené značky v textu. Doplňkové atributy se uchovávají.
  UTF-8 výstup escapuje XML znaky; znak CR v textu zapisuje jako referenci.
- Ukládání probíhá přes dočasný soubor ve stejné složce a následné `os.replace`,
  aby chyba validace či zápisu nezkrátila původní soubor.
- `SongLoadError`, `SongSaveError` a `SongValidationError` dědí ze
  `SongRepositoryError`; obsahují `path`, `cause` i řetězenou původní výjimku.
- `validate(song)` ověřuje reprezentovatelnost modelu v XML, nikoli obsahovou
  správnost písně. Prázdné názvy/texty a chybějící opakování zůstávají načitatelné;
  přísnější obsahové diagnostiky nadále poskytuje nástroj etapy 2.

### Kompatibilita a historická data

`WidgetSource.loadSong()` nabízí explicitní načtení společného modelu z aktuální
cesty. Každé volání znovu čte soubor, takže vidí i pozdější uložení editorem.
Dosavadní metody `importSlide`, `importVariants`, `importSections`,
`importRepetitions`, `importSlideName` a parserové pomocné funkce zůstaly stejné.
Úplné přepojení je odložené, protože starý parser odstraňuje prázdné řádky,
normalizuje mezery a jinak zpracovává XML entity. V této etapě se nemění
navigace, vzhled ani dosavadní cesta promítání. `song_editor.py` a
`presentation_presenter.py` nebyly upraveny.

Test celé databáze odhalil opakování uvnitř variant v písních
`buh_vsech_narodu.xml`, `jak_vzacna_milost_otcova.xml` a `moc_cest_a_slava.xml`.
Repository je zahrnuje do seznamu opakování v pořadí dokumentu a pamatuje si
jejich původní umístění. Uchovává také text mimo sekce, včetně teček za
`</section>` v `pana_chval_duse_ma.xml` a `pane_smadni_sme_po_tebe.xml`.
Tyto zvláštnosti se automaticky neopravují. Žádná píseň nebyla touto etapou změněna.

### Ověření 6. 9. 2026

Python z `.venv` je dostupný. Příkaz
`.venv\Scripts\python.exe -B -m unittest discover -s tests -v`:
**24 testů prošlo**, včetně importů bez GUI. Nový soubor
`tests/test_song_repository.py` ověřuje více jazyků, Unicode, whitespace,
pořadí, hlavní i chybějící opakování, chyby XML/I/O, odmítnutí DTD,
nezměněný cíl při neúspěšném zápisu a kompatibilní přístup přes `WidgetSource`.
Všech **858 písní** prošlo load/save/load do dočasné složky se shodou modelu
 i XML obsahu; test současně ověřuje nezměněné bajty originálů.

Validátor etapy 2 nadále hlásí **5 obsahových chyb a 76 varování**, návratový
kód 1; jde o dosavadní nálezy. Provedena syntaktická kompilace aktivních modulů,
nového balíčku, skriptů a testů v paměti a `git diff --check`. Samostatný linter
není nakonfigurovaný. Zůstávají dvě původní `SyntaxWarning` pro escape `\H`
v hlavním modulu. GUI ani skutečné promítání nebyly interaktivně testované.

Při zahájení byly přítomné změny etapy 2 (README, čtyři XML, validátor,
testy a sledovaný pycache); nebyly přepisované. Během práce se v historii
objevil commit `b717406` této etapy. Změny etapy 3 nejsou commitované.

Omezení: jde o obsahový round-trip, nikoli identickou XML serializaci;
parser normalizuje CRLF podle XML standardu, komentáře a processing instructions
se neuchovávají. Chybějící `name` se zapisuje jako prázdný atribut a nehlavní
opakování bez `main`. Metadata původního umístění opakování slouží k round-tripu;
při budoucím strukturálním přeuspořádání variant/opakování musí editor jejich
umístění aktualizovat nebo explicitně převést opakování pod kořen.
Navazující krok: přepojit editor na repository a samostatně otestovat převod
modelových řádků do dosavadního zobrazení před přepojením prezentéru.

## Etapa 4 – samostatný construct parser

Výchozí stav byl čistý repozitář na commitu `0965cf4` s dokončenými etapami
1–3. Jejich změny byly zachovány. Nový modul
`superpresenter/services/construct_parser.py` poskytuje
`parse_construct(text, available_sections)`. Vrací neměnný strom `Construct`
s instrukcemi `SectionStep` (sekce, pozice, výběr řádků) a `RepeatGroup`
(děti, počet opakování, pozice, informace o opětovném použití řádků).
Neimportuje Tkinter, aplikaci ani projektory a opakování nerozbaluje do paměti.

Syntaxe podle původní implementace, význam skupin pro opakované řádky,
API, výjimky a historické zvláštnosti jsou popsány v
[docs/construct_syntax.md](docs/construct_syntax.md). Úplný seznam výskytů
složených konstrukcí a odmítnutých výrazů je v
[docs/construct_inventory.md](docs/construct_inventory.md).
Závorky implicitně opakují dvakrát, násobení patří skupině, rozsah je včetně
obou krajních řádků. Vnoření je podporované; nová syntaxe nebyla přidána.

`WidgetSource.readInstructions()` nyní překládá výsledek služby přes
`Construct.to_legacy()` do totožných dosavadních zásobníkových instrukcí.
Vrací `Construct` a při chybě vyhazuje konkrétní `ConstructError` podtřídu
s pozicí od 0 a čitelnou zprávou. Volající UI výjimku zobrazí místo číselného
kódu. Původní algoritmus zůstal jen v testovací referenci
`tests/fixtures/legacy_construct_parser.py`; produkční fallback není potřeba.
Renderery a navigace, XML písně, editor i `presentation_presenter.py` zůstaly
beze změny.

### Ověření 6. 9. 2026

Python 3.12.14 z `.venv`, příkaz
`.venv\Scripts\python.exe -B -m unittest discover -s tests -v`:
**39 testů prošlo**, z toho 15 nových v `tests/test_construct_parser.py`.
Pokrývají pořadí, skupiny, násobení, výběry řádků, 1500 úrovní vnoření,
velká opakování bez rozbalení, historická ID a okrajové případy, konkrétní
výjimky i jejich pozice, import služby bez GUI závislostí a atomické předání
instrukcí do adaptéru.

Porovnáno všech **860 XML výrazů v 858 souborech** proti zmrazenému původnímu
parseru: při sjednocení sekcí všech variant **853 shodně přijatých** s přesně
stejnými instrukcemi a použitými sekcemi, **7 shodně odmítnutých**. Další test
porovnává skutečný legacy import pro jednotlivé varianty a jejich společný
výběr. Šest reprezentativních písní a syntetické příklady ověřují výsledky
`longText`, `shortText`, skupin i `short2`, včetně zachování níže uvedené
původní chyby `short2`. Stávající testy importů a XML round-tripu také prošly.

Provedena syntaktická kompilace 14 aktivních Python souborů v paměti
a `git diff --check`. Samostatný linter není nakonfigurován. Přetrvávají dvě
původní `SyntaxWarning` pro escape `\H`. Validátor etapy 2 stále uvádí
**5 obsahových chyb a 76 varování** (návratový kód 1); jeho rozsah se neměnil.
GUI ani projekční okna nebyly interaktivně testovány.

### Omezení a další krok

Parser dostává pouze jména sekcí, proto neověřuje rozsahy proti délce textu.
Zachovává historické nulové indexy, prázdné skupiny a nulové násobení, i když
je renderer nemusí bezpečně zpracovat. Velká násobení mohou být nákladná
v dosavadních rendererech. Podrobnosti jsou v dokumentaci syntaxe.

Při regresním testování byly potvrzeny dvě dosavadní chyby mimo parser:
`importRepetitions` přehlíží guide na stejném řádku jako XML tag a `short2`
může u opakovaných skupin vyvolat `IndexError` (například
`at_srdce_me_tebe_vida.xml`). Obě se projevují i s původními instrukcemi;
nebyly opravovány změnou navigace. Doporučená další etapa je samostatná oprava
těchto dvou cest s regresními testy a ruční rozhodnutí sedmi odmítnutých výrazů
ze zdokumentovaného inventáře.

### Upřesnění syntaxe opakování

Podle následného upřesnění uživatele zůstává XML hierarchie
`slide name="Název písně"` → `variant name="jazyk"` → `section name="v1"`.
ID `v1`, `v2`, … označují sloky, `r1`, `r2`, … refrény a `b1`, `b2`, … bridge.
Parser zachovává i ostatní již používaná ID.

`(v1)` znamená první sloku celkem dvakrát, `(v1) * 3` celkem třikrát.
`v1.3` vybere pouze třetí řádek; `(r2.3) * 3` opakuje třetí řádek druhého
refrénu celkem třikrát. Doplněna tolerance ASCII mezer kolem hvězdičky,
kterou původní implementace nepřijímala. Zápisy s mezerami i bez nich nyní
vytvářejí totožné instrukce; pozice chyb stále odpovídají původnímu textu.

Změněny `construct_parser.py`, `tests/test_construct_parser.py`, dokumentace
syntaxe a tento README. Všech **42 testů prošlo**, včetně celé databáze
a přímého ověření textu i navigačních indexů pro `(r2.3) * 3`.
Syntaktická kompilace a kontrola diffu prošly. XML ani renderery se neměnily;
dříve uvedená omezení a doporučená oprava `short2` nadále platí.

### Mezery kolem operátorů a pořadí sekcí

Další upřesnění uživatele rozšiřuje toleranci ASCII mezer i kolem tečky
 a dvojtečky: `(r2.3)*3`, `(r2.3) * 3` a `( r2 . 3 ) * 3` jsou ekvivalentní.
`v1   v2` nadále znamená dvě sekce v uvedeném pořadí. Mezery uvnitř ID nebo
čísla se neslepují. Pozice chyb zůstávají indexy v původním vstupu.
Změněny parser, jeho testy, dokumentace syntaxe a README; XML ani navigace
nebyly upraveny.

Všech 21 parserových testů prošlo, včetně porovnání celé databáze.
Syntaktická kompilace a kontrola diffu prošly. Celá sada 45 testů byla spuštěna,
ale XML round-trip test tentokrát opakovaně hlásil WinError 5 při os.replace
v dočasné složce, také mimo sandbox. Celou sadu tedy tentokrát nelze označit
za úspěšnou. Doporučený krok: prověřit přístup/zamykání dočasných souborů
Windows a zopakovat round-trip test; starší omezení short2 nadále platí.

## Etapa 5 – čistý generátor stacionárních stránek

Výchozí repozitář byl čistý na commitu `4696ce7`. Předchozí etapy zůstaly
zachované. Nová služba `superpresenter/services/stationary_pages.py` neimportuje
Tkinter ani aplikaci a zatím není zapojena do projekce či navigace.
`presentation_presenter.py`, editor, režimy chvály_sál/chvály_stream, styly
a XML písní nebyly změněny.

### Současné struktury a nový kontrakt

- `long` je výstup `longText`, řádky po jazykových variantách po zpracování
  construct instrukcí; `longsteps` jsou indexy řádků první varianty.
- `group_lengths` odvozuje délky logických skupin z instrukcí a první aktivní
  varianty. Neobsahuje kompletní původ řádků ani příznaky připnutí.
- `short2` vzniká z `shortText`: pro jednu variantu páruje řádky uvnitř skupin
  do dvou polí; lichý konec doplní prázdným textem. `short2steps` indexuje dvojice.
- `short2pairmap`, v navigaci `pair2_map`, mapuje dvojice na původní indexy
  (druhý může být `None`). Není to mapa nových čtyřřádkových stránek.
- `paged_starts` obsahuje začátky stránek odvozené po skupinách, standardně
  s krokem 8. Současná navigace vybírá mezi párováním a stránkováním.

Nové API `generate_pages(sections)` přijímá posloupnost `LogicalSection`:
`occurrence_id` je neprázdný unikátní identifikátor konkrétního výskytu sekce
v pořadí prezentace, `lines` je posloupnost `SourceLine(text, section_id,
line_index, pinned=False, repeated=False)`. Opakované výskyty stejné sloky
mají různá occurrence ID, ale stejná zdrojová section ID. Volající předem
vyřeší jazyk, construct a výběry řádků. Text se neořezává; prázdný řádek
zabírá kapacitu, CR/LF uvnitř jedné položky je odmítnuto. Indexy jsou od nuly.

Výstup `PresentationPlan` obsahuje neměnné `HallPage`, `StreamPage` a
`PresentationCue`. Cue má index ovládacího kroku, přímé odkazy na obě stránky,
occurrence ID, zdrojové rozsahy a stabilní `navigation_id`. Rozsahy jsou
polouzavřené `[start, stop)` a uchovávají příznaky. Je jich více, pokud blok
obsahuje připnuté řádky jiné sekce nebo nesouvislý výběr.
Navigační ID tvoří escapované occurrence ID a lokální offset řádku; nezávisí
na textu ani globálním čísle stránky. Je stabilní při vložení jiné sekce
a při textových opravách, nikoli obecně při změně počtu/pořadí řádků uvnitř
sekce. Je lokální pro plán písně; budoucí navigace přidá identitu písně.

### Deterministická pravidla a připnuté řádky

Každá neprázdná logická sekce začíná vlastní stránkou sálu. Krátké sousední
sekce se automaticky neslučují. Sekce se dělí po 8 řádcích a každá stránka
sálu nezávisle po 4 řádcích pro stream. Dva streamové kroky téže stránky
sdílejí přesně tentýž objekt `HallPage`. Prázdná píseň/sekce nevytváří stránku
ani úvodní či koncový krok. Služba nemá časovač ani animace.

Připnutí je v této etapě explicitní vstup: volající vloží kopie posledních
1–2 řádků před následující obsah se zachovaným zdrojovým section ID/indexem
a `pinned=True`, případně `repeated=True`. Kopie zabírají kapacitu stejně
jako ostatní řádky; generátor nic neduplikuje ani nehádá podle textu.
Například dvě připnuté položky + šest řádků refrénu tvoří jednu stránku sálu
a dva streamové kroky. Při více než osmi položkách platí běžné dělení;
generátor neslibuje udržení připnutých řádků a celého následujícího obsahu
pohromadě. Výběr vhodného připnutí patří budoucímu adaptéru.

Dosavadní model má pouze textové řádky a volné atributy sekce, nikoli
definovaný příznak připnutí. Minimální **návrh ke schválení** je volitelný
atribut sekce `stationary_pin_tail="2"` (povoleno 0/1/2, absence = 0).
Budoucí adaptér by poslední N řádků konkrétního výskytu připojil jako označené
kopie před další sekci pouze tehdy, vejde-li se celek do 8 řádků; na konci
písně bez účinku. Repository již obecné atributy uchovává. Atribut se nyní
nečte ani nezapisuje a nebyl doplněn do žádného XML. Před zavedením je nutné
schválit význam pro částečné výběry a opakované výskyty i ověřit legacy editor.

### Diagnostika a ověření 6. 9. 2026

`format_timeline(plan)` vrací text; samostatná ukázka:
`.venv\Scripts\python.exe -B -m superpresenter.services.stationary_pages`

```text
cue 1 -> hall 1 / stream 1.1 [v1-first:row:0]
cue 2 -> hall 1 / stream 1.2 [v1-first:row:4]
cue 3 -> hall 2 / stream 2.1 [v1-first:row:8]
```

Python není v PATH, ale `.venv\Scripts\python.exe` je dostupný.
`-B -m unittest discover -s tests -p test_stationary_pages.py -v`:
**9 testů prošlo**, včetně podtestů pro 4/6/8/10/16 řádků, dvě krátké sekce,
sloku/refrén, dvě připnuté kopie a prázdnou píseň. Další kontroly délek 0–64
ověřují úplnost obsahu, původ, limity i synchronizaci; testuje se také
stabilita ID, opakované výskyty, diagnostika a import bez GUI.

Celá sada `-B -m unittest discover -s tests -v` spustila **54 testů**;
neprošla kvůli dříve popsanému `WinError 5` při `os.replace` v XML round-tripu
(51 chyb podtestů v sandboxu, 9 při opakování mimo něj). Nové testy prošly
v obou bězích. Validátor 858 písní stále hlásí **5 chyb a 76 varování**,
návratový kód 1. Kompilace všech 18 Python souborů v paměti prošla;
přetrvávají dvě původní `SyntaxWarning` pro `\H`. Samostatný linter není
nakonfigurován. Provedena také kontrola `git diff --check`.

Další etapa: přidat explicitní adaptér z modelu a construct stromu do tohoto
vstupu, ověřit převod řádků/jazyků proti existujícím písním a teprve poté
samostatně zapojit cue navigaci a statické vykreslování. Vyřešit také
zamykání dočasných souborů při round-tripu. Tato etapa nedokládá chování
skutečných projekčních oken; jejich napojení je záměrně odložené.

## Etapa 6 – explicitní připnuté výběry (6. 9. 2026)

Výchozí repozitář byl čistý na `98e5e0f` (Etapa 5). Předchozí etapy jsou
zachovány. Návrh atributu `stationary_pin_tail` z etapy 5 byl nahrazen menší
změnou: prefixem `@` v existujícím textu constructu. XML hierarchie se nemění.
Atribut by neodlišoval jednotlivé výskyty a samostatný XML element uvnitř
repetition by vyžadoval změny editoru/importeru. Migrace není nutná a žádné
XML písně nebylo změněno; význam existujících výběrů nelze bezpečně odhadnout.

### Jak označit a zobrazit řádky

Do pole opakování v editoru nebo do textu `<repetition>` napište například:

```xml
<repetition name="default">v1 @v1.4 v2</repetition>
<repetition name="dva řádky">v1 @v1.3:4 v2</repetition>
```

`@v1.4` je další výskyt čtvrtého řádku; `@v1.3:4` další výskyt třetího
 a čtvrtého řádku. Původní `v1` zůstává celý. Značka nepřidává skryté kopie,
nevyžaduje textovou shodu a lze ji použít i pro jiný než koncový řádek.
Platí pro konkrétní výběr, nikoli pro všechny výskyty sekce. Povolen je
jeden řádek nebo dva sousední řádky, číslování od 1. `@v1`, `@v1.0`
a `@v1.1:3` jsou chyby. `(@v1.4)*3` vytvoří tři označené výskyty.
Mezery jsou přípustné stejně jako u dosavadních výběrů.

Ve **stacionárním generátoru** se označený blok předsadí následujícímu obsahu,
pouze když se celý součet vejde do 8 řádků. Dva připnuté + šest následujících
řádků tvoří stránku 8, stream ji rozdělí na 4 + 4. Dva + sedm tvoří samostatné
stránky 2 a 7 (stream 2, 4, 3). Před dlouhou sekcí 10 vzniknou stránky
2, 8, 2 (stream 2, 4, 4, 2). Na konci písně výběr zůstane samostatný.
Sousední označené bloky se slučují zprava, pokud se vejdou; na předchozí
běžnou stránku se nepřidávají. Žádný výskyt se nezahodí ani nededuplikuje.
Neměnný plán se vytvoří před navigací; vpřed i zpět používá stejné stránky.

Staré písně bez `@` zachovávají dosavadní parserové instrukce i hranice sekcí.
Samotné `v1.4`, závorky ani stejný text automaticky neznamenají připnutí.
Legacy překlad `to_legacy()` zachová vybraný text a opakování, ale příznak
připnutí nezpracovává. **Současná GUI projekce dosud není připojena ke
stacionárnímu generátoru**, takže nové pravidlo slučování platí v jeho API;
připojení projekčních oken je samostatný navazující krok. Editor ukládá guide
jako text, není potřeba nové XML pole. `presentation_presenter.py`, hlavní
aplikace a editor nebyly upraveny.

### Model, převod a validace

`SectionStep.pinned` reprezentuje označení v modelu instrukcí (výchozí `False`).
`resolve_sections(construct, variant)` převádí jednu jazykovou variantu
`SongVariant` do logických výskytů; `SourceLine` zachovává ID/index zdroje,
`pinned` a `repeated`. Opakované skupiny se procházejí iterativně a výskyty
mají ID odvozené od pozice instrukce a cesty opakování. Cue identifikuje výskyt
prvního svého řádku, zdrojové rozsahy zachovávají všechny jeho zdroje.

```python
from superpresenter.services.construct_parser import parse_construct
from superpresenter.services.stationary_pages import resolve_sections, generate_pages

# variant je SongVariant načtená přes SongRepository
construct = parse_construct('v1 @v1.3:4 v2', [s.identifier for s in variant.sections])
plan = generate_pages(resolve_sections(construct, variant))
```

Převod používá zobrazované neprázdné LF řádky s odstraněnými krajními mezerami;
prázdné řádky a XML odsazení nejsou číslované. Repository originální text
nemění. Přímé `SourceLine('')` nadále zabírá místo, stejně jako v etapě 5.
Validátor kontroluje označené constructy bez rozbalování násobení, včetně
neexistujících řádků ve všech příslušných variantách a variantových repetition.
Chyba má kategorii `repetition_pin`; kontroly starých neoznačených výrazů
zůstávají stejné. Validace rozsahu platí i uvnitř skupiny násobené nulou.

Prozkoumané skutečné příklady (ponechány beze změny):
- `songs/duchu_svaty_jsi_tu_vitany_(suchdol_version).xml`: `v2 v2.3 r1`
  opakuje poslední řádek třířádkové sloky. Celý guide navíc obsahuje dříve
  známé neplatné `b1.2*4`; pouhé doplnění `@` tuto chybu neopraví.
- `songs/uk_-_krev_svateho_byla_usmirena.xml`: `r1.3:4 v3` vybírá dva
  řádky pět řádků dlouhého refrénu; nejde automaticky o jeho poslední dva.
- `songs/at_srdce_me_tebe_vida.xml`: `(b1.1)*3 b1.2` opakuje jeden řádek
  bridge. Zda má být připnutý, musí určit autor, ne porovnávání textu.

### Ověření a omezení

Python `.venv\Scripts\python.exe` je dostupný. Celá sada
`-B -m unittest discover -s tests -v`: **62 testů prošlo**, včetně 8 nových
testů připnutí, kompatibility databáze a round-tripu všech 858 XML.
Tentokrát se dřívější `WinError 5` neprojevil. Testy ověřují jeden/dva řádky,
překročení kapacity, dlouhou sekci, konec písně, sousední připnutí, skupiny,
neztracený obsah, limity, determinismus, zpětný průchod, chybnou syntaxi,
rozsahy jednotlivých jazyků, XML round-trip a legacy překlad.

Validátor: **858 souborů, původních 5 chyb a 76 varování**, kód 1.
Syntaktická kompilace v paměti a `git diff --check` prošly. Samostatný linter
není nakonfigurován. Zůstávají dvě původní `SyntaxWarning` pro `\H` v hlavní
aplikaci. GUI a reálné projekční výstupy nebyly interaktivně ověřeny.
Velká opakování stále mohou vytvořit velký výsledný plán. Navazující krok:
napojit stacionární plán na GUI navigaci a ověřit oba projekční výstupy;
konkrétní označení v databázi rozhodnout ručně s autory písní.
