# PresentationPresenter — zadání, etapy a předávání

Datum založení: 11. 10. 2026. Stav: PP1 dokončeno; PP2 nezahájeno.

## Jak používat tento dokument

Tento soubor je společný zdroj zadání a předávání mezi chaty. Před každou etapou jej přečti, ověř skutečný stav kódu a předchozí výsledky. Po etapě jej aktualizuj. Historii dokončených etap nepřepisuj; změny rozhodnutí zaznamenej s důvodem. Nepovažuj plánovanou funkci za hotovou.

Etapy prováděj postupně. Každá má skončit konkrétním spustitelným nebo ověřitelným výsledkem. Neodkládej chybu, která brání dokončení aktuální etapy nebo bezpečnému pokračování. Ostatní závady eviduj s dopadem, reprodukcí a cílovou etapou. Skutečné promítání na fyzické monitory a kontrolu streamového skládání nelze nahradit automatickým testem; neověřené scénáře označ.

## Ochrana současné aplikace

- Nová aplikace bude samostatná. Navržený balíček: `presentationpresenter/`, vývojový spouštěč `presentation_presenter_v2.py`, testy `tests/presentationpresenter/`. Etapa 1 může cesty upravit a zde zdůvodnit.
- Starý `presentation_presenter.py` ponech jako referenci do finálního rozhodnutí o přepnutí. Původní soubory prezentací neupravuj.
- Neměň funkční kód SuperPresenteru, `song_editor.py`, jeho nastavení, styly, profily ani písně. Vzhled můžeš převzít jako samostatné výchozí hodnoty; nevytvářej závislost na jeho interních UI modulech. Biblické podklady lze číst společně, bez zápisu.
- Nová aplikace má vlastní nastavení, ukládání a recovery. Změny společných build souborů nebo spouštěče patří až do distribuční etapy a musí zachovat dosavadní chování.
- Pracovní strom je při založení dokumentu již změněný. Před prací zkontroluj `git status`; cizí změny zachovej a nezahrnuj je do svých commitů. Automaticky necommituj ani nestashuj cizí práci.

## Přijaté produktové zadání

1. Samostatná Windows aplikace vzhledově navazuje na SuperPresenter. PowerPoint import/přehrávání, volná textová pole, animace a skutečná kamera jsou mimo první verzi.
2. Textový úsek má název/odkaz a obsah: odstavce, odrážky, základní tučné písmo, kurzívu, podtržení a barvy. Název se opakuje vpravo nahoře na všech pokračováních úseku. Interní data mají umožnit budoucí import nadpisu a obsahu z PPTX.
3. Sál i stream mají nezávisle 4:3 nebo 16:9; výchozí sál 4:3, stream 16:9. Společný snímek nese stejný obsah na obou výstupech; řádkové zalomení a poloha se liší.
4. Stream rezervuje pravou dolní čtvrtinu plochy (polovina šířky × polovina výšky) plus bezpečný odstup. Text oblast obtéká. Kamera se nepřipojuje. Model geometrie připrav na budoucí změnu velikosti a polohy; editor těchto parametrů není povinný v první verzi.
5. Dělení se počítá společně podle obou aktuálních rozložení, skutečných metrik písma a dostupné výšky. Obsah se nesmí ztratit, duplikovat ani překrýt kameru. Jedna odrážka může mít různý počet řádků. Pokud se vejde celá na další snímek, přesune se; pokud převyšuje celý snímek, rozdělí se s rozpoznatelným pokračováním.
6. Výchozí černý začátek prezentace a černý předěl po každém úseku včetně posledního. Závěrečný předěl lze u úseku vypnout a přesouvá/duplikuje se s úsekem. Začátek lze vypnout v nastavení prezentace. Nevytvářej sousední duplicitní předěly.
7. Velký náhled standardně ukazuje sál a lze jej přepnout na stream. Lišta všech snímků vždy ukazuje sál, aktuální snímek a umožňuje přeskok. Rozlišuj zdrojový úsek a jeho vygenerované pokračování.
8. Úpravy jsou rozpracované až do potvrzení „Použít do projekce“. Teprve potvrzení změní živý obsah i pořadí/počet pokračování. Zachovej aktuální místo podle začátku promítaného textu. Po změně začátku použij začátek upravované věty; po odstranění věty nejbližší následující obsah, případně začátek úseku. Hraniční pravidla a příklady dopracuje etapa 5. Nezachovávej pouze číslo snímku.
9. Obrázkové úseky zachovávají proporce. V sále využijí dostupnou plochu; ve streamu největší vhodný obdélník mimo kameru. Žádný povolený přesah do kamery v první verzi.
10. Bible: rychlý odkaz s našeptáváním a aliasy knih, výběrové ovládání, překlad, rozsah i přes kapitoly, náhled, čísla veršů, kopírování a vložení úseku. Nejednoznačné knihy vyžadují výběr; evangelium a Janovy listy neslučuj. Okno lze spustit samostatně bez editoru prezentace.
11. Automatické přepínání: interval, opakování, bezpečné ukončení. B přepíná dočasné zatemnění obou výstupů bez změny pozice; během zatemnění auto stojí, po návratu běží celý interval. V textovém vstupu B píše znak. Konkrétní další zkratky a globální ovládání dohodnout před etapou 8.
12. Duplikace úseků a možnost vytvořit samostatný snímek z pokračování, přesouvání, mazání, undo/redo, autosave/recovery, přenosné uložení médií a nastavení, kontrola přetečení a médií před projekcí. Skrývání snímků/úseků je mimo rozsah.

