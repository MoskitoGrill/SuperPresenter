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

Na Windows spusťte **`spustit_super_presenter.exe`** ve složce projektu.
Je to malý spouštěč aktuálního Python kódu, nikoli zabalená kopie aplikace.
Nevyžaduje BAT a neotevírá konzoli. EXE ponechte vedle `super_presenter.py`.

### První spuštění a hlavní panel Windows

1. Nainstalujte Python 3.10+ s podporou Tcl/Tk a přidáním do PATH.
2. Spusťte `pripravit_prostredi.bat`. Vytvoří místní `.venv` a nainstaluje
   závislosti z `requirements.txt`; lze ho použít i pro jejich aktualizaci.
3. Spusťte `spustit_super_presenter.exe`.
4. Klikněte pravým tlačítkem na ikonu **běžící aplikace** na hlavním panelu
   a zvolte **Připnout na hlavní panel**. Staré nefunkční připnutí nejdříve odepněte.

Okno předává Windows vlastní identitu a příkaz pro opětovné spuštění EXE,
aby připnutá aplikace spouštěla aktuální zdrojový kód. Pokud přesunete složku
projektu, aplikaci spusťte z nového místa a připněte znovu.

Při chybě EXE zobrazí zprávu. Diagnostika spouštěče je v
`%LOCALAPPDATA%/SuperPresenter/logs/launcher.log` a při dalším spuštění se přepíše.
Volba `spustit_super_presenter.exe --check` zkontroluje prostředí a importy bez
otevření GUI; návratový kód je 0 při úspěchu, jinak 1. Nenahrazuje test GUI.

### Aktualizace přes Git

Zavřete aplikaci a proveďte `git pull` (s případným běžným vyřešením místních
změn). Pokud se mění závislosti, spusťte `pripravit_prostredi.bat`. Potom
spusťte aplikaci připnutou ikonou. `.venv` je místní a není součástí Gitu.
Běžné změny Python kódu nevyžadují nové sestavení EXE.

### Vlastní ikona a sestavení EXE

