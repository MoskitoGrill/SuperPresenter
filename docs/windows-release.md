# SuperPresenter 3.0.0 – Windows x64

Verze 3 obsahuje dokončenou etapu 13B. Etapa 13C bude začátkem verze 4.

## Spuštění bez Pythonu

Rozbalte celý ZIP například do `C:\Aplikace\SuperPresenter-v3` nebo do Dokumentů.
Složka musí být zapisovatelná. Spusťte `SuperPresenter.exe`. Python, Tcl/Tk a další
knihovny jsou přibalené ve složce `_internal`. Není potřeba BAT ani instalace Pythonu.
Samotný soubor EXE nepřesouvejte mimo tuto složku a nespouštějte aplikaci uvnitř ZIPu.

## Hlavní panel a Stream Deck / Bitfocus

Starou ikonu odepněte. Spusťte nové `SuperPresenter.exe`, klikněte pravým tlačítkem
na ikonu běžící aplikace na hlavním panelu a zvolte **Připnout na hlavní panel**.

V akci Bitfocusu pro spuštění aplikace vyberte úplnou cestu k tomuto EXE,
například `C:\Aplikace\SuperPresenter-v3\SuperPresenter.exe`. Argumenty nechte prázdné.
Pokud akce nabízí pracovní adresář, nastavte složku aplikace. Aplikace si své
datové cesty určuje sama a funguje i s jiným pracovním adresářem.
Vzdáleně běžící Bitfocus musí spouštět program na cílovém Windows počítači.

## Data a další verze

Tlačítko **prez** a přepínač `--presentation-editor` spouštějí nový PresentationPresenter (`presentation_presenter_v2.py`). Jeho balíček je zahrnutý ve společném EXE a složka `presentation` obsahuje také vzorovou prezentaci a průvodce. Tato změna platí pro nově sestavené distribuce.

Písně, obrázky, Bible, prezentace a JSON styly jsou vedle EXE a zůstávají
editovatelné. Průběžná obnova editoru je v `.song-recovery` vedle EXE.
Uživatelské profily a logy jsou v `%APPDATA%\SuperPresenter` a sdílejí se
s dosavadní zdrojovou aplikací. Před přechodem na další verzi zazálohujte také tuto složku.

Toto je samostatný snímek verze 3. Změny zdrojového projektu přes Git jej nemění.
Verzi 4 sestavíme a rozbalíme samostatně. Před výměnou zálohujte své písně,
prezentace, obrázky, styly a profily; novou distribucí je nepřepisujte.
Na novou cestu potom přepněte Bitfocus i připnutí na hlavním panelu.

## Ikona

Výchozí ikona je generická. Vlastní skutečný ICO soubor vložte do
`images/ikona.ico`. Okno jej použije při dalším spuštění. Pro změnu ikony EXE
je nutné nové sestavení ze zdrojového projektu; připnutou ikonu případně připněte znovu.

## Diagnostika

Při chybě zašlete text hlášky a logy z `%APPDATA%\SuperPresenter\logs`.
Volba `SuperPresenter.exe --smoke-test C:\cesta\kontrola.json` spustí automatickou
kontrolu GUI, stylů, dočasné písně, Tcl/Tk a editoru prezentací. Cílová složka
pro JSON musí existovat. Návratový kód 0 znamená úspěch, 1 chybu popsanou v JSONu.
Kontrola nenahrazuje zkoušku fyzických projektorů a tlačítka na Stream Decku.

Distribuce není podepsaná placeným certifikátem. Nelze zaručit, že ji každý antivirus
přijme. Při detekci nechte soubor prověřit; nevypínejte ochranu ani nenastavujte
plošné výjimky. Soubor `release.json` obsahuje kontrolní součty sestavení.

## Nové sestavení ze zdrojů

Na Windows x64 s Pythonem 3.13 a Tcl/Tk:

```bat
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts\build_release.py
```

Každé sestavení vytvoří novou složku a ZIP v `dist`, existující distribuci
nepřepisuje. Verze aplikace je v `superpresenter/version.py`, metadata EXE
v `packaging/version_info.txt`. Pro verzi 4 se upraví také název distribuce
v `.spec` a sestavovacím skriptu. Soubory v `dist` nejsou součástí Gitu.