## Etapy a zadání do chatů

Každý níže uvedený text je samostatné zadání. Chat má nejprve přečíst tento dokument, ne rekonstruovat zadání pouze z názvu etapy. Pro etapy 1–9 použij stejný checkout; nespouštěj souběžné implementace závislých etap.

### Etapa PP1 — samostatný základ a datový model

**Výsledek:** spustitelné samostatné okno, vlastní vzhled/nastavení a verzovaný model prezentace s ukázkovými daty. Bez zásahu do SuperPresenteru.

**Text do chatu:**
> Proveď etapu PP1 PresentationPresenteru podle docs/presentation-presenter-handoff.md. Nejprve přečti celý dokument a místní instrukce, ověř pracovní strom. Založ samostatnou aplikaci vzhledově navazující na SuperPresenter, odděl doménu, layout, projekční session, UI a persistence. Navrhni a implementuj verzovaný model úseků, strukturovaných odstavců/odrážek a formátování, obrázků, stabilních identit obsahu, černých předělů a dvou nezávislých výstupních konfigurací. Odděl zdrojový dokument, odvozený plán snímků a potvrzenou projekční session. Připrav budoucí rozšíření pro PPTX, ale neimplementuj je. Vytvoř základní spustitelné okno a ověř model vhodnými testy. Zaznamenej cesty, spuštění, rozhodnutí, výsledky a známé chyby do společného dokumentu. Nepokračuj do PP2.

### Etapa PP2 — společné dělení a layout sálu/streamu

**Výsledek:** ověřený plán společných snímků a statický náhled obou rozložení, včetně obtékání kamery.

**Text do chatu:**
> Proveď pouze PP2 podle docs/presentation-presenter-handoff.md a výsledků PP1. Implementuj layout a společnou paginaci textu pro všechny čtyři kombinace poměrů sálu/streamu. Použij metriky skutečně vykreslovaných fontů, odděl měření od kreslení a zachovej identitu/rozsahy zdrojového obsahu. Implementuj název vpravo nahoře, obtékání rezervované oblasti kamery s odstupem, odstavce, odrážky, formátování, dlouhá slova a příliš dlouhé odrážky. Definuj pravidla kapacity a čitelnou výchozí velikost písma; neřeš nedostatek místa nekontrolovaným zmenšováním. Přidej generování černých předělů. Ověř shodný obsah obou výstupů, úplnost textu a nepřekrývání kamery testy i vizuálně na ukázkách. Aktualizuj předávací dokument; další etapu nezačínej.

