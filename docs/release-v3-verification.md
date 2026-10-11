# Ověření distribuce SuperPresenter 3.0.0

## Aktuální sestavení po stabilizaci — 9. 10. 2026

Stav: **automatické ověření prošlo; finální ověření ČEKÁ na reálné kontroly**.
Následující zářijový záznam je historický a netýká se nového artefaktu.

- ZIP: `C:\Users\moski\Documents\Prográmky\SuperPresenter\dist\3.0.0-20261009-140605\SuperPresenter-3.0.0-win64.zip`
  (28 537 890 B).
- EXE: `C:\Users\moski\Documents\Prográmky\SuperPresenter\dist\3.0.0-20261009-140605\SuperPresenter-v3\SuperPresenter.exe`.
- SHA-256 ZIP: `3CF5F8567C4D1C2FB1DB0C3C27AF1DC39863FEF5764D7C44CB893477A8EDDB38`.
- SHA-256 EXE: `4F1C5BDBB4320C401C5F7C2F7180D714AFFB92814664C76404833CE2DD9E02D1`.
- Windows 11 build 26200, Python 3.13.14 AMD64, PyInstaller 6.22.2,
  Tcl/Tk 8.6.15. Balíčky přesně odpovídají `requirements-build.txt`.
  HEAD `00b24e84feff730c841452d27937b071177f44e2`, dirty=true;
  zahrnuté necommitované stabilizační změny etap 1–4 a rozšířená diagnostika.
- Etapa 4: 305 testů OK a 40 cyklů zdrojového provozního testu OK; nejsou
  vydávány za nové testy EXE. Etapa 5: zdrojová diagnostika, zabalené EXE
  a EXE z rozbaleného ZIPu všechny skončily kódem 0, `ok: true`.
- Každá diagnostika: šest stylů a jejich prostředky, 31 úspěšných běhů
  projekce zakončených stopem/zavřením, 120 navigačních dvojic vpřed/zpět,
  šest skutečných uložení názvu dočasné písně během projekce se zachováním
  názvu běžícího snímku. Šest odmítnutých vstupů (syntaxe, strukturální
  limit a limit skutečných řádků ve stacionárním i legacy režimu), obnovené
  ovládání a následný úspěšný start. Zavření za projekce uklidilo výstupy.
  Python callback i Tcl bgerror: žádné chyby. Editor prezentací/tkdnd OK.
- Ověřeno všech 2010 hashů manifestu. Přenos do složky s mezerami a
  diakritikou na stejném PC, spuštění z TEMP s PATH pouze
  `C:\Windows\System32;C:\Windows`. Běžný start otevřel okno
  `SuperPresenter 3.0.0`, WM_CLOSE skončil kódem 0; izolovaný console log
  je prázdný. EXE metadata uvádějí 3.0.0 / stage 13B.
- Diagnostika používá dočasnou píseň a APPDATA; běžný start používá
  izolovanou rozbalenou kopii a vlastní APPDATA. Ostré profily ani písně
  nebyly testem ukládány. Přibalených 859 XML zahrnuje známý nález
  prázdného názvu `songs/.xml`; data nebyla opravována ani mazána.
- Logy: `stage5-build.log`, `stage5-source.json`, `stage5-verification.log`
  (prázdný při úspěchu), `release-checks/stage5-20261009/{packaged,portable,verification}.json`.
  Build obsahuje běžná upozornění na volitelné/platformní importy;
  testované funkce prošly, neověřené formáty obrázků tím nejsou certifikovány.

**ČEKÁ:** skutečný projektor a odpojení/připojení monitoru, čtyřhodinový
provoz s pamětí/odezvou/logy, čistý druhý PC, skutečné připnutí a tlačítko
Bitfocus/Stream Deck a kontrola antivirem na cílovém PC. Přesný postup,
izolace i kritéria jsou v [ručním scénáři](stage5-hardware-scenario.md).
Nic nebylo publikováno ani instalováno do produkčního umístění.

## Historické sestavení před stabilizací

Datum: 11. 9. 2026. Hranice vydání: etapa 13B; 13C patří do verze 4.

## Výsledek

- 249 regresních testů prošlo (`unittest discover -s tests -v`).
- Diagnostika zdrojové aplikace prošla.
- PyInstaller 6.22.2 sestavil Windows x64 onedir bez UPX.
- Zabalené EXE prošlo diagnostikou s návratovým kódem 0.
- ZIP byl rozbalen do jiné složky s mezerami a diakritikou. Kontrola prošla
  i při spuštění z adresáře TEMP a s PATH obsahujícím jen Windows.
- Otevřelo se skutečné okno `SuperPresenter 3.0.0` a normální zavření skončilo kódem 0.
- Windows spuštění nového EXE při těchto testech nezablokoval.

Diagnostika skutečně vytváří GUI, načítá šest dodaných projekčních stylů a obrázky,
spouští a zastavuje každý styl s dočasnou písní, ověřuje Windows vlastnosti pro
opětovné spuštění připnutého okna, Tcl/Tk 8.6.15 a start editoru prezentací s tkdnd.
Písně a profily uživatele se při kontrole neupravují. Distribuce obsahuje 859 XML písní.

Kontrola odhalila starší pád editoru prezentací při jediném monitoru; oprava
vybírá druhý monitor jen tehdy, pokud existuje. Opakovaná kontrola prošla.

## Artefakty

Složka: `dist/3.0.0-20260911-141738/SuperPresenter-v3`

ZIP: `dist/3.0.0-20260911-141738/SuperPresenter-3.0.0-win64.zip` (28 008 875 B)

SHA-256 ZIP:
`3EE1414985CDFCB00064BB17C7D36B65341873534F5510DBAF5A9893C8FBB3FD`

SHA-256 EXE:
`BC98868EC2369CB2AB8877B54D821703A6FFD2BC0671CA2825A4A03EFCFD9DAF`

Distribuce obsahuje `release.json` s hashi přibalených souborů, údajem o Pythonu,
zdrojovém Git commitu a příznakem necommitovaných změn při sestavení.
`build-dependencies.txt` zaznamenává balíčky sestavovacího prostředí.

Místní podrobné logy jsou v ignorované složce `release-checks`: `stage3-tests.log`,
`stage3-build.log`, `release-source-check.json`, `packaged.json` a `portable.json`.

## Praktické meze ověření

Test přenosu proběhl na stejném Windows počítači do jiného adresáře, nikoli na
fyzicky čistém druhém PC. Neověřuje konkrétní konfiguraci Bitfocusu, skutečné
kliknutí na Připnout ani fyzické projektory. Pro Bitfocus je připraveno normální
EXE bez argumentů a bez požadavku na systémový Python. Uživatelskou zkoušku
je potřeba provést na cílovém PC před ostrým provozem.

Budoucí sestavení nemají zaručený stejný hash a přijetí antivirem. Nebyly měněny
výjimky ani nastavení ochrany. Vydání není digitálně podepsané.

## Kontrola antivirem

Vlastní kontrola výsledné distribuční složky Windows Defenderem dokončena.
Dotaz na detekce vztahující se k cestě tohoto vydání nevrátil žádný nález.
Systém eviduje také McAfee; jeho samostatný výsledek z těchto nástrojů nebyl získán.
