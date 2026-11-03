# Webový editor písní – kompatibilita a místní obnova

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
Varianty lze přepínat, přidávat a přejmenovat. Nový jazyk má prázdné texty.
„Odebrat jazyk“ po potvrzení smaže vybraný jazyk a jeho texty. Poslední jazyk
nelze odebrat. Pořadí uvnitř odebíraného jazyka se zachovají jako společná,
včetně jejich obsahu a výchozího označení. Potvrzení upozorní na unikátní části;
odkazy na ně zůstanou zachovány s diagnostikou chybějící části.
Pojmenovaná pořadí lze přidat, přejmenovat a výslovně nastavit jako výchozí.
Duplicitní jména a původní umístění pořadí uvnitř jazyků se při importu zachovají.
Výchozí výběr: první main, jinak default, jinak první pořadí.

Pořadí se upravuje jako strom: „Opakovat tento blok“, „Seskupit s následujícím“,
počet opakování, vnořené skupiny, přesuny, výběr řádků a připojení k předchozímu
bloku při volné kapacitě (@). Syntaxi není třeba psát. Výběry řádků jsou číslované
od 1 po desktopovém odstranění prázdných řádků a levého odsazení; rozsah zahrnuje
oba konce. Náhled ukazuje posloupnost, nikoli stránkování, spojování a styly
projektoru. Skutečný výsledek ověřte v SuperPresenteru.

Bezpečný import: UTF-8 (i BOM), nejvýše 1 MiB a 10 000 elementů. Vadné pořadí,
chybějící reference/řádky nebo historické nulové konstrukce se zachovají uzamčené
s diagnostikou. Lze měnit texty a stáhnout XML se stejným vadným pořadím po
upozornění; případně výslovně sestavit náhradu. Po doplnění textů použijte
„Znovu ověřit pořadí po změně textů“. Původní guide se bez úpravy nepřepisuje.
Chybějící pořadí se automaticky nedoplňuje. XML s prázdným názvem se zachová;
stažený soubor se jmenuje pisen.xml a desktop může zobrazit název podle souboru.

Vadné XML, chybná identita, DTD, namespace známých uzlů, duplicitní/prázdné
názvy jazyků a ID částí nebo nepodporovaný vnořený obsah se odmítají bez změny
aktuálního konceptu. Před smazáním části se zobrazí dopad na každé pořadí;
vyprázdnění celého pořadí nebo jakékoli uzamčené pořadí mazání bezpečně blokuje.
Neznámá kořenová metadata i atributy se uchovávají v XML DOM a nevykreslují jako HTML.
Není garantováno původní formátování XML. Není mazání celých pořadí,
přejmenování ID částí, tažení ani historie. Strom má limit 32 úrovní a 4096 kroků
i prezentačních řádků přes všechny jazyky; guide nejvýše 16 384 znaků.

Běžné stažení zachová UUID; starému XML bez ID přidělí ID při otevření.
Pro další práci otevírejte stažené XML s ID. Kopie vyžaduje vlastní název,
získá nové UUID a původní koncept je dostupný tlačítkem návratu. Uchovává se
jedna kopie současně. Koncept, původní práce, identity a výběry se průběžně
obnovují z místního úložiště prohlížeče po obnovení stránky. **Nejde o sdílené
ani trvalé uložení.** Vymazání dat, jiný profil/adresa, anonymní režim či plné
úložiště mohou obnovu znemožnit. Selhání zápisu se zobrazí; nečitelná záloha
se bez potvrzení nepřepíše a lze ji stáhnout jako JSON (bez importního UI).
Více oken nemá řešení konfliktů, poslední místní zápis vyhraje. Stahujte XML.
Prohlížeč nemusí beforeunload varování vždy zobrazit.

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
Python porovná význam roundtripů přes SongRepository a skutečný WidgetSource,
strom každého platného pořadí se současným parserem i shodné odmítnutí vadných
výrazů. Nevyžaduje shodné formátování XML. Po Playwrightu spusťte Python znovu
pro kontrolu skutečných downloadů. Originály se pouze čtou. Aktuální výsledky:
862 XML, 13 Vitest testů, 5 Chromium scénářů a 25 desktopových testů parseru/limitů.
Existující desktopové zápisové sady mají nadále chyby WinError 5 při os.replace
dočasných XML; jejich běh nelze označit za úspěšný. Podrobnosti jsou v předání.
Ruční scénář a známá omezení jsou v `../docs/web-song-editor-plan.md`, oddíl 9.
Distribuované EXE a další prohlížeče zbývají ověřit ručně. Commit provádí uživatel.
## TXT pro Poznámkový blok

Použijte **Stáhnout TXT**, vyberte jazyk a pořadí, upravte soubor v UTF-8
a načtěte jej přes **Importovat TXT**. Soubor nemá technickou hlavičku ani
povinné dvojtečky. **Stáhnout prázdnou TXT šablonu** nabídne název a prázdnou
sloku, refrén a bridge k doplnění. Před importem se zobrazí náhled a problémy.
Import obvykle vytvoří novou píseň. Při shodě názvu s otevřeným konceptem
nabídne přepsání textů zvoleného jazyka (ostatní data a identita zůstanou)
nebo novou píseň s jiným názvem. Knihovnu na disku web neprohledává.
TXT je jen vybraný jazyk a jedno jednoduché pořadí; plná záloha je XML.
Změněné pořadí se při aktualizaci přidá jako nové nevýchozí TXT pořadí.
Stejný postup je dostupný také pro Word DOCX, viz níže.

Podrobná pravidla a ruční test: [specifikace TXT](../docs/song-txt-format.md).
Ukázka: [ukazkova-pisen.txt](examples/ukazkova-pisen.txt).
Prázdná šablona: [sablona-pisne.txt](examples/sablona-pisne.txt).

## Word DOCX

**Stáhnout DOCX** nabízí jazyk a pořadí; **Stáhnout prázdnou DOCX šablonu**
připraví dokument k doplnění. Upravte jej ve Wordu a vraťte přes **Importovat DOCX**.
Náhled, rozpoznání částí, konflikty, shoda názvu a ochrany jsou stejné jako u TXT.
Přenášejí se texty a pořadí, nikoli fonty, barvy a Word formátování.
Při přepsání jazyka se zachovají ostatní data a UUID; změněné pořadí se přidá
jako nové nevýchozí DOCX pořadí. Starší `.doc` není podporován.

Pravidla, omezení a ruční průchod: [návod DOCX](../docs/song-docx-format.md).
Ukázka: [ukazkova-pisen.docx](examples/ukazkova-pisen.docx).
Šablona: [sablona-pisne.docx](examples/sablona-pisne.docx).

DOCX ZIP čte a zapisuje lokálně [fflate](https://github.com/101arrowz/fflate)
(přímá závislost 0.8.3, uzamčená v pnpm-lock.yaml). Žádné uploady ani CDN.
Kontroly po `pnpm test` a `pnpm test:browser`:

```powershell
# Z kořene repozitáře:
python web-song-editor/tests/verify_docx_desktop.py
# Volitelně ve web-song-editor na Windows s instalovaným Wordem:
./tests/verify_docx_word.ps1
```

Word kontrola otevírá jen vygenerované test-output soubory skrytě, uloží
upravený DOCX a QA PDF. `tests/fixtures/word-edited.docx` je referenční vzorek
skutečně upravený a uložený Microsoft Wordem. Výstupy se necommitují.