Zatím se používá generická ikona `images/launcher-default.ico`.
Vlastní ikonu uložte jako **`images/ikona.ico`** (skutečný formát ICO,
například s velikostmi 16, 32, 48 a 256 px; pouhé přejmenování PNG nestačí).
Při dalším spuštění ji aplikace použije pro okno a hlavní panel.
Pro změnu ikony samotného EXE jej po zavření aplikace znovu sestavte:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_launcher.ps1
```

Skript používá kompilátor .NET Framework 4.x ve Windows a zdroj
`scripts/WindowsLauncher.cs`; nevyžaduje PyInstaller ani Visual Studio.
Do Gitu zahrňte také nové EXE a ikonu. Windows může mít ikonu připnutého
zástupce v mezipaměti; po změně jej případně odepněte a znovu připněte.

Pro diagnostiku lze použít `spustit_super_presenter.bat`, který nechá viditelnou
konzoli, nebo přímo z kořene projektu:

```bat
.venv\Scripts\python.exe super_presenter.py
```

Samostatný editor:

```bat
.venv\Scripts\python.exe song_editor.py
```

## Struktura projektu

- `super_presenter.py` – kompatibilní spouštěč; aplikace je v `superpresenter/app.py`
  a `superpresenter/ui/`, datová logika v `superpresenter/domain/` a `superpresenter/services/`.
- `song_editor.py` – samostatný i vložený editor písní.
- `presentation_presenter.py` – starý modul, mimo rozsah této přípravy.
- `songs/` – soubory písní.
- `bible/` – biblické podklady.
- `images/` – obrázky.
- `presentations/` – uložené prezentace.
- `tests/` – základ automatických testů.
- `settings.json`, `gui_style.json`, `projectors_styles.json` – nastavení a styly.
- PDF návody – původní dokumentace.
- `spustit_super_presenter.exe` – sestavitelný Windows spouštěč aktuálního kódu.

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

## Etapa 7 – napojení stacionární projekce na cue 8/4 (6. 9. 2026)

Výchozí stav: čistý repozitář na `a112c12` (Etapa 6). Předchozí změny jsou
zachované. Žádná píseň ani `presentation_presenter.py` nebyly upraveny.

Přesné názvy a explicitní typy v `projectors_styles.json`:

| Název stylu | mode |
| --- | --- |
| chvály sál | legacy_scroll |
| chvály stream | legacy_scroll |
| chvály sál – stacionární | stationary_hall |
| chvály stream – stacionární | stationary_stream |
| chvály sál 1/3x | legacy_scroll |
| chvály stream 1/3x | legacy_scroll |

Názvy a pořadí stylů zůstaly zachované kvůli uloženým konfiguracím. `mode`
má přednost před názvem: styl lze přejmenovat. U staré konfigurace bez `mode`
se pouze dva přesné původní stacionární názvy přeloží v kompatibilitní funkci
`style_mode`; ostatní styly zůstanou legacy. Neznámá hodnota `mode` zastaví
spuštění s chybou konfigurace. U přejmenovaného starého stacionárního stylu
bez `mode` doplňte typ ručně. Žádná detekce podle části názvu se nepoužívá.

### Propojení a ovládání

`superpresenter/services/stationary_navigation.py` obsahuje čistou službu
`CueNavigation`, adaptér vybraných variant `build_plan` a malý canvas adaptér
`StationaryPageWidget` bez importu Tkinteru. `super_presenter.py` při spuštění
připraví plán každé písně podle aktuálního guide a zvolených variant. Plány
se během navigace nepřegenerovávají. Nové spuštění je připraví znovu.

Stacionární seznam náhledu má jednu položku na cue. Šipky vlevo/vpravo,
tlačítka vpřed/zpět i výběr položky používají tentýž navigační stav. Sál
vykresluje `hall_page`, stream `stream_page`. Stejný objekt stránky sálu
nevyvolá ani změnu textu na canvasu; stream se přitom aktualizuje. Přepnutí
je okamžité, bez plánování animace přes `after`. Při návratu z prázdného
kroku se stránka znovu správně vykreslí.

Zachovány jsou prázdné kroky na začátku a konci písně. Posloupnost je:
úvod, cue 1 až N, konec, úvod další písně, cue 1 další písně.
Zpět prochází přesně tutéž posloupnost obráceně, tedy z úvodu další písně
nejprve na konec předchozí písně a potom její poslední cue. Přímé přepnutí
písně (také Shift+šipka) nastaví úvod. Začátek a konec celého seznamu se
nepřetáčejí. Prázdný seznam ani píseň bez cue navigaci neshodí.

Stejná časová osa platí při samostatném stacionárním sálu, samostatném
stacionárním streamu i jejich souběhu. Sál samotný proto má také kroky,
při nichž se jeho obraz nemění. Čistě pohyblivá sestava používá původní
navigaci a widgety; větve `pair2/paged` jsou ponechány pro legacy konfigurace
a stacionární větev je obchází. Ve smíšené sestavě s pohyblivým projektorem
se jeho původní widget nastaví okamžitě na zdrojový řádek začátku cue.

Výběry řádků a `@` se vyhodnotí před proložením zvolených jazyků. Každý
fyzický řádek překladu zabírá jednu pozici v limitu 8/4, pořadí jazyků je
pořadí jejich výběru. Náhled zobrazuje všechny zvolené jazyky současně.
Stacionární widget zatím používá hlavní font pro všechny jazyky. Sál má
plátno 1920 × 1080 místo dřívější výšky 5000 a stream začíná na y=860,
aby se vešly čtyři řádky. Rozměry ani widgety legacy stylů se nemění.

### Diagnostika a ruční scénáře

Čítač ovládání ukazuje `song`, `step`, `cue`, `hall`, `stream` (od jedničky,
`-` označuje prázdný krok). Pro výpis každého přepnutí do konzole spusťte
v PowerShellu:

```powershell
$env:SUPERPRESENTER_CUE_DEBUG = '1'
.venv\Scripts\python.exe super_presenter.py
```

Na skutečných výstupech zbývá ověřit:

- Jedna sekce s 8 řádky: cue 1 = hall 1 / stream 1; cue 2 = hall 1 /
  stream 2. Sál bez bliknutí, stream zobrazí druhé čtyři řádky.
- Jedna sekce s 10 řádky: dvojice stránek 1/1, 1/2, 2/3.
- Vpřed přes konec do další písně a zpět přes stejné prázdné kroky;
  přímé přepnutí písní a nové spuštění vždy začínají úvodem.
- Tytéž scénáře se sálem samotným, streamem samotným a oběma současně.
- Původní `chvály sál` a `chvály stream`: původní pohyb a ovládání,
  včetně rychlého přepínání; také smíšená sestava se stacionárním stylem.
- Dlouhé řádky, více jazyků, připnuté výběry, čitelnost na skutečném
  rozlišení a umístění textu vůči pozadí streamu a QR obrázku.

### Ověření a omezení pro další etapu

Python `.venv\Scripts\python.exe` je dostupný. Nový soubor
`tests/test_stationary_navigation.py` přidává 12 testů bez skutečných oken:
plány 8 a 10 řádků, přesně obrácený průchod včetně prázdné písně, start a
restart všech písní, prázdný seznam, výběr cue myší, šipky i metody tlačítek,
všechny kombinace výstupů, stejné hall page bez zásahu do canvasu,
kompatibilitu stylů, jazykové varianty/připnutí a legacy směrování widgetů.

Celá sada `-B -m unittest discover -s tests -v`: **74 testů prošlo**.
Validátor: **858 XML, původních 5 chyb a 76 varování**, návratový kód 1.
Kompilace všech **21 Python souborů** v paměti a `git diff --check` prošly.
Samostatný linter není nakonfigurován; přetrvávají dvě původní
`SyntaxWarning` pro `\H` v hlavní aplikaci.

Změněné soubory: `super_presenter.py`, `projectors_styles.json`, tento
`README.md`; nové soubory: `superpresenter/services/stationary_navigation.py`
a `tests/test_stationary_navigation.py`.

GUI testy používají náhrady canvasu a ovládacích prvků, nikoli skutečná okna.
Dlouhý text se může zalomit a překročit pevnou svislou rozteč; automatické
zmenšování fontu není součástí této etapy. Velká opakování stále mohou
vytvořit velký plán. U více jazyků s různými délkami může smíšené legacy
zobrazení používat odlišné zarovnání; prioritou je přesná společná časová
osa stacionárních výstupů. Doporučený další krok: vizuálně provést uvedené
scénáře na cílovém sálu/streamu, potom samostatně řešit typografii dlouhých
řádků a případnou diferenciaci fontů jazyků. Známé chyby databáze neopravovat
automatickým odhadem obsahu.

## Doplnění Etapy 7 – opakované řádky stejné sloky (6. 9. 2026)

Na předchozí necommitované napojení 8/4 navazuje pravidlo pro obyčejné
výběry řádků bez `@`. Při zahájení této úpravy už existovala také uživatelská
změna `songs/.xml`; zůstala nedotčená. `presentation_presenter.py` se nemění.

Příklad pro pětiřádkovou sloku:

```text
v1 (v1.5)*3
```

Zobrazí celou sloku a tři další výskyty pátého řádku: sál 8, stream 4 + 4.
Pátý řádek tedy zazní čtyřikrát celkem. Pro třikrát celkem použijte
`v1 (v1.5)*2`: sál 7, stream 4 + 3. Stejně funguje rozepsaný zápis
`v1 v1.5 v1.5 v1.5` a navazující rozsah, například `v1 v1.4:5`.

Slučuje se celá souvislá skupina výběrů pouze s bezprostředně předcházejícím
blokem stejné zdrojové sekce a jen když součet nepřesáhne 8 fyzických řádků.
Identita sekce se určuje podle ID, nikoli shodou textu. `v1 r1` s délkami
5 a 3 zůstane na samostatných stránkách 5 / 3. Výběr `r1.1` se rovněž
nepřipojí k `v1`. Opakování celé sloky `(v1)*2` zachovává její hranice.

`v1 (v1.5)*4` vytvoří stránky 5 / 4: skupina čtyř opakování se nerozdělí
jen proto, aby vyplnila první stránku. Samotná skupina delší než 8 se
následně standardně stránkuje po osmi. Při více jazycích se do kapacity
počítají všechny zobrazované jazykové řádky. Explicitní dopředné připnutí
`@` z Etapy 6 zachovává vlastní dosavadní pravidlo; nové slučování jej
nepřesouvá na předchozí sloku. Historická poznámka Etapy 6, že obyčejné
výběry vždy zachovávají hranice, je tímto doplněním pro stacionární režim
nahrazena. Význam textu písně ani legacy překlad parseru se nemění.

Změněno v tomto doplnění:
- `superpresenter/services/stationary_pages.py`: příznak obyčejného výběru
  na LogicalSection a slučování celé skupiny se stejnou slokou.
- `superpresenter/services/stationary_navigation.py`: přenos příznaku přes
  adaptér vybraných jazyků, takže pravidlo skutečně platí v projekci.
- `tests/test_stationary_navigation.py`: tři nové testy s více scénáři
  (kapacita, ID sekce, opakování, rozsahy, více jazyků, cue vpřed i zpět).
- `tests/test_pinned_lines.py`: upravené očekávání obyčejného `v1 v1.4`;
  testy explicitního `@` zůstaly zachované a procházejí.
- `README.md`: tento zápis a příklady pro obsluhu.

Ověření: **77 testů prošlo**, kompilace **21 Python souborů** v paměti a
`git diff --check` prošly. Python ve `.venv` je dostupný. Samostatný linter
není nakonfigurován; zůstávají dvě původní SyntaxWarning pro `\H`.
Validátor: **858 souborů, 5 chyb, 77 varování**, kód 1. Jedno varování navíc
oproti předchozímu běhu pochází z již změněného `songs/.xml`: jeho construct
`v1 v2 v1 (v1.6)` není vyhodnocován omezenou kontrolou starých výrazů ve
validátoru (`repetition_unchecked`); není to chyba nového slučování.

Omezení z předchozí etapy platí: skutečná okna nebyla vizuálně testována a
zalamování dlouhého textu může zvětšit počet obrazových řádků. Navazující
krok: znovu spustit prezentaci (plán se vytváří při startu) a vyzkoušet
uvedený pětiřádkový příklad na sálu i streamu, včetně návratu zpět.

## Etapa 8 – řádkový náhled časové osy 8/4 (6. 9. 2026)

Navazuje na necommitovanou Etapu 7 a její doplnění. Existující změny README,
projektorových stylů, songs/.xml, stránkování a testů byly zachovány.
Tato etapa upravuje pouze super_presenter.py, tests/test_stationary_navigation.py
 a README.md. presentation_presenter.py ani XML písně se nemění.

Podle upřesnění uživatele zůstává seznam po jednotlivých textových řádcích.
Jeden ovládací krok tvoří záhlaví a jeho řádky; každý z nich přímo odkazuje
na stejný PresentationCue. Kliknutí na text (i prázdný řádek) nebo záhlaví
vybere přesně tento krok, bez zpětného odvozování z indexů zdrojového textu.
Kliknutí, šipky a tlačítka synchronizují tentýž navigační stav.

Záhlaví obsahuje ID sekce, číslo kroku a číslo stránky sálu s označením
nová / stejná. Aktivní záhlaví má modré písmo a značku fokusu.
Při zapnutém stacionárním streamu běžný výběr označuje jeho nejvýše čtyři
textové řádky. Světle modrý podklad označuje celou aktivní stránku sálu,
včetně druhého streamového kroku. Bez streamu výběr označuje celou stránku
sálu (nejvýše osm řádků), ovládání stále postupuje po cue.
Text pochází přímo ze stream_page.lines; oba bloky dohromady tvoří přesný
obsah hall_page. Zůstávají všechny vybrané jazyky, opakování a prázdné řádky.
Záhlaví jsou pouze pro obsluhu, neposílají se na projektory. Rozměry okna
se nemění; seznam při přepnutí posune aktivní stránku do viditelné oblasti.
Čítač používá české názvy místo interní diagnostiky; konzolový debug zůstává.
Legacy indexové pomocné metody jsou stále používané a nebyly odstraněny.

Ověření: Python z .venv je dostupný, všech 79 testů unittest prošlo.
Doplněno ověření každého řádku a záhlaví proti přesnému cue i oběma výstupům,
počtu vybraných řádků, úvodu, konce, další písně a návratu. Stávající testy
ověřují šipky, opakování, více jazyků a kompatibilitu databáze.
Kompilace 19 aktivních Python souborů v paměti a git diff --check prošly.
Samostatný linter není nakonfigurován; přetrvávají dvě původní SyntaxWarning
pro escape \H. Validátor databáze má nezměněných 5 chyb a 77 varování
v 858 souborech (návratový kód 1).

Omezení: testy GUI používají náhrady ovládacích prvků; skutečná okna nebyla
vizuálně ověřena. Náhled ukazuje textový obsah, nikoli zalamování a font
projekčního canvasu. U velmi úzkého seznamu může být dlouhé záhlaví/text
vodorovně oříznuté jako dosavadní text. Smíšené legacy výstupy nadále mají
původní vykreslování, tento náhled popisuje stacionární sál a stream.
Doporučený další krok: na cílovém monitoru ověřit čitelnost podbarvení,
8/4 a 10řádkovou sloku, kliknutí na druhou polovinu sálu a návrat mezi písněmi.

### Upřesnění Etapy 8 – pouze text písně

Na přání uživatele byla odstraněna všechna záhlaví sekcí, kroků a stránek
ze seznamu. Viditelný text nyní tvoří pouze řádky písně v pořadí promítání.
Úvod a konec mají prázdnou položku, takže zůstává možný přímý výběr prázdného
výstupu. Čítač pod seznamem, zvýraznění 4/8 a přímé odkazy řádků na cue
zůstávají zachované. Tato úprava nahrazuje popis záhlaví výše.
Změněny super_presenter.py, tests/test_stationary_navigation.py a README.md.
Test přesného obsahu seznamu nově vylučuje přidané popisky. Ověření: všech
79 testů prošlo, syntaktická kompilace upravených modulů a git diff --check
prošly; přetrvávají původní dvě SyntaxWarning pro \H. Skutečné GUI nebylo
vizuálně testováno; navazující krok je znovu spustit prezentaci a ověřit
výběr textových řádků. presentation_presenter.py a písně zůstaly nedotčené.

### Doplnění Etapy 8 – střídavé pozadí slok

Každý druhý blok sloky/refrénu v pořadí promítání má jemně světlejší pozadí
(8 % směrem k bílé podle aktuální barvy seznamu; u #444444 je to #535353).
Střídání vychází z výskytů sekcí v cue, nikoli z čísla v názvu sloky.
Dlouhá sloka si zachová odstín přes více streamových kroků i stránek sálu;
opakovaný celý výskyt sloky tvoří nový blok. Připojené výběry řádků na téže
stránce sálu zůstávají součástí společného bloku. Úvod a konec mají základní
pozadí. Zvýraznění aktivního sálu a výběr streamu mají přednost; po odchodu
se původní střídavé pozadí obnoví. Žádné nadpisy se do seznamu nevracejí.

Změněny super_presenter.py, tests/test_stationary_navigation.py a README.md.
Předchozí necommitované změny zachovány; presentation_presenter.py, styly
projektorů a XML písně nebyly touto úpravou změněny.
Ověření: všech 80 testů prošlo, včetně tří opakovaných deset řádků dlouhých
slok, zachování odstínu přes stránky a obnovení po změně aktivního kroku.
Syntaktická kompilace upravených modulů a git diff --check prošly.
Zůstávají dvě původní SyntaxWarning pro \H; samostatný linter není nastaven.
Skutečné GUI nebylo vizuálně ověřeno. Doporučený další krok: znovu spustit
prezentaci a posoudit jemnost kontrastu na monitoru obsluhy.

### Doladění streamového pruhu – svislé umístění textu

Na základě náhledu obsluhy posunut začátek textu stacionárního streamu
z y=860 na y=872 (o 12 px níže). Pro zobrazený čtyřřádkový blok tím vychází
přibližně stejná mezera nad a pod textem v šedém pruhu (pozadí začíná na
 y=858 a končí na 1080). Velikost fontu 32, rozteč 48 i pozadí se nemění.
Změněny pouze projectors_styles.json a README.md; presentation_presenter.py
ani písně nebyly upraveny. Výchozí repozitář byl čistý na b6dfd63.
Ověření: 80 testů unittest, načtení JSON a git diff --check prošly.
Přetrvávají dvě původní SyntaxWarning pro \H; samostatný linter není nastaven.
Jde o pevný posun podle dodaného čtyřřádkového náhledu, nikoli automatické
centrování různých počtů řádků. Doporučený krok: restartovat aplikaci, aby
načetla styl, a ověřit okraje na skutečném streamovém výstupu.

### Doladění označení aktivního sálu – neutrální šedá

Modré pozadí části aktivní stránky sálu mimo stream nahrazeno jemně světlejší
variantou barvy výběru streamu: 8 % směrem k bílé, tedy při současném stylu
#444444 → #535353. Text používá běžnou barvu seznamu (nyní bílou), nikoli
původní tmavě modrou. Výběr streamu, střídání neaktivních slok a navigace
zůstávají zachované. Tento zápis nahrazuje dřívější popis modrého podkladu.
Změněny super_presenter.py, tests/test_stationary_navigation.py a README.md.
Předchozí změny README a projectors_styles.json zachovány; do písní ani
presentation_presenter.py tato úprava nezasahuje.
Ověření: všech 80 testů prošlo; syntaktická kompilace upravených modulů
 a git diff --check prošly. Přetrvávají dvě původní SyntaxWarning pro \H.
Samostatný linter není nastaven. Skutečné GUI nebylo vizuálně ověřeno;
doporučený další krok je restart aplikace a kontrola kontrastu na monitoru.

---

# SuperPresenter – poznámky pro další etapy

## Etapa: životní cyklus Song Editoru (6. 9. 2026)

### Výchozí stav

Výchozí commit: `4e4472b` (Nová mechanika pro stream). Pracovní strom byl čistý.
V tomto checkoutu nebyl README ani zdrojové soubory modelu, repository a testů
z předchozích etap. Ve složkách `superpresenter` a `tests` byly pouze jejich
`__pycache__`; ty nejsou náhradou zdrojových souborů. Tato etapa proto doplňuje
malou společnou datovou vrstvu. Neobnovuje nesouvisející předchozí etapy.

### Implementováno

- `superpresenter/domain/song.py`: společný `Song` pro editor i hlavní aplikaci,
  jazyky, sekce, pojmenovaná repetition a hlavní repetition; XML šablona zachovává
  další atributy a metadata platných vstupů.
- `superpresenter/services/song_repository.py`: načítání XML, validace názvu,
  převod názvu na soubor, ochrana kolizí, zápis do dočasného souboru ve stejném
  adresáři, flush/fsync a atomické nahrazení. Nový cíl se zveřejňuje atomickým
  hardlinkem bez možnosti přepsat souběžně vzniklý soubor.
- `superpresenter/services/song_edit_session.py`: jeden model stavu pro draft
  i existující píseň, čistý snapshot, dirty state, uložení kopie/přejmenování.
  Odstranění sekce přečísluje odpovídající sekce ve všech jazycích i odkazy
  ve všech repetition, včetně rozsahů řádků a vnořených prázdných skupin.
- `song_editor.py`: jediná cesta načítání, indikace neuložených změn,
  detekce změn textu i vložením ze schránky, názvu, jazyků, sekcí a repetition.
  Přechody nabízejí Uložit / Zahodit / Storno. Změna názvu souboru nabízí
  přejmenování nebo kopii; kolize vyžaduje souhlas. Chyba načtení zachová
  rozpracovanou píseň. Chyby ukládání a callbacků se zobrazují konkrétně;
  neúspěšná synchronizace se před dalším přechodem opakuje.
- `super_presenter.py`: `WidgetSource` adaptuje společný Song na existující
  rozhraní promítání. Název se váže přes StringVar předanou konstruktoru,
  editor se nepřepojuje nahrazováním jeho interních widgetů. Construct zrcadlí
  vybrané repetition oběma směry a je součástí dirty state. Seznam jazyků se
  aktualizuje při editaci a výběr zůstává zachován při uložení.
  Hlavní aplikace publikuje uložený model callbackem, včetně obnovení již
  otevřených souborů a jejich cest po přejmenování. Oddělený systém snapshotů
  draftu byl odstraněn; `draft_open` slouží jen jako informace pro navigaci.
- Ochrana změn platí pro jinou píseň, nový draft, zavření písně a aplikace.
  Také před spuštěním promítání se vyřeší neuložené změny. Běžící promítání
  používá vlastní snapshot, aktualizovaná data se použijí při dalším spuštění.
- Samostatné spuštění `song_editor.py` zůstalo zachováno; má vlastní pole názvu
  a ochranu zavření. Hlavní aplikace už násilně neukončuje samostatný editor.
- `presentation_presenter.py`, knihovna písní a konfigurace nebyly upraveny.
  Rozložení vloženého editoru zůstalo zachováno, přibyl stavový popisek.

### Ověření

Python je dostupný jako `.venv\Scripts\python.exe` (3.12.14).

```powershell
# Datová část bez GUI:
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_song_editor_data.py -v