### Etapa PP3 — editor textů, náhled a lišta

**Výsledek:** použitelná příprava textové prezentace v hlavním okně.

**Text do chatu:**
> Proveď pouze PP3 podle docs/presentation-presenter-handoff.md. Navazuj na existující model a layout. Implementuj editaci názvu a obsahu, odstavce, odrážky a domluvené základní formátování, přidání/přesun/duplikaci/mazání úseků, volbu černého předělu a běžné undo/redo těchto operací. Vyřeš duplikaci jednotlivého pokračování jako nového samostatného úseku s vlastním obsahem. Implementuj velký náhled s přepnutím sál/stream a přehlednou posuvnou lištu všech snímků pro sál s označením aktuálního místa a klikacím přeskokem. Dbej na správný fokus při psaní a svižnou aktualizaci bez obnovování všech miniatur při každém přepnutí. Projekci zatím nespouštěj. Ověř běžný uživatelský průchod a aktualizuj předávací dokument.

### Etapa PP4 — dvě projekční okna a synchronní navigace

**Výsledek:** textová prezentace promítaná současně do sálu a streamu, možnost spustit i jediný výstup.

**Text do chatu:**
> Proveď pouze PP4 podle docs/presentation-presenter-handoff.md. Implementuj vlastní potvrzenou projekční session, nezávislý výběr monitoru a poměru stran pro sál/stream, spuštění a zastavení jednoho nebo obou výstupů a synchronní navigaci z hlavního okna i miniatur. Při spuštění použij aktuální připravený dokument; pozdější rozpracované editace živou session nesmí měnit. Ošetři odlišné rozměry monitorů, záporné souřadnice, resize, chybějící monitor, konflikt při výběru téhož monitoru a opakované spuštění/zavření. Sdílej renderer s náhledem. Přidej B/zatemnění s ochranou textových vstupů. Ověř synchronizaci, lifecycle a rozpracované editace. Fyzické scénáře, které nelze provést, označ jako neověřené. Aktualizuj společný dokument.

### Etapa PP5 — potvrzené živé opravy a zachování pozice

**Výsledek:** oprava za běhu bez průběžného přepisování na projekci a bez náhodného skoku.

**Text do chatu:**
> Proveď pouze PP5 podle docs/presentation-presenter-handoff.md. Implementuj jasné rozlišení rozpracované a živé verze a akci „Použít do projekce“. Po potvrzení atomicky přepočítej plán a synchronně aktualizuj oba výstupy. Zachovej pozici podle začátku promítaného obsahu a domluvených náhradních pravidel. Nejdříve v dokumentu konkretizuj příklady chování při vložení textu před aktuální místo, změně/odstranění první věty, opakujících se větách, odstranění aktuálního úseku, změně poměru a černém předělu; rutině rozhodni podle zadání. Používej stabilní identity a textové kotvy, ne samotné číslo snímku nebo hledání první shodné věty. Ověř, že ani editace, undo/redo či regenerace miniatur před potvrzením nemění projekci. Přidej cílené testy a aktualizuj předávací dokument.

### Etapa PP6 — obrázky a přenosné uložení

**Výsledek:** prezentace s obrázky, úplné ukládání/načítání, autosave a obnova.

**Text do chatu:**
> Proveď pouze PP6 podle docs/presentation-presenter-handoff.md. Implementuj obrázkové úseky, výběr souboru a podle dostupných závislostí přetažení, náhledy i oba výstupy se zachováním proporcí a umístěním streamového obrázku mimo kameru. Rozšiř undo/redo. Zvol a zdokumentuj vlastní verzovaný přenosný formát obsahující dokument, média a nastavení rozložení; neukládej strojově závislý monitor jako přenositelnou jistotu. Implementuj bezpečný zápis, otevření, autosave rozpracované verze a nabídku obnovy po nečistém ukončení. Původní data nepoškoď ani při chybném souboru či přerušeném zápisu. Přidej omezený import původních JSON prezentací s hlášením nepodporovaného obsahu a zachováním originálu. Ověř přenos bez původních obrázků, poškozená data a recovery. Aktualizuj společný dokument.

