# Nasazení editoru a ověření s kapelníky

Stav 3. 11. 2026: připraveno k nasazení, **publikace není ověřena**.
Cílová adresa: https://moskitogrill.github.io/SuperPresenter/ (při kontrole HTTP 404).

## Nasazení na GitHub Pages

1. Zkontrolujte změny, dokončete připravené sloučení commitem a push do větve
   **`Sbor`** (přesná velikost písmen). `test` zůstává pro vývoj a nenasazuje se.
   Commit musí zahrnovat celý současný editor,
   lockfile i `.github/workflows/web-song-editor-pages.yml`.
2. V GitHub repozitáři otevřete **Settings → Pages → Build and deployment →
   Source: GitHub Actions**. Pokud prostředí `github-pages` omezuje větve,
   povolte zvolenou větev nebo nasaďte z povolené větve.
3. V **Actions → Web song editor Pages** ověřte úspěch jobů build a deploy.
   Workflow lze spustit také ručně přes **Run workflow** s větví `Sbor` po pushi jeho souboru.
   Deploy má navíc podmínku větve `Sbor`, takže ruční spuštění z `test` nepublikuje web.
4. Otevřete URL z deployment environment `github-pages`. Musí odpovídat editoru,
   nestačí zelený workflow ani HTTP 200. Ověřte také obnovení stránky.

Workflow sestaví izolovaný Vite projekt (Node 24, pnpm 11.25.0, frozen lockfile),
zkontroluje povolený obsah `dist`, provede Chromium testy produkčního sestavení
pod `/SuperPresenter/` a publikuje **pouze `web-song-editor/dist`**.
Žádná knihovna `songs/`, test-output, DOCX příklady, zdrojové mapy ani lokální
koncepty nejsou součástí artefaktu. Kontrola odmítne každý soubor kromě index.html
či výsledných hashovaných JS/CSS. Případné budoucí veřejné assety vyžadují
vědomé rozšíření seznamu. Toto neskrývá soubory už přítomné ve veřejném Git
repozitáři; omezuje pouze obsah nasazeného webu.

V této relaci není GitHub CLI ani připojený GitHub nástroj pro správu Pages.
Bez uživatelova commitu a push nelze nasadit tyto necommitnuté změny.
Není vytvořen commit ani proveden push nebo změna nastavení GitHubu.

## Ověření vývojářem

Ve `web-song-editor/`:

```powershell
pnpm install --frozen-lockfile
pnpm build
node scripts/check-dist.mjs
pnpm test
pnpm exec playwright install chromium
pnpm test:browser
# Po skutečném nasazení spusťte stejné scénáře proti veřejné adrese:
$env:EDITOR_URL = 'https://moskitogrill.github.io/SuperPresenter/'
pnpm test:browser
Remove-Item Env:EDITOR_URL
```

Browserové testy bez EDITOR_URL používají `vite preview` nad hotovým `dist`,
nikoli vývojový server. Produkční uživatel potřebuje jen aktuální prohlížeč
na HTTPS adrese, žádný Node, lokální server ani instalaci. Dvojklik na stažené
`index.html` přes `file://` není podporované spuštění (ES moduly mají omezení).
Po načtení lze upravovat i stahovat bez sítě; nové offline otevření/reload není
garantováno, protože není service worker ani PWA. TXT lze upravovat offline
v Poznámkovém bloku a později znovu importovat.

## Ruční scénář pro kapelníky

Použijte vlastní testovací kopii, nikoli jediný originál; poznamenejte prohlížeč,
zařízení a URL. Není společná knihovna ani automatické předávání do SuperPresenteru.

1. **Vytvoření nové písně:** Nová píseň → zadejte název, Sloku, Refrén a Bridge.
   Zkontrolujte diakritiku a více řádků. Obnovte stránku a ověřte název i texty.
2. **Úprava existující písně:** Otevřít → vyberte kopii místního XML.
   Upravte název a text sloky, případně přepněte dole jazyk. Ověřte,
   že ostatní jazyky zůstaly zachované a originál na disku se nezměnil.
3. **Sestavení a změna pořadí:** v Části k přidání klikněte Sloka 1,
   Refrén 1, Sloka 2. Přesuňte výskyt tažením i pomocí Alt + šipek.
   Rozbalte Náhled výsledného pořadí a ověřte skutečný sled.
4. **Opakování refrénu:** vložte stejný refrén znovu. Změňte jeho text
   v textové kartě; změna musí být ve všech výskytech. Odeberte jeden
   výskyt křížkem v pořadí; samotný text refrénu musí zůstat.
5. **Offline úprava TXT a opětovné načtení:** Stáhnout → TXT → jazyk.
   V Poznámkovém bloku bez připojení změňte text sloky, zachovejte označení
   částí a UTF-8. V editoru Importovat → TXT → zkontrolujte náhled.
   Při stejném názvu výslovně zvolte přepsání správného jazyka.
   Ověřte text, pořadí, refrén a ostatní jazyky. TXT není úplná XML záloha.
6. **Export XML a použití v SuperPresenteru:** Stáhnout → XML. Otevřete
   stažené XML znovu ve webu a ověřte texty/pořadí. Potom soubor ručně
   umístěte do testovací knihovny používané distribuce SuperPresenteru,
   načtěte a promítněte celý sled včetně opakovaného refrénu a jazyků.
   Ověřte i opětovné uložení desktopovým editorem a následné načtení.
   Stažení samo nepřepisuje původní soubor; pozor na přidané číslo v názvu.

## Šablona zpětné vazby

- Datum, URL, prohlížeč/verze, zařízení, verze SuperPresenteru:
- Úkol (číslo scénáře a provedené kroky):
- Očekávání:
- Skutečný výsledek:
- Nejasnosti (popisek, ovládání, kam pokračovat):
- Závažnost: blokující / velká (existuje obcházení) / drobná / námět.
- Opakovatelnost a případná anonymizovaná ukázka nebo screenshot:

## Omezení a další etapa

Koncept je pouze v místním úložišti konkrétního prohlížeče a adresy.
Smazání dat, anonymní režim nebo jiné zařízení může obnovu znemožnit;
pravidelně stahujte XML. Více otevřených oken neřeší konflikty.
Desktopové Python kontroly nenahrazují test konkrétního distribuovaného EXE.
Firefox, Safari a reálné mobilní stahování zbývají k ručnímu ověření.
Databáze, účty, společná knihovna a synchronizace jsou budoucí samostatná etapa
po vyhodnocení zpětné vazby; nyní se nezavádějí.

## Výsledky přípravy (3. 11. 2026)

Produkční sestavení OK, 29/29 modelových a 14/14 Chromium testů OK pod cestou
repozitáře. XML/TXT import/export, obnova i práce bez sítě po načtení ověřeny.
Desktopové utility ověřily 862 roundtripů, novou píseň a reálné browserové
exporty v aktuálním Python loaderu. Obsah veřejného artefaktu prošel kontrolou.
Veřejná URL stále vrací 404; veřejné funkční ověření a konkrétní EXE zbývají.