# Všechny testy, včetně skrytých oken Tk a celé knihovny:
.venv\Scripts\python.exe -B -m unittest discover -s tests -v

git diff --check
```

Závěrečný výsledek: všech 26 testů prošlo.

Testy pokrývají životní cyklus a Storno, neúspěšné ukládání, kolize,
přejmenování/kopie, chyby callbacků a jejich opakování, synchronizaci Construct,
jazyků, zachování metadat i start editoru a hlavního okna. Test knihovny kontroluje
načtení všech 858 XML písní, shodu modelu po uložení do dočasných souborů
na disku a shodu viditelného textu s původním importérem (po dekódování XML entit
a odstranění okrajových mezer). Originály testy nepřepisují.

Byla provedena syntaktická kompilace změněných Python souborů bez zápisu
`__pycache__` a kontrola diffu. Ruff/Pyflakes/Flake8 nejsou v prostředí nainstalované.
Tk testy v sandboxu nemohly načíst existující Tcl knihovnu; mimo sandbox fungují.

### Známá omezení a další krok

- Čtyři existující XML soubory jsou neplatné. Hlavní aplikace je načte původním
  tolerantním importérem do společného Song a zobrazí upozornění. Až výslovné
  uložení vytvoří platné XML. Samostatný editor používá striktní repository
  a neplatné XML odmítne, aniž by přepsal rozpracovanou píseň.
  Jde o `hlas_tvuj_kdyz_vola_mne.xml`, `Jen v tebe důvěr mám.xml`,
  `jsi_slavy kral.xml` a `odpustils_mi_(suchdol_version).xml`.
  Tolerantní import nezaručuje zachování nestandardních metadat poškozeného XML.
- Přejmenování je bezpečný zápis nového souboru následovaný odstraněním starého;
  není to transakce dvou souborů. Pokud odstranění selže, zůstanou obě kopie,
  editor zůstane změněný a chyba uvede obě cesty.
- Atomické zveřejnění nového souboru vyžaduje podporu hardlinků (např. NTFS).
  Nepodporovaný disk vrátí konkrétní chybu; existující cíle se nahrazují `os.replace`.
- Není přidána automatická obnova po pádu aplikace ani řízení souběžných editací
  téhož souboru v jiném procesu. Ochrana se vztahuje na běžné uživatelské přechody.
- Navazující krok: ruční zkouška běžné práce se skutečnými projektory
  (editace → Storno/Uložit/Zahodit → nové spuštění promítání). Potom lze
  samostatně řešit opravu čtyř neplatných písní a odstranění tolerantního importéru.

## Začlenění do dev (6. 9. 2026)

Původní uspořádaný model Song a SongRepository z etapy 3 zůstávají zachovány.
Nový editor a prezentér používají EditableSong (domain/editable_song.py) a
SongEditorRepository (services/song_editor_repository.py). Výše uvedené poznámky
k životnímu cyklu popisují původní implementaci na Sbor; při přenosu do dev
byly její model a repository přejmenovány, aby nepřepsaly existující rozhraní.
WidgetSource.loadSong() nadále vrací původní model načtený ze souboru.

Po začlenění prošlo všech 50 testů (`python -B -m unittest discover -s tests -v`),
včetně původního repository, validátoru, kompatibility knihovny písní a GUI editoru.

## Nápověda názvu a vynechané sekce (7. 9. 2026)

- Prázdné pole názvu zobrazuje „Název zde“ v hlavní aplikaci i samostatném editoru.
  Kliknutí nebo vstup klávesnicí do pole nápovědu skryje; po opuštění prázdného
  pole se vrátí. Nápověda není součástí modelu a nemění dirty state.
- Před uložením se kontroluje každé pojmenované opakování zvlášť. Dialog vypíše
  sekce, které nejsou použité (například Refrén 1 při `v1 v2 v1`). Volba Ano
  uloží i záměrně vynechané sekce, Ne ponechá editor otevřený bez zápisu.
- Kontrola pokrývá skupiny, násobení, řádkové rozsahy i sousední odkazy `v1v2`.
  Stejné sekce v různých jazycích se ve varování neopakují. Jde o upozornění na
  vynechání, nikoli úplnou validaci syntaxe nebo rozbalení konstruktu.
- Dotčené soubory: `song_editor.py`, `super_presenter.py`,
  `superpresenter/services/song_edit_session.py`, `tests/test_song_editor_data.py`,
  `tests/test_song_editor_integration.py` a tento README.
- Ověření: 57 testů prošlo (`.venv/Scripts/python.exe -B -m unittest discover -s tests`),
  včetně kontroly knihovny a GUI. První běh narazil na chyby přístupu k dočasnému
  souboru knihovny; opakovaný běh prošel. Test kliknutí vyžaduje mapované okno,
  proto ho umisťuje mimo obrazovku. Provedena také kontrola syntaxe a diffu.
- Navazující krok: vyzkoušet vlastní pojmenovaná opakování jednotlivých kapel.
  Původní rozpracované změny a pomocné skripty nalezené na začátku zůstaly zachované.

### Vzhled nápovědy názvu (7. 9. 2026)

Nápověda „Název zde“ je vycentrovaná a světle šedá (`#aaaaaa`). Skutečný název
ani chování pole se nemění. Upraven `song_editor.py`; všech 18 integračních
GUI testů prošlo, stejně jako kontrola syntaxe a diffu. Bez nových známých omezení.

## Dokončení etapy 9: jeden Song a SongRepository (7. 9. 2026)

Tato část nahrazuje poznámku „Začlenění do dev“ o dvou souběžných datových
rozhraních. Editor, editovací session a WidgetSource nyní používají přímo
`superpresenter.domain.song.Song` a `superpresenter.services.song_repository.SongRepository`.
`EditableSong` a `SongEditorRepository` byly odstraněny. Původní API repository
z etapy 3 zůstává použitelné, včetně `WidgetSource.loadSong()`.

### Změny

- Song nabízí odvozené textové pohledy pro existující UI a tovární metodu pro
  draft/legacy import. Tyto pohledy nejsou druhý uložený stav ani druhý datový model.
- `update_song_fields` přenáší změny widgetů do kopie společného modelu. Pokud se
  pole nezměnilo, ponechá jeho původní řádky včetně mezer, prázdných řádků a atributů.
  Zachovává pořadí variant, sekcí, umístění repetition a metadata kořene XML.
- Společná repository převzala generování názvů souborů a ochranu kolizí.
  Výchozí `save(song, path)` zachovává původní chování etapy 3; editor předává
  `overwrite` výslovně podle zvoleného cíle a potvrzení uživatele. Zápis používá
  dočasný soubor, flush/fsync a atomické zveřejnění/náhradu. Chyby mají cestu a příčinu.
- Prázdný název dál odmítá editor i editovací session; repository ponechává možnost
  bezeztrátově převést starší píseň s prázdným názvem pro jiné datové nástroje.
- Tři existující písně mají stejné jméno repetition uvnitř varianty i v kořeni.
  Pole nadále ukazuje poslední hodnotu; ostatní záznamy se zachovávají. Úprava
  zobrazeného pole nesmaže původní vnořené repetition. Duplicitní názvy variant
  nebo sekcí, které editor nemůže bezpečně zobrazit, odmítne s konkrétní chybou.
- Vzhled, nápověda názvu, upozornění na vynechané sekce, dirty state, dialogy
  přejmenování/kopie a uložené snapshoty pro hlavní aplikaci zůstaly zachované.
  V `super_presenter.py` se změnila jen datová integrace. Vykreslování projekce,
  `presentation_presenter.py` ani soubory písní nebyly změněny.

### Ověření a navazující krok

Všech 63 testů prošlo příkazem `.venv/Scripts/python.exe -B -m unittest discover -s tests`.
Regrese zahrnuje celou knihovnu 858 XML písní, nyní také převod dat do polí editoru
bez změny a zpět. Nový `tests/test_shared_editor_model.py` ověřuje surové řádky,
metadata, vnořené/duplicitní repetition a cestu uložené kopie. Prošly také stávající
GUI testy a testy původního repository. Provedena kontrola syntaxe Pythonu a diffu.

Dotčené soubory: `song_editor.py`, `super_presenter.py`, `superpresenter/domain/song.py`,
`superpresenter/services/song_repository.py`, `superpresenter/services/song_edit_session.py`,
README a testy editoru/repository/kompatibility; přidán `tests/test_shared_editor_model.py`.
Odstraněny `superpresenter/domain/editable_song.py` a `superpresenter/services/song_editor_repository.py`.

Etapa 9 je tím dokončena i po stránce společného modelu. Doporučený další krok
je ruční provozní zkouška uložit/přepnout/spustit na skutečných projektorech.
Stávající omezení (žádný autosave po pádu, hardlinky pro nový soubor) zůstávají.
Předchozí rozpracované úpravy a pomocné skripty nebyly odstraněny ani vráceny.

## Přenos kompletní etapy 9 na větev test (7. 9. 2026)

Správná cílová větev této etapy je `test`. Etapa 9 včetně všech doplňků byla
přenesena z `dev` (`78bdea3` a `fd147c3`) na základ etapy 8 (`9ac1952`).
Původní rozpracované slučování opačným směrem bylo nejprve zálohováno a ukončeno.
Záloha pracovních souborů, diffu a indexu je v místní složce
`C:/Users/moski/AppData/Local/Temp/SuperPresenter-etapa9-transfer-nb0ru8mz`.
Větev `dev` zůstala na `fd147c3`; její historie nebyla přepsána.

Přenesený rozsah:

- vložený i samostatný Song Editor, sjednocené načítání a jeden stav draftu;
- dirty state a Uložit / Zahodit / Storno při přepnutí, zavření, novém draftu
  a ukončení aplikace; kontrola také před spuštěním projekce;
- bezpečné ukládání, prázdný název, kolize, volba přejmenovat/uložit kopii,
  konkrétní chyby a opakování chybného callbacku;
- synchronizace názvu, jazyků, sekcí a repetition přes společný Song/Repository;
- šedá vycentrovaná nápověda „Název zde“, která zmizí po vstupu do pole;
- potvrditelné upozornění na vynechané sekce v každém pojmenovaném repetition;
- související datové/GUI testy a kompletní dokumentace změn.

Při řešení konfliktů v README a `super_presenter.py` byly zachovány etapy 4–8:
construct parser, připnuté řádky, stacionární stránky, navigace a časová osa.
Stacionární plán používá stejný uložený model z `onlineSources` jako ostatní
režimy, bez nového čtení souboru uprostřed přípravy projekce. Kontrola vynechaných
sekcí rozpoznává také `@v1.1`; odstranění sekce odstraní i její značku připnutí
nebo správně přečísluje přeživší připnutý odkaz. Test navigace ověřuje přípravu
kopií zdrojů a zákaz opětovného načítání modelu z disku.

Ověření na větvi `test`: všech **121 testů prošlo** příkazem
`.venv/Scripts/python.exe -B -m unittest discover -s tests` (GUI mimo sandbox).
Prošla syntaktická kompilace 24 Python souborů a kontrola diffu. Porovnání AST
potvrdilo zachování vykreslovacích tříd i metod parseru/sestavování řádků z etapy 8.
`presentation_presenter.py`, soubory písní, styly a servisní moduly etap 4–8
zůstaly proti `9ac1952` beze změny. Testy nadále zahrnují knihovnu 858 XML písní.

Přenos je dokončen místním merge commitem na `test`; push není součástí této operace.
Doporučený navazující krok je běžná ruční zkouška editoru a skutečných projektorů
na větvi `test`. Stávající omezení etapy 9 zůstávají stejná.

## Doplňky editoru: zkratky a obnova rozpracované písně (7. 9. 2026)

Na větvi `test` byly doplněny odsouhlasené body 1–4. Kontrola externích změn
souboru (bod 5) nebyla přidána. Vzhled editoru zůstává zachovaný.

- `Ctrl+S` spouští běžné uložení včetně všech potvrzení ve vloženém i samostatném
  editoru. `Ctrl+Z`, `Ctrl+Y` a `Ctrl+Shift+Z` vracejí/opakují změny textu sekce.
  Historie je samostatná pro každé textové pole, maximálně 200 kroků; počáteční
  načtení není krokem historie. Nezahrnuje odstranění celé sekce ani další pole.
