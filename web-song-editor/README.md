# Webový editor písní SuperPresenter

Samostatná statická aplikace bez databáze, přihlášení a synchronizace.
Uživatel otevře HTTPS adresu v prohlížeči bez instalace. Společná knihovna
zatím není zavedena; exportované XML musí ručně přenést do SuperPresenteru.

## Vývoj a ověření

Node 24 a pnpm 11.25.0:

```powershell
pnpm install --frozen-lockfile
pnpm dev
pnpm build
node scripts/check-dist.mjs
pnpm test
pnpm exec playwright install chromium
pnpm test:browser
```

Build je v `dist/`, relativní base umožňuje GitHub Pages pod názvem repozitáře.
Browserové testy běží nad produkčním sestavením pod `/SuperPresenter/`.
Pro veřejnou adresu nastavte `EDITOR_URL` (včetně koncového lomítka).

## Ovládání

Nahoře Nová píseň / Otevřít XML / Importovat TXT nebo DOCX, šablony a menu
Stáhnout → XML / TXT / DOCX. Vlevo upravujte texty Sloky, Refrénu a Bridge,
vpravo přidávejte jejich výskyty do pořadí a přesouvejte je tažením nebo
Alt + šipkami. Stejná část sdílí text ve všech výskytech. Dole v pořadí je
rozbalovací náhled; správa jazyků je na konci stránky. Název opakování
při XML exportu uloží aktuální sled pod zvoleným jménem, prázdný znamená default.
TXT/DOCX přenášejí vybraný jazyk; úplná záloha je XML.

Rozpracovaný koncept se průběžně ukládá pouze do místního úložiště prohlížeče.
Pravidelně stahujte XML. Stažení nepřepíše původní soubor na disku.
Vadné importované pořadí se zachová s diagnostikou; neprovádí se tichá oprava.

[Nasazení a scénáře pro kapelníky](../docs/web-song-editor-deployment.md)
obsahují přesný postup GitHub Pages, stav adresy, omezení a zpětnou vazbu.
[Plán a výsledky](../docs/web-song-editor-plan.md),
[formát TXT](../docs/song-txt-format.md), [formát DOCX](../docs/song-docx-format.md).

Písně se nikam neodesílají. Publikuje se pouze zkontrolovaný obsah `dist/`,
nikoli knihovna `songs/`, testovací data či místní koncepty. Offline lze upravovat
již načtenou stránku; nové offline načtení a `file://` nejsou podporované režimy.