### Etapa PP7 — Bible jako vložený i samostatný nástroj

**Výsledek:** rychlé zadávání i pohodlný výběr a samostatné spuštění biblického okna.

**Text do chatu:**
> Proveď pouze PP7 podle docs/presentation-presenter-handoff.md. Implementuj oddělenou službu Bible nad stávajícími podklady pouze pro čtení a vlastní okno spustitelné z prezentace i samostatně. Přidej rychlé zadání odkazu, aliasy a našeptávání knih, výběr překladu/knihy/kapitol/veršů, rozsahy přes kapitoly, náhled, čísla veršů, kopírování a vložení nového textového úseku do editoru. Rozliš evangelium Jana a jeho listy; kontroluj rozsahy a dostupnost dat, neodvozuj úplnost překladů z názvu souboru. V samostatném režimu vložení do neexistující prezentace nenabízej. Ověř běžné české názvy a zkratky, nejednoznačnosti, chybné odkazy a více oken. Aktualizuj předávací dokument.

### Etapa PP8 — automatické přehrávání a ovládání

**Výsledek:** spolehlivé přehrávání a dohodnuté ovládání včetně práce mimo projekční okno.

**Text do chatu:**
> Proveď pouze PP8 podle docs/presentation-presenter-handoff.md. Nejprve zjisti uživatelem požadované konkrétní klávesy a způsob externího/globálního ovládání; nerozhoduj neznámé integrace naslepo. B a ovládání z hlavního okna jsou již schválené. Nezávisle implementuj automatické přehrávání s validovaným intervalem, opakováním, definovaným prvním čekáním a zastavením na konci. Zatemnění pozastaví časovač, návrat začne celý interval. Ošetři ruční přeskok, použití živých úprav, zavření projekce a aplikace bez zbylých časovačů. Implementuj dohodnuté zkratky bez konfliktů s textovými vstupy a případné externí ovládání v samostatném adaptéru. Ověř souběh vstupů a lifecycle. Aktualizuj předávací dokument včetně případné čekající uživatelské volby.

### Etapa PP9 — kontrola, stabilizace a první distribuce

**Výsledek:** ověřený balíček samostatné aplikace a přehled zbývajících omezení.

**Text do chatu:**
> Proveď pouze PP9 podle docs/presentation-presenter-handoff.md. Zkontroluj skutečné splnění zadání PP1–PP8 a oprav blokující chyby. Implementuj přehlednou kontrolu před projekcí pro přetékající obsah, chybné/chybějící obrázky, kolize s kamerou a výstupní konfiguraci. Ověř delší prezentace, všechny poměry stran, formátování, živé opravy, Bible, undo/redo, přenos a obnovu. Ověř, že SuperPresenter nebyl změněn ani regresně rozbit. Připrav samostatnou Windows distribuci s vlastní identitou a datovým adresářem; změny společného build procesu izoluj. Rozhodnutí o nahrazení původního spouštěče předlož uživateli až s ověřeným výsledkem. Sepiš krátký návod a checklist fyzického sálu/streamu. Nevydávej automatické testy za ověření hardwaru. Aktualizuj dokument výsledky, přesnou cestou balíčku a známými omezeními. PPTX neimplementuj.

## Záznamy dokončených etap

U každé dokončené etapy přidej:

### PPx — název, datum, stav (hotovo / částečně / blokováno)