- Před uložením sdílený construct parser kontroluje neexistující sekce a syntaxi
  každého neprázdného pojmenovaného opakování. Dialog uvádí konkrétní problém
  a dovoluje vědomě uložit rozpracovanou píseň. Stávající potvrzení vynechaných
  sekcí zůstává. Nejde o úplnou kontrolu rozsahů řádků ve všech jazycích.
- Změněný editor ukládá pomocnou zálohu do `.song-recovery/` přibližně jednou
  za sekundu. Složka je v `.gitignore`; původní píseň se mění jen běžným uložením.
  Záloha obsahuje pracovní i poslední čistý model a cestu; oba modely používají
  XML serializaci společného SongRepository. Zápis zálohy je atomický.
- Při příštím spuštění lze zálohu obnovit, zahodit nebo ponechat na později.
  Obnovený editor zůstává změněný. Hlavní aplikace pro prezentaci zachovává čistý
  model až do běžného potvrzení/uložení. Obnovit lze také nový neuložený draft.
  Úspěšné uložení či výslovné zahození změn odstraní příslušnou zálohu.
- Zámek zálohy rozlišuje běžící instance od ukončených; nejde o sledování změn
  původních souborů. Poškozená záloha zůstává zachovaná a zobrazí se konkrétní
  chyba. Chyba průběžného zápisu se také zobrazí, předchozí záloha zůstává.

Tato část nahrazuje dřívější omezení „žádný autosave po pádu“. Při pádu lze stále
ztratit poslední přibližně sekundu změn, při zablokované událostní smyčce nebo
chybě disku i více. Při jednom spuštění se obnoví nejvýše jedna záloha; ostatní
zůstávají pro další spuštění. Drobné soubory `.lock` mohou ve složce zůstávat.

Změněné soubory: `.gitignore`, `song_editor.py`, `super_presenter.py`,
`superpresenter/services/song_edit_session.py`,
`superpresenter/services/song_repository.py`, `tests/test_song_editor_data.py`,
`tests/test_song_editor_integration.py` a `README.md`. Přidány
`superpresenter/services/song_recovery.py` a `tests/test_song_recovery.py`.
`presentation_presenter.py`, knihovna písní a styly projekce se neměnily.
Předem změněný sledovaný bytecode editoru byl ponechán beze zásahu.

Ověření: **137 testů prošlo** příkazem
`.venv/Scripts/python.exe -B -m unittest discover -s tests` mimo sandbox.
Testy zahrnují skutečné předčasné ukončení pomocného procesu, zámky souběžných
instancí, selhání atomického zápisu, časované zálohování, obnovu draftu i existující
písně, Ctrl+S a undo/redo. Prošla kontrola syntaxe 26 Python souborů a
`git diff --check`. Fyzické projektory nebyly ověřovány.
Doporučený navazující krok: restart aplikace a běžná uživatelská zkouška zkratek
a ukládání na větvi `test`. Tyto doplňky zatím nejsou commitnuté ani pushnuté.

## Etapa 10 – rozdělení hlavní aplikace do modulů (8. 9. 2026)

Výchozí stav: větev `test`, commit `6094cf0`, dokončené předchozí etapy včetně
obnovy editoru. Předem změněný `__pycache__/song_editor.cpython-312.pyc` zůstal
beze zásahu. `presentation_presenter.py`, písně, JSON konfigurace, obrázky,
spouštěcí BAT a samostatný editor nebyly upravovány.

### Mapa závislostí a provedené přesuny

Původní soubor měl 3 338 řádků. `GUI` vytvářelo `SortingWin`, `ProjWindow`
a `WidgetSource`; projektor vytvářel čtyři projekční widgety a používal callbacky
hlavního okna. `WidgetSource` závisel na Song, repository, construct parseru
a pomocných funkcích tolerantního XML importu. Editorové callbacky sdílely stav
GUI a publikovaly uložené snapshoty. Tyto vztahy a algoritmy zůstávají zachované.

| Soubor | Odpovědnost a závislosti |
| --- | --- |
| `super_presenter.py` | 19řádkový spouštěč a kompatibilní exporty původních tříd a pomocných funkcí. |
| `superpresenter/app.py` | Logging, vytvoření GUI, nabídka obnovy editoru a hlavní smyčka. |
| `superpresenter/paths.py` | Kořen projektu pro původní cesty k prostředkům. |
| `superpresenter/ui/main_window.py` | GUI, rozložení, ovládání prezentace a koordinace existující navigace. |
| `superpresenter/ui/song_editor_panel.py` | SongEditorPanel: zděděné callbacky vloženého editoru, draft, varianty a publikování uloženého modelu. Vlastní editorové widgety dál poskytuje `song_editor.py`. |
| `superpresenter/ui/source_sorter.py` | SortingWin a přesouvání položek. |
| `superpresenter/ui/projector_widgets.py` | Widget_OneLine, Widget_FlowLines, Widget_StanzaPaged a Widget_Image. |
| `superpresenter/ui/projector_window.py` | ProjWindow, projekční okno, widgety a překrytí sbírky. |
| `superpresenter/services/presentation_session.py` | WidgetSource, nezbytný _LegacyWidgetSource a XML pomocné funkce; načtení/snapshot a původní sestavování textů bez Tkinteru. |
| `superpresenter/ui/__init__.py` | Balíček UI, bez inicializace oken. |

Importy směřují ze spouštěče přes app a hlavní okno do projektoru, widgetů
a služeb; žádný z těchto modulů neimportuje původní spouštěč. Typový odkaz
projektoru na GUI je pouze pod `TYPE_CHECKING`, za běhu se neimportuje.
Datové moduly neimportují Tkinter. Dědění SongEditorPanel zachovává původní
jména metod a tentýž stav GUI, nevytváří druhou kopii dat ani nový životní cyklus.

Zůstává stejné spuštění přes BAT nebo `python super_presenter.py`. GUI.dir
a cesta Widget_Image jsou ukotvené ke stejnému kořeni jako před přesunem,
nikoli k podsložce UI. Formáty ani význam cest v JSON se nemění. Vzhled,
klávesové zkratky, parser, generátor stránek a pravidla navigace nebyly měněny.

Dva nahodilé printy nahrazuje standardní logging do konzole; diagnostika cue
nadále vyžaduje `SUPERPRESENTER_CUE_DEBUG=1`. Konkrétní výjimky byly doplněny
jen u čtení textu, převodu float a vybraných operací Tk. Obecné ochranné bloky
kolem starého parseru a přípravy/provozu projekce zůstávají, protože jejich
zúžení bez samostatného ověření všech historických vstupů by mohlo změnit chování.
Odstraněné soukromé `_testList` a `_testProj` neměly žádné volající v aktivním
kódu ani testech; druhá obsahovala pevné testovací cesty původního autora.
Odstraněn i její zakomentovaný start a importy nepotřebné v nových modulech.

### Ověření

Python je dostupný jako `.venv/Scripts/python.exe` (příkaz `python` není v PATH).
Po každém celku byly spuštěny příslušné regrese: adaptér – 21 testů parseru;
řazení – 27 integračních testů editoru; widgety a projektor – po 27 testech
stránkování/navigace; hlavní okno a callbacky – 27 integračních testů editoru.

Kompletní sada: **142 testů prošlo**, včetně knihovny 858 XML písní, parseru,
stránkování, navigace, GUI editoru a obnovy. Nový `tests/test_module_boundaries.py`
ověřuje datové importy bez GUI závislostí, identitu kompatibilních exportů,
pořadí startu obnovy/smyčky, cestu obrázků a zákaz zpětných importů spouštěče.
`tests/test_imports.py` nyní ověřuje i nové UI moduly samostatně v čerstvých
procesech se zakázaným vytvořením Tk okna.

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests
git diff --check
```

Testy vyžadovaly běh mimo sandbox kvůli přístupu k instalovaným závislostem/Tcl.
Výchozí kompletní běh ještě před změnami zaznamenal opakované `WinError 5`
při náhradě dočasných XML souborů; závěrečný kompletní běh již prošel.
Provedena syntaktická kompilace 36 aktivních Python souborů v paměti bez zápisu
bytecode a kontrola globálních odkazů nových modulů. Porovnání AST proti HEAD
potvrdilo 125 přesně zachovaných metod; rozdíly jsou pouze popsané cesty,
logging, konkrétní výjimky a odstraněné testovací metody. Samostatný linter
není nakonfigurovaný a Ruff/Pyflakes/Flake8 nejsou nainstalované.

### Omezení a navazující krok

Fyzické projektory nebyly interaktivně ověřeny. Doporučený další krok:
spustit běžným BAT a ručně ověřit editor, řazení, oba stacionární režimy,
legacy projekci, obrázky/sbírku a klávesové ovládání na skutečných monitorech.
Hlavní okno stále koordinuje prezentační stav; jeho další případné oddělení
vyžaduje samostatnou etapu. Tolerantní import a známá omezení historických
písní i algoritmů z předchozích etap zůstávají zachována.

## Etapa 11 – monitory a projekční profily (8. 9. 2026)

Výchozí repozitář byl čistý na commitu `1560311` (etapa 10). Předchozí etapy,
písně a `presentation_presenter.py` zůstaly beze změn.

### Ovládání

Rozložení a přepínače zůstávají na původním místě. Aplikace automaticky ukládá
poslední rozložení po přidání/odebrání výstupu, změně monitoru, stylu,
fullscreen nebo QR sbírky, dále při zastavení projekce a běžném zavření.
Při příštím spuštění je obnoví; samotné promítání se stále zapíná přes F5.
Poloha přesunutého běžného okna se zachytí při Save, zastavení či zavření.

- **save** otevře dialog pro uložení celého rozložení do pojmenovaného JSON
  profilu, například `Běžná bohoslužba.json` nebo `Velikonoce.json`.
- **load** načte zvolený profil. Během promítání požádá nejprve o jeho zastavení.
  Úspěšné načtení se stane také posledním rozložením pro další spuštění.
- Pro běžný provoz nastavte sál i stream a uložte také pojmenovaný běžný profil.
  Pro Velikonoce odeberte stream a uložte zvláštní profil. Po akci načtěte běžný.
- Bez uloženého nastavení zůstává jeden výstup, první stacionární sálový styl,
  fullscreen zapnutý a QR vypnuté. Nově se přednostně vybere neprimární monitor,
  jinak hlavní (případně první dostupný). Aplikace nedokáže poznat, zda je
  neprimární displej skutečně projektor; při více externích jej vyberte ručně.

Skutečné názvy monitorů se již nepřepisují. Nabídka ukazuje polohové označení a souřadnice (viz upřesnění níže). Párování preferuje jejich úplnou shodu, potom jedinečnou
shodu názvu a rozlišení; geometrie pomáhá při nedostupném
názvu, ale nepřebírá jinak pojmenovaný monitor. Nejednoznačnost se nepovažuje
za shodu. Při chybějícím monitoru dialog vypíše dotčené výstupy a nabídne
**běžné okno na hlavním displeji, bez fullscreen a bez staré pozice**.
Odmítnutí ponechá současné rozložení. Monitory se znovu zjistí při Load i před F5.
Odpojení za již běžící projekce se průběžně nesleduje.

### Umístění a formát verze 1

Windows: `%APPDATA%/SuperPresenter/last-layout.json`; výchozí složka pojmenovaných
profilů je `%APPDATA%/SuperPresenter/profiles/`. Dialog dovolí profil přenést
jinam. Mimo Windows se používá `$XDG_CONFIG_HOME/SuperPresenter`, jinak
`~/.config/SuperPresenter`. Testy zapisují pouze do dočasných složek.

```json
{
  "version": 1,
  "outputs": [
    {
      "style": "chvály sál – stacionární",
      "monitor": {"name": "DISPLAY2", "x": 1920, "y": 0, "width": 1920, "height": 1080},
      "fullscreen": true,
      "collection": false,
      "window_position": null
    }
  ]
}
```

`outputs` uchovává pořadí 1–5 výstupů. Styl je identifikován jedinečným názvem,
nikoli indexem; jeho typ/režim a renderovací volby poskytuje validovaný katalog
stylů. `window_position` je volitelná dvojice celých souřadnic běžného okna;
pozice mimo vybraný monitor se ignoruje. Časování animace, textové zdroje,
fonty a rozměry plátna nejsou ovládacími volbami jednotlivých výstupů a zůstávají
v katalogu. Profil nekopíruje obrázky ani definice stylů, proto cílová instalace
musí obsahovat stejné pojmenované styly. Neznámá verze nebo styl je konkrétní
chyba; profil se neaplikuje částečně. Další verze bude vyžadovat explicitní
migraci, nikoli odhad struktury.

Zápis používá dočasný soubor ve stejné složce a atomickou náhradu. Chyby se
zobrazují obsluze. Po vadné nebo odmítnuté automatické obnově samotné zavření
nepřepíše původní soubor; až explicitní úprava rozložení nebo úspěšný Load
potvrdí nový stav. Původní projektový `settings.json` s jediným `monitor_index`
zůstává nedotčený jako nepoužívaný historický soubor. Index neobsahuje dost
informací pro bezpečnou migraci více výstupů, a proto se neimportuje.

### Validace a cesty

Nová služba `superpresenter/services/projection_config.py` neimportuje GUI,
Pillow ani screeninfo. Validuje strukturu profilů a katalogu, jedinečná jména,
režimy, zdroje textu, widgety, odkazy na fonty, číselné volby, QR a existenci
obrázků. Chyba katalogu uvádí jméno stylu a problém/pole; neplatný katalog
zastaví start s dialogem, aby se nepromítala neúplná konfigurace. Hodnoty
specifické pro Tk (například dostupnost fontu či název barvy) definitivně
ověřuje Tk při tvorbě projektoru; také jeho chyba uvádí styl.

`projectors_styles.json` zůstává v aplikaci jako sdílený katalog dodávaných
stylů. Všechny jeho obrázky používají `images/...`, relativně ke kořeni aplikace.
Oba obrazové renderery používají společný resolver založený na `pathlib`;
pracovní adresář nemá vliv. Absolutní cesty, cesty od kořene disku a `..` se
odmítají. Vlastní staré styly s `\\images\\...` převeďte na `images/...`.

Změněné soubory: `superpresenter/services/projection_config.py` (nový),
`superpresenter/ui/projection_profiles.py` (nový), `superpresenter/ui/main_window.py`,
`superpresenter/ui/projector_window.py`, `superpresenter/ui/projector_widgets.py`,
`projectors_styles.json`, `tests/test_projection_config.py` (nový), `README.md`.
Opraveno také odebrání právě vybraného posledního projektoru a formátování
záporných souřadnic projekčních oken.

### Ověření a další krok

Python je dostupný v `.venv/Scripts/python.exe`. Kompletní sada se spouští:

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests
```

