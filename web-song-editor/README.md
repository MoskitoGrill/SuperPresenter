# Webový editor písní – funkční základ

Samostatný TypeScript/Vite web bez serverové části. Písně se nikam neodesílají.
Knihovna `songs/` se nebalí do výsledného webu. Vzhled je pouze základní.

## Lokální spuštění

Node.js 22.12+ (nebo 24 LTS), pnpm 11+:

```powershell
cd web-song-editor
pnpm install --frozen-lockfile
pnpm dev
```

Otevřete adresu vypsanou Vite (obvykle http://127.0.0.1:5173).
Produkční build: `pnpm build`; výstup `dist/`, relativní cesty pro pozdější Pages.
Hosting není součástí této etapy. Vývojový server je určen pro lokální použití.

## Ovládání a omezení

Text části upravujete jen jednou; všechny její výskyty v pořadí na něj odkazují.
Části i výskyty přesouváte tlačítky nahoru/dolů, dostupnými také klávesnicí.
Části Sloka/Refrén/Bridge mají interní ID v/r/b s číslem. Vlastní typ zadáte při
přidání vlastního bloku. Změna ID existující části zatím není nabízena.
Importované varianty a pojmenovaná pořadí lze přepínat. Přidávání jazyků,
dalších pořadí, změna main, skupiny, výběry řádků a @ jsou další etapa.

Bezpečný import: UTF-8 (i BOM), nejvýše 1 MiB a 10 000 elementů, pouze jednoduché
neprázdné posloupnosti celých částí. Všechny varianty musí mít stejná ID částí.
Složitý/vadný guide, duplicitní/prázdná jména, více main, chybná identita, DTD
a nepodporovaný vnořený obsah se odmítají bez změny aktuálního konceptu.
Neznámá kořenová metadata i atributy se uchovávají v XML DOM a nevykreslují jako HTML.
Není garantováno původní formátování XML ani projektorové rozdělení stránek.
Náhled zobrazuje uložené texty, nikoli desktopové čištění a prezentační styly.

Běžné stažení zachová UUID; starému XML bez ID přidělí ID při otevření.
Pro další práci otevírejte stažené XML s ID. Kopie vyžaduje vlastní název,
získá nové UUID a původní koncept je dostupný tlačítkem návratu. Uchovává se
jedna kopie současně, pouze v paměti. Zavření stránky může koncepty ztratit;
prohlížeč nemusí beforeunload varování vždy zobrazit.

**Stažení XML nepřepíše původní soubor. Stažený soubor musíte sami umístit do
knihovny SuperPresenteru a případně nahradit původní soubor.** Prohlížeč může
přidat k názvu číslo. Stav „staženo“ znamená zahájení downloadu, ne ověření zápisu na disk.

## Ověření

```powershell
pnpm test
pnpm build
# V kořeni repozitáře, Python s desktopovými závislostmi:
.venv/Scripts/python.exe web-song-editor/tests/verify_desktop.py
# Opět ve web-song-editor:
pnpm exec playwright install chromium
pnpm test:browser
```

Vitest vytvoří ignorovaný `test-output/` s reportem přijatých/odmítnutých souborů
ze `songs/` a `Testovací písně/`, výstupními XML a novou testovací písní.
Python porovná přijaté roundtripy přes SongRepository a skutečný WidgetSource,
ověří pořadí současným parserem. Originály se pouze čtou. Úspěch omezené
podmnožiny není důkaz úplné kompatibility knihovny. Aktuální výsledky a ruční
scénář jsou v `../docs/web-song-editor-plan.md`, oddíl Předání implementace.