- Výsledek a dostupné funkce:
- Změněné soubory a případný commit (jen pokud vznikl):
- Jak spustit a ověřit:
- Provedené kontroly a jejich výsledky:
- Vizuální/fyzické ověření; co zůstalo neověřené:
- Rozhodnutí, změny zadání a důvody:
- Známé chyby (ID z registru):
- Co má převzít následující etapa:

### PP1 — samostatný základ a datový model, 11. 10. 2026, hotovo

- Výsledek: samostatné Tkinter okno s ukázkovým textovým dokumentem, seznamem zdrojových úseků, inspektorem obsahu a nezávislou volbou 4:3/16:9 pro sál a stream. Inspektor zobrazuje odstavce, odrážky a formátování; není to layoutový ani projekční náhled. Editace obsahu, lišta snímků a projekce nejsou v PP1 implementovány.
- Model: schéma v1, neměnné dataclasses a tuple kolekce. Textové a obrázkové úseky mají název, odkaz, vlastní ID a `break_after`; textové bloky a běhy mají další globálně unikátní ID. Formátování: tučné, kurzíva, podtržení, barva #RRGGBB. Obrázek odkazuje na identitu média, které má locator a MIME typ. Zdroj uchovává samostatné konfigurace výstupů; výchozí sál 4:3, stream 16:9 s normalizovanou kamerovou oblastí (.5, .5, .5, .5) a odstupem .02. Černý začátek a předěly jsou výchozí; obě volby lze měnit v modelu.
- Oddělení: `Presentation` je zdroj; `SlidePlan` nese zdrojový snapshot a odvozené `Slide` s rozsahy do konkrétních běhů; `ProjectionSession.confirm()` vytvoří potvrzený neměnný snapshot s aktuální identitou snímku. Změna rozpracovaného dokumentu se provádí vytvořením nové verze (např. `dataclasses.replace`) a živý snapshot nemění. Skutečné ovládání projekce a potvrzování z UI patří do PP4/PP5.
- Černé předěly: `with_black_breaks()` obaluje již připravené obsahové snímky, zachovává pořadí úseků a nevytváří sousední černé snímky. Neobsahuje paginaci ani metriky fontu. Stabilní klíče předělů jsou odvozené z ID dokumentu/úseku.
- Persistence: přísný verzovaný JSON codec `dumps/loads` pro zdroj, média a výstupní konfigurace; zachovává ID a odmítá neznámé verze a nepodporované typy úseků. Neobsahuje balení médií, souborové akce prezentací ani recovery (PP6). `ImportOrigin` připravuje původní formát, zdroj a identitu položky pro budoucí adaptéry; PPTX se nečte.
- Vlastní vzhled: samostatné výchozí hodnoty šedého UI a Courier New, inspirované současnou aplikací bez importu jejích modulů nebo čtení jejích stylů. Vlastní nastavení okna a vzhledu jsou v `%LOCALAPPDATA%/PresentationPresenter/settings.json`; při běžném zavření se atomicky uloží geometrie. Volby poměru stran patří do zdrojového dokumentu, v PP1 jsou pouze v paměti. Poškozené aplikační nastavení přejde na vlastní výchozí hodnoty.
- Změněné/přidané soubory: `presentation_presenter_v2.py`; `presentationpresenter/__init__.py`, `app.py`, `domain.py`, `layout.py`, `session.py`, `persistence.py`, `settings.py`, `sample.py`, `ui.py`; `tests/presentationpresenter/__init__.py`, `test_pp1.py`; tento dokument. Žádný commit nevznikl. Předexistující změny pracovního stromu zůstaly zachované. `presentation_presenter.py`, funkční kód SuperPresenteru, `song_editor.py`, jejich styly, nastavení a data se v PP1 neupravovaly.
- Spuštění z kořene projektu: `python -B presentation_presenter_v2.py` (Python 3.10+ s Tkinterem). Ve zdejším prostředí Windows Store Python i `.venv/Scripts/python.exe` nelze spustit; ověřeno s `C:/Users/moski/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`. Nejsou potřeba nové externí závislosti ani změny společného buildu.
- Testy: `python -B -m unittest discover -s tests/presentationpresenter -v` — 9/9 OK. Pokrytí: roundtrip textu/obrázku/formátování/provenance a ID; nezávislé výstupy; neplatné identity, média, verze a geometrie; poškozený JSON; černé předěly a vypnutí; zdrojové rozsahy; izolace potvrzené session; vlastní nastavení a fallback; import doménových vrstev při zablokovaném Tkinteru a starých aplikacích. První běh měl jedinou chybu sandboxu při zápisu do dočasné složky; opakovaný povolený běh mimo sandbox prošel. Závěrečný běh po zpřesnění validace také 9/9 OK.
- Kontrola spuštění: skutečné `tk.Tk()`, sestavení `MainWindow`, `root.update()`, změna sálu na 16:9 a další update proběhly bez chyby; okno mělo titul PresentationPresenter — PP1, rozměr 1100×720 a ukázkový obsah. Test okno zničil bez ukládání skutečných uživatelských nastavení. Vizuální kontrola člověkem není provedena; fyzické výstupy se v PP1 nespouštějí. `git diff --check` bez chyb, závěrečný status původních tracked změn odpovídá úvodnímu seznamu. Celá regresní sada SuperPresenteru se nespouštěla.
- Rozhodnutí: zachovány plánované cesty. Tkinter kvůli návaznosti vzhledu a dostupnosti bez nové závislosti. Stabilní identity běhů a rozsahy jsou základ pro budoucí kotvení; přesná pravidla větných kotev se teprve určí v PP5. Při editaci zachovávat ID existujícího obsahu, při duplikaci vytvořit nová ID celé kopie; přímé opakované vložení stejného úseku model odmítá.
- Známé chyby: PP-ENV-1; další blokující chyba PP1 nebyla zjištěna. Omezení pozdějších etap jsou evidována níže.
- Předání PP2: implementovat měření skutečných fontů, geometrii, společné dělení a renderer nad těmito daty. Jeden logický snímek musí mít společné zdrojové rozsahy pro sál/stream, samostatné geometrie obou výstupů. Použít `with_black_breaks()` po paginaci, doplnit úplnost textu a obrazové umístění. Současný inspektor nelze vydávat za náhled rozložení. Doplnit typografii, okraje a pravidla dělení; následně statický náhled obou výstupů. PP2 ani další etapy zde nezahájeny.