Nové testy bez otevírání GUI pokrývají JSON round-trip, Unicode, chybnou verzi,
booleany, neznámé styly, chybějící soubory, neúspěšný atomický zápis, přenositelné
cesty, chyby katalogu, pořadí i nejednoznačnost monitorů, zrušení a přijetí
fallbacku, neměnnost názvů monitorů, více výstupů, první start a ochranu vadného
posledního nastavení. Součástí je import a načtení katalogu se zakázanými GUI
závislostmi. Testy se kvůli přístupu k instalovanému screeninfo/Tcl spouštějí
mimo sandbox; první běh uvnitř sandboxu selhal na importu screeninfo.

Fyzické projektory ani interaktivní dialogy nebyly v této etapě ručně ověřeny.
Doporučený další krok: na sborovém PC nastavit sál + stream, restartovat aplikaci,
vyzkoušet oba pojmenované profily, QR, okno na monitoru vlevo a odpojený projektor.
Stejně pojmenované a geometricky nerozlišitelné displeje nelze bez EDID/seriového
čísla spolehlivě identifikovat; aplikace při nejednoznačnosti nabídne fallback.

Závěrečný výsledek: **161 testů prošlo** (142 původních + 19 nových).
Syntaktická kompilace **39 aktivních Python souborů** v paměti prošla,
`git diff --check` je čistý. Samostatný linter není nakonfigurovaný.
Validátor 858 písní vrací kód 1: **5 obsahových chyb a 77 varování**;
XML soubory ani validátor nebyly změněny, jejich nálezy zůstávají mimo tuto etapu.
Kontrola diffu potvrdila nedotčené `songs/`, `settings.json` a
`presentation_presenter.py`. Testy fyzického promítání nenahrazují.


### Upřesnění etapy 11 – názvy podle polohy

Nabídka monitorů nově zobrazuje například `Hlavní (0, 0)`,
`Vlevo (-1920, 0)` a `Vpravo (1920, 0)`. Systémové názvy DISPLAY ani rozlišení
se nezobrazují. Polohy se určují ze souřadnic vůči hlavní obrazovce; hlavní
nemusí být fyzicky uprostřed. Při více monitorech na stejné straně přibude
`Vlevo – 1. zleva`, `Vlevo – 2. zleva` atd., počítáno od nejlevějšího
monitoru dané skupiny. Podporované jsou i polohy nahoře, dole a diagonálně;
více monitorů nad sebou se čísluje shora. Souřadnice jsou vždy uvedeny.

Názvy i dostupné monitory se přepočítají při rozbalení nabídky, při načtení
profilu a před startem projekce. Rozbalení zachová vybraný projekční výstup;
pokud jeho monitor chybí, platí dosavadní dialog bezpečného fallbacku.
Během promítání je nabídka nadále vypnutá. Technická identita v uložených
profilech zůstává stejná, změna označení nenarušuje jejich kompatibilitu.

Upraveny `projection_config.py`, `projection_profiles.py`, `main_window.py`,
`tests/test_projection_config.py` a tento README. Navíc byl izolován test
`test_main_window_wiring` v `tests/test_song_editor_integration.py` od
skutečných uživatelských profilů: první běh odhalil, že po jejich vytvoření
test editoru načítal reálné nastavení navzdory mockovaným monitorům.
Přidány kontroly polohových názvů, přepočtu při změně počtu monitorů,
svislého rozložení a zachování vybraného výstupu při obnově nabídky.
Ruční ověření připojování monitorů zůstává doporučeným navazujícím krokem.

Ověření upřesnění: **164 testů prošlo**, syntaktická kompilace 39 aktivních
Python souborů a `git diff --check` prošly. Samostatný linter není
nakonfigurovaný. Písně a `presentation_presenter.py` zůstaly beze změn.

### Upřesnění etapy 11 – editor monitorů a vlastní názvy

Původní tlačítko **save** v hlavním okně je nahrazeno **edit**. Otevírá
samostatné modální okno „Monitory a projekční výstupy“. Nahoře je mapa
obrazovek odpovídající souřadnicím a poměrům jejich rozměrů; pod ní jsou
karty řazené podle polohy vlevo/vpravo a nahoře/dole. Karty mají čitelné stejné
šířky, nemusí odpovídat fyzické velikosti monitorů. Větší rozložení se posouvá
vodorovným a svislým posuvníkem.

Každá připojená obrazovka se objeví automaticky. Na kartě lze:

- zadat vlastní název (například „Sál“, „Stream“, „Obsluha“); prázdný název
  obnoví automatické pojmenování podle polohy,
- vybrat styl nebo **Nepromítat**, což na monitoru nevytvoří projekční okno,
- nastavit fullscreen a QR sbírky; QR je dostupné u stylů, které jej podporují,
- přidat další výstup na stejnou obrazovku. Stávající vícenásobné výstupy se
  neztrácejí; každý má vlastní výběr stylu. Maximum zůstává pět aktivních výstupů.

Názvy jsou vidět také v hlavní nabídce monitorů, stále se souřadnicemi.
Systémový název ani rozlišení se do popisků nevracejí. Vlastní název nemění
hardwarovou identitu používanou k přiřazení výstupu. Názvy mohou mít nejvýše
80 znaků, bez řídicích znaků; ukládají se i pro obrazovku s volbou Nepromítat.

- **save** aplikuje celý návrh, uloží poslední nastavení pro další spuštění
  a zavře editor. Při chybě zápisu ponechá původní rozložení a otevřený návrh.
- **Uložit profil…** uloží návrh do pojmenovaného souboru pro zvláštní událost,
  ale samo nezmění aktuální rozložení ani nezavře editor.
- **Zrušit**, Escape nebo zavření okna zahodí neaplikované úpravy.
- Původní **load** zůstává v hlavním okně. Editor i Load vyžadují zastavenou
  projekci. Je dovoleno vypnout všechny výstupy; F5 pak vysvětlí, že je třeba
  nejprve některému monitoru vybrat styl.

Editor pracuje s kopií rozložení. Při jeho otevření se zjistí připojené monitory.
Změní-li se zapojení během úprav, save odmítne aplikaci na jinou sestavu;
návrh lze exportovat do profilu a editor znovu otevřít. Fyzické monitory se
přidávají připojením a povolením obrazovky v systému, nikoli vytvořením
virtuálního monitoru v aplikaci. Obnova chybějícího monitoru při otevření editoru
používá dosavadní potvrzovaný bezpečný fallback.

#### Formát verze 2

Nové snapshoty mají `version: 2`, `outputs` dovoluje 0–5 výstupů a přibývá
`monitor_names`, seznam objektů například:

```json
{
  "monitor": {"name": "DISPLAY2", "x": 1920, "y": 0, "width": 1920, "height": 1080},
  "label": "Sál"
}
```

Formát jednotlivých výstupů se nemění. Soubory verze 1 se dál validují a načítají;
při dalším uložení aplikací přejdou do verze 2. Starší aplikace podporující jen
verzi 1 nové soubory neotevře. Názvy jsou součástí konkrétního profilu, proto
načtení jiného profilu obnoví i jeho názvy; starý profil bez názvů použije
polohové označení. Jména odpojených monitorů se při editaci zachovávají.

Změněny `superpresenter/services/projection_config.py`,
`superpresenter/ui/projection_profiles.py`, `superpresenter/ui/main_window.py`,
`tests/test_projection_config.py` a README. Nové soubory:
`superpresenter/services/projection_editor_model.py` (model návrhu bez GUI),
`superpresenter/ui/projection_editor.py` (Tk editor),
`tests/test_projection_editor.py` (datové a integrační testy).
Zachovány všechny existující změny předchozích etap, písně i
`presentation_presenter.py` zůstávají nedotčené.

Integrační testy skutečných Tk widgetů ověřují přejmenování, vypnutí výstupu,
zrušení návrhu, save, chybu zápisu, export profilu a rozmístění mapy/karet.
Datové testy navíc pokrývají migraci verze 1, více výstupů na jednom monitoru,
neaktivní i odpojené monitory, přemístění pojmenovaného monitoru, limit výstupů,
validaci jmen, změnu zapojení před save a uložení prázdného rozložení.
Doporučený další krok: na sborovém PC ověřit přejmenování Sál/Stream,
profil bez streamu a znovunačtení po restartu. Testy používají skrytá Tk okna
a dočasné složky; skutečné projektory nebyly interaktivně ověřeny.

Závěrečné ověření editoru: **180 testů prošlo**, včetně 16 nových datových
 a Tk integračních testů. Syntaktická kompilace **42 aktivních Python souborů**
v paměti a `git diff --check` prošly. Python z `.venv` je dostupný; testy
běžely mimo sandbox kvůli instalovaným závislostem/Tcl. Samostatný linter
není nakonfigurovaný. Diff potvrzuje nedotčené písně, `settings.json`
a `presentation_presenter.py`.

### Upřesnění etapy 11 – přepínání a přejmenování profilů v editoru

Editor má nahoře výběr **Profil**, tlačítko **+ Nový profil** a pole **Název**.
Načítá JSON profily z uživatelské složky `SuperPresenter/profiles/`. Bez
odpovídajícího uloženého profilu nabídne současné rozložení jako nový návrh
`Profil 1`, případně další volné číslo. Nový profil kopíruje uložené rozložení
vybraného profilu a dostane další volný název `Profil N`. Název lze přepsat;
uloží se tlačítkem Save nebo Save and use. Duplicitní názvy bez ohledu na
velikost písmen se odmítají.

- **Save** uloží vybraný profil a ponechá editor otevřený. Lze hned přepnout
  na jiný profil, upravit jej a opět uložit. Aktuální projekční rozložení
  aplikace se tím nemění.
- **Save and use** uloží vybraný profil, použije ho jako aktuální rozložení,
  zapamatuje jej pro příští start a zavře editor. Pokud uložení profilu uspěje,
  ale jeho použití selže (například se změnilo zapojení), profil zůstane uložený
  a editor otevřený s chybou; aktuální rozložení se nepřepne.
- Přepnutí profilu, vytvoření nového a zavření editoru při neuložených úpravách
  nabídne uložit / zahodit / zrušit. Chyba uložení zabrání přechodu a návrh zůstane.
- Výběr profilu v editoru sám neaktivuje promítání ani nemění současné rozložení.

