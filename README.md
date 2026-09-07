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
