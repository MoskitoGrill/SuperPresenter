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