Přidávání dalších výstupů na stejné obrazovce bylo odstraněno. Každá karta má
jeden výběr stylu nebo Nepromítat. U staršího profilu s více výstupy na jedné
připojené obrazovce editor viditelně upozorní na převod: nabídne první styl,
obsluha může zvolit jiný, a až Save uloží jeden zvolený výstup. Načtení souboru
samotné jeho obsah nemění. Výstupy odpojených monitorů se při editaci jiného
profilu zachovají, aby se jejich konfigurace neztratila. Takový profil lze
uložit; před Save and use je třeba monitor připojit nebo použít hlavní Load,
který nabízí dosavadní bezpečný fallback.

Profily nadále používají verzi 2, doplněnou o volitelné `profile_name`.
Starší soubory bez tohoto pole se zobrazí názvem souboru. Nový soubor má
čitelný název odvozený z prvního uloženého názvu profilu; znaky nevhodné pro
soubor se nahradí. Při pozdějším přejmenování se změní `profile_name` ve stejném
souboru, takže nevznikne kopie; fyzický název souboru zůstane původní. V editoru
se vždy ukazuje aktuální název profilu. Chybný soubor zůstane ve výběru a při
pokusu o otevření ukáže konkrétní chybu bez nahrazení současného návrhu.

Změněny `superpresenter/ui/projection_editor.py`,
`superpresenter/ui/projection_profiles.py`,
`superpresenter/services/projection_editor_model.py`,
`superpresenter/services/projection_config.py`, `tests/test_projection_editor.py`
a README; přidán `superpresenter/services/projection_profile_catalog.py`.
Testy pokrývají úpravu více profilů po sobě, přejmenování bez kopie, automatická
čísla, kolize názvů, zrušené přepnutí, chybu Save, oddělení Save od použití,
starší i vadné soubory a bezpečné odvození cesty z názvu.

Doporučený další krok: v editoru vytvořit běžný profil a profil bez streamu,
oba uložit, přepnout mezi nimi a přes Save and use ověřit použití na skutečných
monitorech. Předchozí změny zůstaly zachované; písně ani
`presentation_presenter.py` se neměnily.

Závěrečné ověření této úpravy: **189 testů prošlo**, syntaktická kontrola
**43 aktivních Python souborů** v paměti a `git diff --check` prošly.
Python z `.venv` je dostupný. Testy běžely mimo sandbox kvůli Tcl/Tk a
instalovaným závislostem; samostatný linter není nakonfigurovaný.

### Upřesnění etapy 11 – QR v editoru a mazání profilů

Z editoru monitorů byl odstraněn přepínač QR sbírky. Fullscreen zůstává.
Existující hodnota QR v profilu se při editaci zachovává kvůli kompatibilitě;
tato úprava nemění ovládání sbírky v hlavním okně ani renderer.

Nahoře je tlačítko **Smazat profil**. Potvrzení uvádí název vybraného profilu
 a upozorňuje i na zahození jeho neuložených úprav. Smaže pouze vybraný JSON
ve spravované složce profilů; používané rozložení ani last-layout.json nemění.
Po smazání se otevře další čitelný profil, případně vznikne neuložený návrh
Profil 1 z aktuálního rozložení. Chyba mazání zachová výběr i návrh.
Mazání není vratné přes editor; důležitý profil předem zálohujte.

Dotčené soubory: `superpresenter/ui/projection_editor.py`,
`superpresenter/services/projection_profile_catalog.py`,
`tests/test_projection_editor.py` a README. Doplněny testy absence QR přepínače,
zachování fullscreen/uložené QR hodnoty, potvrzení a zrušení mazání,
chyby mazání, posledního profilu a odmítnutí mazání mimo složku profilů.
Doporučený navazující krok: vyzkoušet smazání pomocného profilu v editoru.

Ověření: **195 testů prošlo**, syntaktická kompilace **43 aktivních Python
souborů** a `git diff --check` prošly. Python je dostupný v `.venv`;
samostatný linter není nakonfigurovaný. Testy používají dočasné soubory
a skrytá Tk okna. Písně a `presentation_presenter.py` zůstávají nedotčené.

### Upřesnění etapy 11 – kompaktní vzhled editoru

Editor monitorů používá šedé pozadí hlavního okna, tmavě šedá tlačítka,
bílé popisky a stejný základní font `listfont` / `buttfont` (Courier New 14).
Styly mají vlastní prefix Projection, takže nepřepisují vzhled ostatních oken.
Ovládání profilů je ve dvou řádcích, informace a akční tlačítka dole také.

Výchozí šířka se odvozuje od skutečně potřebné šířky karet a hlavičky: pro jeden
monitor je okno užší, více monitorů vedle sebe dostane více prostoru, nejvýše
šířku displeje s okrajem. Výška se odvozuje od obsahu a dostupné obrazovky;
posuvníky zpřístupní obsah, který se nevejde. Okno lze dále ručně zvětšovat.

Každá obrazovka má nyní náhled přímo nad svým nastavením ve společné kartě.
Nastavení je přesně o 24 px širší než náhled, tedy 12 px na každé straně.
Celá sestava karet se v okně centruje a při posouvání zůstává zarovnání stejné.
Polohy karet vlevo/vpravo a nahoře/dole nadále odpovídají pořadí systémových
souřadnic. Náhledy mají sjednocenou čitelnou velikost, nejsou už měřítkovou mapou
poměrů rozlišení monitorů. Vlastní název i souřadnice zůstávají viditelné.

Změněny `superpresenter/ui/projection_editor.py`,
`tests/test_projection_editor.py` a README. Doplněny kontroly fontu/barvy,
symetrických okrajů a užšího okna pro jeden monitor. Doporučený další krok:
ručně ověřit vzhled na používaném monitoru a při jeho nastavení DPI;
testy geometrie pracují s Tk okny mimo viditelnou plochu.

Ověření vzhledu: **198 testů prošlo**, syntaktická kontrola **43 aktivních
Python souborů** a `git diff --check` prošly. První kompletní běh odhalil
chybu měření skrytého Tk okna (1×1); test nyní měří rozložené okno mimo
viditelnou plochu. Python v `.venv` je dostupný, samostatný linter není
nakonfigurovaný. Profily, písně ani `presentation_presenter.py` tato vizuální
úprava nemění.

### Upřesnění vzhledu – spodní tlačítka

Spodní akce editoru jsou vycentrované a pojmenované **Uložit**, **Použít**
a **Zrušit**. Význam se nemění: Uložit ukládá vybraný profil; Použít jej
uloží a aktivuje. Také nápověda používá české názvy. Tlačítka editoru mají
plochý styl bez světlého orámování, včetně aktivního/stisknutého stavu.
Změněny `superpresenter/ui/projection_editor.py` a README. Doporučený další
krok: vizuálně ověřit běžný i aktivní stav tlačítek při používaném DPI.

Ověření: **198 testů prošlo**, syntaktická kontrola **43 aktivních Python
souborů** a `git diff --check` prošly. Samostatný linter není nakonfigurovaný.
Písně a `presentation_presenter.py` zůstávají beze změny.

### Upřesnění etapy 11 – monitory bez restartu aplikace

Aplikace každé **2 sekundy** zjišťuje aktuálně připojené a systémem povolené
obrazovky. Nově připojený projektor se automaticky objeví v hlavní nabídce
monitorů i v již otevřeném editoru. V editoru začíná nový monitor s volbou
Nepromítat; obsluha mu vybere styl a stiskne Použít. Výstupy se automaticky
nepřidělují nově připojenému zařízení. Interval není okamžitá systémová událost:
k prodlevě se přičítá doba, než monitor rozpozná operační systém.

Při změně pořadí se existující výstupy znovu přiřadí podle technické identity,
nikoli podle starého indexu. Přidání nepoužívané obrazovky nepřerušuje projekci.
Pokud používaný monitor zmizí nebo změní polohu či rozlišení, aplikace promítání
zastaví a upozorní obsluhu. Odpojený monitor nabídne dosavadní potvrzovaný
fallback; projekce se po změně sama nespustí. Automatická obnova nepřepisuje
poslední uložené rozložení nouzovým stavem. Odmítnutí fallbacku nevyvolává znovu
stejný dialog každé dvě sekundy; lze znovu otevřít nabídku/Load nebo změnit zapojení.

Otevřený editor aktualizuje karty i velikost okna a uchová rozpracované názvy,
styly a fullscreen. Odpojený výstup uchová v návrhu a po opětovném připojení
jej znovu zobrazí. Neplatné rozpracované údaje se nezahazují: editor vypíše,
že se seznam obnoví po jejich opravě. Během otevřeného editoru se přes něj
neotevírá automatický fallback dialog hlavního okna. Chyba detekce ani prázdný
výsledek nepřepíšou známou konfiguraci; další kontrola proběhne později.
Časovač běží v Tk hlavní smyčce a při ukončení aplikace se ruší.

Změněny `superpresenter/ui/projection_profiles.py`,
`superpresenter/ui/projection_editor.py`, `superpresenter/ui/main_window.py`,
`tests/test_projection_editor.py`, `tests/test_song_editor_integration.py`
a README. Přidán `tests/test_monitor_refresh.py`. Integrační test editoru písní
má detekci monitorů izolovanou, aby nepracoval s reálnou sestavou uživatele.
Doplněno devět testů pro připojení, přečíslování, odpojení/přemístění aktivního
výstupu, dočasnou chybu detekce, obnovu návrhu a zrušení časovače.

Ověření: **207 testů prošlo**. Připojování a odpojování se simuluje; fyzický
projektor nebyl v této etapě připojován. Doporučený další krok: nechat aplikaci
i editor otevřené, připojit projektor, vyčkat několik sekund a přiřadit mu styl.
Písně a `presentation_presenter.py` zůstávají nedotčené.

Syntaktická kontrola **44 aktivních Python souborů** a `git diff --check`
prošly. Python z `.venv` je dostupný; samostatný linter není nakonfigurovaný.

## Etapa 12 – obnovená stabilizace pouze na pozadí (9. 9. 2026)

Tato verze obnovuje technické opravy po nechtěném zahození předchozí stabilizace.
Podle nového zadání **nemění popisky, tlačítka, grafiku, rozložení, klávesové
zkratky ani způsob ovládání**. Tlačítko `prezentace` i jeho spouštěcí příkaz
zůstávají zachované. `presentation_presenter.py` bude řešen samostatně a nebyl
upraven. Oproti zahozenému pokusu se do původního streamu nepřidává nový prázdný
krok mezi písněmi a nepřidávají se nové chybové dialogy.

Výchozí commit: `3979f14`. Při zahájení byla přítomna pouze změna sledovaného
`__pycache__/song_editor.cpython-312.pyc`; byla ponechána. Historie etap výše
zůstává zachovaná. Písně, styly a uživatelská nastavení se nemění.

### Co bylo opraveno

- Třídění pracuje s kopií pořadí. Dosavadní dialog uložit/zahodit/zrušit tak
  skutečně rozhoduje, zda se změna publikuje do playlistu; zahození už nemění
  pořadí na pozadí. Zachová se vybraná píseň. Pozice mimo začátek seznamu se
  omezí na první položku.
- Původní pohyblivé režimy sdílejí výpočet indexů pro animované a okamžité
  přepnutí. Odstraněna chybná speciální větev stacionárního streamu ve staré
  cestě a odhad sloky ze špatně indexované mapy párů. Stacionární režimy
  nadále používají svou společnou časovou osu.
- Interní koncový index odpovídá řádkům náhledu, nikoli počtu komprimovaných
  párů/stránek. Poslední pár původního streamu se už neposuzuje jako konec
  před jeho zobrazením. Po posledním páru se dál přechází rovnou na další
  píseň; metody nextStep/prevStep a přepínání písní nebyly změněny.
- Konstrukce streamu nevrací texty dvojřádků jako metadata jazyků. Tato záměna
  vypínala párovou navigaci; při více jazycích navíc používala neinicializované
  proměnné. Do stávajícího výběru se vracejí správná jazyková data, bez změny
  samotného widgetu nebo jeho popisku.
- Před párováním streamu se rozbalí existující mapa opakování. Opakované řádky
  tak nezpůsobí IndexError při delší sekvenci kroků než počet uložených textů.
  Původní značky opakování včetně `×3` zůstávají zachované.
- Zastavení i ukončení ruší čekající animaci a zavírají projekční okna;
  selhání jednoho výstupu nebrání pokusu zavřít další. Při nečekané chybě
  startu se nejprve uklidí stav a chyba pokračuje do dosavadní obsluhy.
  Tk callback se zaloguje, případná projekce zastaví a použije se původní
  Tk reportování chyby. Nové dialogy se neotevírají.
