# Ověření distribuce SuperPresenter 3.0.0

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