## Registr známých chyb a odložených prací

| ID | Popis a reprodukce | Dopad | Cílová etapa | Stav / řešení |
| --- | --- | --- | --- | --- |
| PP-ENV-1 | Zdejší Windows Store Python a `.venv/Scripts/python.exe` končí chybou přístupu při spuštění. | Nelze zde ověřit obvyklý launcher přes venv. | PP9 / prostředí | Obejití pro ověření: bundled Python uvedený v PP1; původní prostředí se neměnilo. |
| PP-LAYOUT | PP1 inspektor nepočítá společné dělení, kamerové obtékání ani skutečnou geometrii. | Nelze použít jako projekční náhled. | PP2 | Plánovaná práce, nezahájeno. |
| PP-STORAGE | JSON codec nebalí média a nemá UI ukládání prezentace, autosave ani recovery. | Ukázka a změny dokumentu jsou pouze v paměti. | PP6 | Plánovaná práce, nezahájeno. |

## Otevřená rozhodnutí

- PP1: uzavřeno — cesty a hranice modulů viz záznam dokončení.
- PP2: výchozí typografie, okraje a odstup kamery, přesná pravidla dělení dlouhého obsahu.
- PP5: detailní pravidla kotvení po odstranění obsahu a chování lišty při rozdílu rozpracované/živé verze.
- PP6: přípona a formát přenosného souboru, retention recovery a převod starého formátování.
- PP8: konkrétní zkratky a externí/globální ovládání — projednat s uživatelem.
- Později: PPTX, volná pole, nastavitelné umístění kamery a další šablony.