- Opožděná událost výběru jazyka náhledu po zastavení se bezpečně ignoruje.
  Ochrana neuložených změn i ukončování otevřeného editoru prezentací zůstávají.
- Doplněny logy chyb načítání, konstrukce prezentace, ukládání, synchronizace
  a ukončení. Výjimky mají traceback; načítání a ukládání uvádí cestu.
- Odstraněny nepoužívané `_line_to_pair`, `get_long_step_from_line` (po opravě
  mapování), `positions0`, demonstrační spuštění časové osy a jednorázové
  přepisovací skripty `.update_editor_hints.py` a `.update_hint_tests.py`.
  Parserová testovací reference a používané kompatibilní větve zůstaly.
  V dotčených aktivních souborech nebyly nalezeny zakomentované lokální cesty.

### Logování a opakování kontrol

Při startu hlavní aplikace i samostatného editoru vzniká UTF-8 log
`%APPDATA%/SuperPresenter/logs/superpresenter.log`. Rotuje po 2 MB, uchovává
nejvýše tři zálohy. Obsahuje čas, závažnost a modul. Import knihoven soubor
nevytváří. Pokud nelze otevřít log, použije se konzole; samotná chyba logování
nezablokuje start. Pro zachování rozhraní se neměnily existující texty dialogů.

```bat
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B scripts/validate_songs.py --details
.venv\Scripts\python.exe -B scripts/check_python.py
git diff --check
```

Python **3.12.14 v `.venv` je dostupný**. Testy byly spuštěny mimo sandbox kvůli
přístupu k instalovaným závislostem a Tcl/Tk. Výchozích **207 testů prošlo**;
závěrem prošlo všech **222 testů** (15 nových), bez přeskočení. Záměrně
simulované chyby mohou vypsat tracebacky do konzole; výsledek celé sady je `OK`.
Test startu mockuje novou konfiguraci logování, aby nepsal do uživatelského logu.

Statická kontrola **47 aktivních Python souborů a 63 importovaných modulů**
prošla. Kompiluje se v paměti, nevzniká pycache. Kontrola rozlišuje platformní
`fcntl`/`msvcrt`; neověřuje typy ani všechny dynamické atributy. Skutečné importy
hlavních modulů navíc kontroluje existující procesově izolovaný test. Samostatně
prošla syntaxe `presentation_presenter.py` a `oprava_xml_tagu.py`, bez jejich
spuštění nebo změny. Samostatný linter není nakonfigurován. `git diff --check`
prošel; rozdíl ve sledovaném pycache pochází už z výchozího stavu.

### Co je automaticky a ručně ověřeno

| Scénář | Rozsah ověření |
| --- | --- |
| Jedna a více písní | Hlavní GUI, jedno- i dvoupísňový běh, databázová kompatibilita |
| Pořadí playlistu | Potvrzení a zahození změny, zachování vybrané písně |
| Jazykové varianty | Výběr a obsah stránky, dvoujazyčný původní stream, kombinace jazyků ve stávajících testech |
| Původní sál a stream | Skutečná Tk/Canvas okna všech čtyř pohyblivých stylů; okamžité a animované indexy |
| Stacionární sál, stream a oba současně | Tk okna i datové kontroly společné časové osy |
| Vpřed/zpět a přechody mezi písněmi | Navigace v GUI, poslední pár původního streamu a návrat na předchozí píseň |
| Více než 8 řádků, dělení po 4 | Desetiřádková píseň, stávající datové testy obsahu a hranic stránek |
| Připnuté řádky | Stávající parserové, stránkovací a integrační testy |
| Editace, uložení, neuložené změny | Tk editor, round-trip, atomický zápis a simulované chyby; zrušení zavření |
| Více monitorů | Simulované připojení/odpojení, profily a topologie ve stávajících testech |
| Ukončení během prezentace | Zavření projekčních oken, zrušení animace a monitorového časovače |
| Chyba a restart | Úklid po selhání startu/callbacku, opětovné spuštění, log a rotace |
| Tlačítko prezentací | Původní text, umístění v gridu a spuštění stejného souboru; proces je v testu mockovaný |

Navíc proběhlo porovnání AST s výchozím commitem: **14 definic vzhledu,
ovládání, navigace a otevření presentation presenteru je totožných**.
V upravených GUI souborech jsou stejné všechny existující výskyty nastavování
vzhledu/rozložení, vazeb a dialogů. Nedotčené jsou `gui_style.json`,
`projectors_styles.json`, `settings.json` a `presentation_presenter.py`.

Ruční kontrola zahrnovala kód, diff a návaznosti odstraněných funkcí.
**Interaktivní ruční zkouška na fyzické projekční sestavě neproběhla.**
Automatická Tk okna byla mimo viditelnou plochu, monitory simulované a písně
v dočasné složce. Čitelnost, animaci na plátně, HDMI/hotplug, DPI, skutečný
fullscreen, zachytávání streamu, dlouhodobý provoz a distribuční EXE to neověřuje.

### XML a známá omezení

Validováno všech **858 XML: 0 syntaktických chyb, 5 obsahových chyb a 77 varování**.
Validátor vrací **1** kvůli stejným obsahovým nálezům jako před stabilizací:

- `songs/.xml`: prázdný název.
- `songs/chci_oslavovat+hevenu_salom.xml`: prázdná sekce `v3` druhé varianty.
- `songs/je_jeden_hlas_co_mel_by_znit.xml`: neexistující `r1` druhého opakování.
- `songs/Kancionálky/110 - Pán Jeºíτ p²ijde zas.xml`: neexistující `v4`.
- `songs/moc_cest_a_slava.xml`: neexistující `r1`.

Varování: 13 chybějících opakování a 64 složených výrazů nevyhodnocovaných
jednoduchým validátorem. Neznamenají automaticky neplatný construct; parser má
samostatné testy. Obsah ani zamýšlené odkazy nebyly domýšleny. Správce písní musí
nálezy rozhodnout před jejich použitím. Round-trip databáze ověřuje zachování
modelu a originálů, nikoli obsahovou správnost každé písně.

### Krátký manuální checklist před akcí

- [ ] Zálohovat písně, styly a uživatelské profily; zvolit ověřený playlist.
- [ ] Připojit projektor i stream, v systému zapnout rozšířenou plochu;
  dosavadním `edit` ověřit monitor, styl, fullscreen a použít správný profil.
- [ ] Načíst jednu i více písní, jazyky a pořadí. Zkusit také zahození změny pořadí.
- [ ] Projít původní sál/stream a stacionární sál/stream jednotlivě i současně.
  Ověřit čitelnost, správný monitor a přechody vpřed/zpět mezi písněmi.
- [ ] Promítnout sloku delší než 8 řádků, stream po 4 řádcích, opakování
  a připnutý řádek; ověřit poslední řádky a návrat zpět.
- [ ] Na kopii písně ověřit editaci, uložení, znovunačtení a neuložené změny
  s uložit/zahodit/zrušit. Originál musí zůstat zachovaný.
- [ ] Před akcí zkusit odpojení a návrat monitoru, F5/Escape, zavření během
  prezentace a restart. Zkontrolovat log a mít záložní provozní kopii.

### EXE a doporučený další krok

EXE nebylo vytvořeno ani aktualizováno. Nejprve doporučeno testovací **onedir**
sestavení na cílových Windows s konzolí; windowed sestavení až po ověření.
Zafixovat ověřené verze závislostí, připravit `.spec`, přibalit potřebné Tcl/Tk,
Pillow, screeninfo, JSON styly/nastavení a obrázky podle stylů. Editovatelné písně
musejí zůstat v trvalém zapisovatelném umístění; před onefile balením oddělit
uživatelská data od přibalených zdrojů, které se rozbalují do dočasné složky.
Viz [režimy PyInstalleru](https://pyinstaller.org/en/stable/operating-mode.html)
a [cesty za běhu](https://pyinstaller.org/en/stable/runtime-information.html).

Otestovat čistý počítač bez Pythonu, diakritiku v cestách, jiný pracovní adresář,
uložení/restart a fyzické výstupy. Přechod do presentation presenteru zůstává
ve zdrojové aplikaci; jeho subprocess používá `sys.executable`, což v EXE není
Python interpreter. Jeho samostatné balení a spuštění bude potřeba vyřešit
v navazujícím projektu, nikoli odstranit jeho tlačítko. Další krok je fyzická
zkouška podle checklistu, rozhodnutí obsahových nálezů a následné samostatné
opravy presentation presenteru a distribuce.

### Dotčené soubory

Upraveny `superpresenter/ui/main_window.py` (pouze vnitřní logika),
`superpresenter/ui/source_sorter.py` (kopie pořadí),
`superpresenter/services/presentation_session.py`,
`superpresenter/services/stationary_pages.py`, `superpresenter/app.py`,
`song_editor.py`, `tests/test_module_boundaries.py` a README.
Přidány `superpresenter/logging_setup.py`, `scripts/check_python.py`,
`tests/test_release_stability.py`. Odstraněny `.update_editor_hints.py`
a `.update_hint_tests.py`. Předexistující změna pycache byla ponechána.

## Etapa 13A – ovládání hlavního okna a vloženého editoru (10. 9. 2026)

Výchozí větev `test`, HEAD `baa90bb`. Při zahájení už byly necommitované
úpravy `song_editor.py`, `superpresenter/ui/main_window.py`,
`superpresenter/ui/song_editor_panel.py`, `tests/test_song_editor_integration.py`,
nový `tests/test_main_controls.py` a logy `test-13a.log` a
`test-13a-controls.log`. Rozpracovaná implementace byla zachována a dokončena;
staré logy zůstávají jako historické výsledky, nikoli závěrečné ověření.

### Výsledek

- Dirty state přidává prezentační hvězdičku k názvu a vedle editovatelného pole.
  Uložení, zahození, přepnutí písně a obnova draftu aktualizují indikaci.
  Hvězdička se nikdy nepřidává do StringVar názvu, modelu ani XML.
- Levý Listbox má svislý i vodorovný posuvník. Změna kroku a načtení náhledu
  vracejí xview na nulu; ruční posun funguje až na konec dlouhého řádku.
- Počítadlo ukazuje `0 / y`, skutečné kroky `x / y` a koncový stav `Konec`.
  Prázdná píseň začíná `0 / 0`. Počítají se existující kroky příslušného režimu,
  bez úvodního a koncového prázdného stavu; navigace ani výstupy se nemění.
- SongEditor vytváří tlačítka Sloka/Refrén/Bridge pod sekcemi a nad Opakováním
  ve vloženém i samostatném použití. Za kontejnerem opakování je původní text
  nápovědy a Uložit. Přidávání/odebírání opakování toto pořadí nemění.
- Ve vloženém editoru je Přidat variantu vedle Variant 2; všechny tři výběry
  jazyků zůstaly. Funkce přidání jazyka je původní.
- Start uzamkne editaci, sekce, opakování, construct, varianty, playlist
  a konfiguraci projekce. Pamatuje si původní stavy včetně disabled/readonly.
  Navigace, náhled, zastavení a sbírka zůstávají dostupné. Ctrl+S a textové
  undo/redo respektují zámek. Opožděný výběr prezentační varianty se ignoruje.
  Již otevřené dialogy mají zamčené prvky; řazení nelze publikovat během běhu.
  Zastavení i chyba startu/callbacku obnoví uložené stavy ovládání.

### Soubory a ověření

Implementace: `song_editor.py`, `superpresenter/ui/main_window.py`,
`superpresenter/ui/song_editor_panel.py`.
Testy: nový `tests/test_main_controls.py`, doplněné
`tests/test_song_editor_integration.py` a `tests/test_stationary_navigation.py`.
Dokumentace: tento README. Závěrečný lokální log: `stage13a-verification.log`.

- `.venv\Scripts\python.exe -B -m unittest discover -s tests -v`:
  **231 testů, OK, bez přeskočení**. GUI testy spuštěny mimo sandbox, kde
  fungují screeninfo a Tkinter. Sada zahrnuje regresní databázové kontroly,
  šest dodávaných stylů, kombinaci výstupů, layout samostatného editoru,
  dirty indikaci, posuvník a obnovu ovládání po běžném i chybovém ukončení.
  Mapovaný Listbox se testuje v okně mimo obrazovku: nezobrazené Tk okno
  neposílá aktualizaci polohy do posuvníku. Testovací náhrady GUI byly doplněny
  o nový stav běhu/zámku; skutečné zamykání ověřují integrační Tk testy.
- `.venv\Scripts\python.exe -B scripts/validate_songs.py --details`:
  **858 XML, 1 chyba, 77 varování**, návratový kód 1. Jediná chyba je očekávaný
  prázdný název v `songs/.xml`, který zůstává beze změny. Varování: 13 chybějících
  opakování a 64 výrazů mimo jednoduchou analýzu validátoru. Tento aktuální
  výsledek nahrazuje historický počet pěti obsahových chyb uvedený výše.
- `.venv\Scripts\python.exe -B scripts/check_python.py`:
  **48 Python souborů, 64 importovaných modulů, 0 chyb**.
- `git diff --check`: prošel. Bez změn v XML, parseru, službách stránkování,
  navigaci, projekčních oknech, JSON konfiguraci a `presentation_presenter.py`.

Fyzická projekční sestava, DPI a interaktivní vizuální zkouška nebyly ověřeny.
EXE nebylo aktualizováno. Živé promítání rozepsaných změn, vyhledávání ani
nastavení počtu řádků nebyly přidány. Změny nejsou commitované.
Doporučeno krátce ověřit layout a dlouhý řádek na monitoru obsluhy, potom 13B.

### PŘEDÁNÍ PRO DALŠÍ CHAT – Etapa 13B

Pracuj v SuperPresenter na větvi test. Nejprve přečti Git status/diff a poslední
předání README; zachovej všechny necommitované změny dokončené Etapy 13A.
13A přidala dirty hvězdičku, horizontální posuvník a reset náhledu doleva,
čítač 0 / y → x / y → Konec, přesun sekčních tlačítek/nápovědy/Přidat variantu
 a zámek editace během projekce s obnovou původních stavů i po chybě.
Pokračuj vyhledáváním písní v Etapě 13B podle konkrétního nového zadání.
Respektuj dirty přechody a zámek; neměň presentation_presenter.py, XML,
construct parser, limity 8/4 ani projekční grafiku. Počet řádků patří do 13C.
Výchozí ověření: 231 unittest OK; validátor 858 XML, očekávaná chyba songs/.xml
 a 77 varování; check_python 48 souborů/64 modulů/0 chyb; diff --check OK.
Tk/screeninfo testy může být nutné spouštět mimo sandbox. Závěrečný log 13A
je stage13a-verification.log; starší test-13a*.log obsahují neúspěšné pokusy.

### Úprava 13A podle obsluhy – šířka, mezery a editace během projekce

Toto upřesnění nahrazuje výše popsaný plošný zámek 13A. Při promítání se
zamyká pouze nastavení projekce (výstupy, monitory, styly, profily, fullscreen).
Editor písní, ukládání včetně Ctrl+S, undo/redo, sekce, opakování, jazykové
varianty a správa/řazení playlistu zůstávají dostupné. Uložení a příprava dalších
změn nemění snapshot ani časovou osu právě běžící prezentace; projeví se při
novém spuštění. Původní stavy nastavení projekce se obnoví i po chybě.

Roztažení okna způsobovala zejména dirtyLabel: převzala ze sourcesLabel také
šířku celého názvu (v testovací sestavě 420 px). Indikátor má nyní šířku dvou
znaků. Nápověda používá původní font vloženého zobrazení a může se zalomit
v šířce 640 px, její obsah zůstává stejný. Nad Sloka/Refrén/Bridge je mezera
20 px, před Přidat variantu rovněž 20 px. Zachovány všechny dřívější změny
 i předexistující změna sledovaného pycache; presentation_presenter.py nedotčen.

Pro další chat: 13B musí respektovat nově otevřenou editaci během projekce;
nezavádět zpět plošný zámek. Zámek se týká jen konfigurace výstupů.

Ověření tohoto upřesnění: 232 unittest OK (GUI mimo sandbox), včetně měření šířky a mezer a uložení během běhu bez změny plánu. check_python: 48 souborů, 64 modulů, 0 chyb. Validátor: 858 XML, očekávaná chyba songs/.xml a 77 varování. git diff --check prošel. Log: stage13a-layout-verification.log. Fyzické projektory nebyly zkoušeny.

### Fullscreen za běhu (upřesnění 13A)

Checkbox fullscreen zůstává dostupný i během prezentace. Jeho změna nyní
okamžitě přepne existující projekční okno mezi bezrámovým zobrazením přes
monitor a běžným oknem; dříve callback pouze ukládal příznak. Při prvním
zmenšení použije 80 % rozměrů monitoru, při dalším návratu obnoví zapamatovanou
geometrii okna. Canvas, aktuální krok ani připravený plán se nevytvářejí znovu.
Tlačítko Přidat variantu má šířku 18 znaků, aby se celý popisek vešel.
Pro další chat: fullscreen je výjimka ze zámku nastavení promítání.
Upraveny main_window.py, test_main_controls.py a README. Uživatelský nový
songs/kghigkgik.xml a všechny předexistující změny byly ponechány.

Ověření: 233 unittest OK (mimo sandbox), check_python 48 souborů / 64 modulů / 0 chyb, git diff --check OK. Log: stage13a-fullscreen-verification.log. Fyzická projekční sestava nebyla zkoušena.

## Etapa 13B – hledání podle názvu a textu

Před implementací ověřeny Git status, historie a necommitnuté změny 13A
(HEAD `baa90bb`). Platí poslední upřesnění 13A: playlist a editor jsou dostupné
během prezentace, zamyká se konfigurace výstupů s výjimkou fullscreen.
Vyhledávání tuto politiku zachovává; přidání neovlivní běžící snapshot ani plán.

Vedle `order` je `⌕ Hledat`; původní `+` zůstává a tlačítko editoru prezentací
má popisek `prez` se stejným callbackem. Samostatné okno zobrazuje název,
místo shody (název/soubor/jazyk a sekce) a původní úryvek do 152 znaků.
Dotaz se zpracuje po 200 ms nebo Enterem. Dvojklik/Přidat používá `loadSource`,
včetně validace a potvrzení neuložených změn. Písně v aktuálním playlistu jsou
označené a opakované přidání stejné cesty je odmítnuté; jiné soubory se stejným
názvem zůstávají samostatnými písněmi.

`superpresenter/services/song_search.py` neimportuje Tkinter. Paměťový index
vzniká přes společný SongRepository a Song při otevření okna ve vlákně,
Tk obsluhuje pouze hlavní vlákno. Prochází rekurzivně produkční `songs`
pod kořenem projektu, nikoli sousední `Testovací písně`. Záměrný `songs/.xml`
se tiše přeskočí; další neindexovatelné soubory se logují jednotlivě a okno
ukáže jen počet. Dotazy už XML neparsují.

Normalizace: Unicode casefold, odstranění diakritiky pouze latinky,
sjednocení bílých znaků. Ukrajinské й/ї a ostatní nelatinkové znaky zůstávají
zachované. Všechna slova dotazu musí být podřetězci jednoho prohledávaného
pole, v libovolném pořadí; hledají se všechny sekce všech jazyků. Relevance:
přesný název → začátek názvu → všechna slova v názvu → soubor → sekce.
Při shodě relevance rozhoduje normalizovaný název, původní název a úplná cesta.

**Obnova indexu:** zavřít a znovu otevřít Hledat. Nové okno vždy načte nový
index, takže zahrne uložené změny, nové písně, přejmenování i externí úpravy.
Pouhé přesunutí již otevřeného okna do popředí index neobnovuje. Během jeho
otevření představují výsledky snapshot knihovny; přidání čte aktuální soubor.
Není zavedená databáze, závislosti ani index při importu.

Omezení: žádné fuzzy hledání ani skloňování; slova se nekombinují mezi různými
sekcemi či jazyky. Dlouhý úryvek nemusí ukázat všechna daleko vzdálená slova.
Index neověřuje celou prezentační použitelnost, kterou kontroluje stávající
načítací cesta při přidání. Vizuální zkouška na fyzické projekční sestavě a EXE
nebyly součástí ověření.

Soubory 13B: nové `superpresenter/services/song_search.py`,
`superpresenter/ui/song_search_window.py`, `tests/test_song_search.py`,
`tests/test_song_search_window.py`; upravené `superpresenter/ui/main_window.py`,
`tests/test_release_stability.py` (očekávaný popisek prez) a README.
Log ověření: `stage13b-verification.log`. Předexistující úpravy, uživatelský
`songs/kghigkgik.xml` i sledovaný pycache zachovány. `presentation_presenter.py`,
Song Editor, XML, limity 8/4 a projekční logika touto etapou nezměněny.

### PŘEDÁNÍ PRO DALŠÍ CHAT – Etapa 13C

Pracuj v SuperPresenter; nejprve přečti Git status/diff a poslední části README.
Zachovej necommitnuté změny 13A/13B a uživatelská data. 13B přidává Hledat
vedle order, ponechává + a zkracuje prezentace na prez. Služba SongSearch
indexuje pouze produkční songs přes SongRepository; okno načítá index ve
vlákně a obnovuje jej při novém otevření. Přidávání používá loadSource,
respektuje dirty potvrzení a odmítá stejnou cestu už přítomnou v playlistu.
Platí konečné upřesnění 13A: během prezentace se smí upravovat editor/playlist,
změny nemění běžící snapshot. Zamčené jsou výstupy kromě fullscreen.
13C má navázat nastavením počtu řádků podle konkrétního zadání; dosavadní
limity 8/4 nebyly v 13B změněny. Nezasahuj do presentation_presenter.py.
Tk/screeninfo testy spouštěj mimo sandbox, pokud v něm nejsou dostupné.

### Závěrečné ověření 13B (10. 9. 2026)

- Celá sada `.venv\Scripts\python.exe -B -m unittest discover -s tests -v`:
  **243 testů OK, bez přeskočení**, mimo sandbox (Tkinter/screeninfo).
  První běh odhalil staré očekávání popisku prezentace a dočasné WinError 5
  při atomickém přepisu dočasného XML v databázovém testu. Očekávání změněno
  na prez; opakovaná celá sada prošla bez úpravy repository a XML dat.
- Validátor produkce: **859 XML, 1 očekávaná chyba songs/.xml, 77 varování**,
  návratový kód 1. O jeden soubor více oproti historickému souhrnu 13A kvůli
  předexistujícímu uživatelskému songs/kghigkgik.xml.
- `scripts/check_python.py`: **52 souborů, 67 modulů, 0 chyb**.
- `git diff --check`: OK. `presentation_presenter.py` a sledované XML bez diffu.
- Skutečný produkční index: **858 písní, 0 selhání**, záměrný .xml vynechán;
  vytvoření přibližně **0,8 s**. Dotaz `poklad vzacnejsi` najde píseň
  „Je jeden hlas, co měl by znít“, čeština / v1, s původním textem úryvku.

### Upřesnění 13B – úryvky a vzhled

Výsledky mají pouze Název písně a Úryvek, sloupec Shoda v byl odstraněn.
Úryvek zachovává dva neprázdné řádky kolem nejlepší shody slov dotazu;
na posledním řádku přidá předchozí. Dlouhé jednotlivé řádky se zkracují
kolem shody (nejvýše 150 znaků plus výpustky na řádek). Při shodě názvu
nebo souboru zobrazí odpovídající textovou sekci, případně začátek první
neprázdné sekce. Pořadí výsledků se nemění.
Okno přebírá aktuální barvy a fonty hlavního okna, vstupu a tlačítek.
Výsledky mají výšku pro dva řádky a vodorovný posuvník pro dlouhý text.
Změněné soubory: song_search.py, song_search_window.py, oba vyhledávací
testy a README. Ověřeno 12 testy vyhledávání včetně skutečného Tk okna,
shody na šestém a posledním řádku; statická kontrola a diff --check OK.
Toto upřesnění nahrazuje původní popis jednorádkového úryvku a sloupce shody.

Doplnění: dlouhý sousední řádek bez shody se zkrátí od začátku, nikoli
od konce, aby úryvek zachoval srozumitelný kontext. Regresní test prošel.

### Ovládání 13B – přesun výběru souborů

Hlavní tlačítko `+` nyní otevírá vyhledávání; samostatné `Hledat` je odstraněno.
Původní výběr souborů z disku je dostupný přes `+` vpravo vedle vstupu dotazu
ve vyhledávacím okně. Používá původní addSource/loadSource včetně validace
 a ochrany neuložených změn. Po návratu se aktualizuje označení playlistu.
Obě tlačítka přebírají styl aplikace. Upraveny main_window.py,
song_search_window.py, test_song_search_window.py a README.
Ověřeno: 12 testů vyhledávání OK včetně vyvolání obou tlačítek a původního
výběru souborů; check_python 52 souborů / 67 modulů / 0 chyb; diff --check OK.
