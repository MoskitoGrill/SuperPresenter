# Samostatný webový editor písní — plán a předání

Stav k 3. 11. 2026: implementován funkční základ etapy 1 v `web-song-editor/`.
Aktuální předání implementace, výsledky a ruční scénář jsou v oddílu 8.
Původní průzkum a historické předání jsou ponechány jako kontext.
Tento dokument je trvalý kontext pro další chaty. Před implementací znovu přečíst
aktuální AGENTS.md a ověřit případné změny níže uvedených zdrojů.

## 1. Cíl a rozsah

Kapelník otevře web bez instalace, vytvoří píseň nebo otevře místní XML,
upraví text, jazyky, bloky a pořadí a stáhne kompatibilní XML. Nejprve ověřit
funkčnost, teprve potom řešit vzhled. Aplikace bude později na GitHub Pages.
Bez serverové části, databáze, účtů a synchronizace. Písně zůstávají v prohlížeči;
knihovna `songs/` se nemá automaticky publikovat ani přibalovat do webu.

Odloženo: TXT do třetí etapy, hosting a ověření uživateli do čtvrté, vizuální
design do páté. Databáze, historie změn a automatická synchronizace desktopu
jsou až navazující projekt po uživatelském ověření. Trvalé lokální koncepty,
PWA a File System Access API nejsou podmínkou prvního vydání.

Povinné sdělení u stažení: **„Stažení XML nepřepíše původní soubor.
Stažený soubor musíte sami umístit do knihovny SuperPresenteru a případně
nahradit původní soubor.“** Po stažení nelze tvrdit, že původní soubor byl uložen.
Prohlížeč může změnit jméno souboru přidáním čísla. Při odchodu z rozpracovaného
editoru varovat před ztrátou změn; prohlížeč nemusí varování vždy zobrazit.

## 2. Zjištěný formát a kompatibilita

### Autoritativní zdroje

- `superpresenter/domain/song.py`: uspořádané Song, SongVariant, SongSection,
  SongRepetition; nepoužívat slovníkové projekce jako bezeztrátový model.
- `superpresenter/services/song_repository.py`: XML čtení, zápis a validace.
- `superpresenter/services/song_edit_session.py`: zachování metadat při editaci,
  duplicity, změny sekcí a jejich referencí.
- `superpresenter/services/construct_parser.py`: skutečná gramatika a limity.
- `superpresenter/services/presentation_session.py`: současný WidgetSource,
  import a prezentační interpretace; starý importer je jen fallback pro vadné XML.
- `superpresenter/services/stationary_pages.py`: význam řádků a připojení.
- `song_editor.py`, `tests/test_song_repository.py`, `tests/test_song_compatibility.py`,
  `tests/test_construct_parser.py`, `tests/test_construct_limits.py`.
- `docs/construct_syntax.md`, `docs/construct_inventory.md`: užitečné vysvětlení,
  ale starší počty a některá omezení už neodpovídají aktuálnímu kódu.

### XML

Ilustrační nový soubor (nikoli úprava knihovny):

```xml
<?xml version="1.0" encoding="utf-8"?>
<slide name="Domov" song-id="11111111-1111-4111-8111-111111111111">
  <variant name="čeština">
    <section name="v1">První řádek
Druhý řádek</section>
    <section name="r1">Refrén</section>
  </variant>
  <repetition name="default" main="1">v1 (r1)*2</repetition>
</slide>
```

Kořen je přesně `slide`, název v `name`. Varianty mají libovolné textové
`name`, sekce `name` jako přesné ID a prostý text bez vnořených elementů.
`repetition` má jméno, text výrazu a volitelné `main`; true znamená bez ohledu
na velikost písmen `1`, `true`, `yes`. Zápis repository normalizuje true na `1`,
false atribut vynechá. Opakování může být pod kořenem i uvnitř varianty.
Model ukládá jejich původní umístění; nelze je při importu sloučit podle jména.
Výběr pro běžný editor/presenter: první označené main, jinak `default`, jinak
první jméno. Pomocná vlastnost `selected_repetition` má jiný fallback (první
objekt); pro web použít chování `main_repetition` a otestovat duplicity.

Repository zachovává neznámé atributy všech známých uzlů a neznámé elementy
kořene včetně jejich umístění. Pod variantou dovoluje jen section/repetition;
pod sekcí a repetition žádné děti. DTD odmítá. Neznámá metadata uchovat jako
inertní XML, nikdy jako HTML ani spustitelný obsah. Namespace na kořeni není
součástí podporovaného formátu. Komentáře, přesné uvozovky a původní XML
formátování nejsou smlouvou desktopového roundtripu.

Zachovat pořadí variant, sekcí, opakování, jejich atributy, texty, prázdné řádky,
odsazení a Unicode. Model dělí text pouze na LF. Nevytvářet automaticky
odsazení uvnitř textu sekce. XML parser normalizuje fyzické konce řádků;
explicitní CR desktop zapisuje jako `&#13;`. Rozlišovat modelový text od
prezentačního: WidgetSource odstraňuje okolní a prázdné řádky a používá
další čištění. Výběry řádků proto testovat proti skutečné prezentaci, nikoli
jen proti řádkům textarea. Escapovat XML přes serializer, ne řetězcové náhrady.
První web podporuje UTF-8 s BOM i bez; jiné deklarované kódování musí rozpoznat
a buď bezpečně dekódovat, nebo srozumitelně odmítnout, nikdy potichu poškodit.

### Skutečná knihovna

Čtecí inventura rekurzivně přes `songs/**/*.xml`: **859 souborů**, všech 859
načte SongRepository, **1002 variant**, **3949 sekcí**, **860 repetition**.
135 souborů má více variant, čtyři repetition jsou uvnitř variant a dva soubory
mají duplicitní jméno repetition. Inventura nezahrnuje `dist/`, zálohy ani
samostatnou složku `Testovací písně/`; tu přidat jako zvláštní testovací sadu.

Jazyková jména a počty variant: čeština 853; український - auto 124;
slovenčina 3; ukrajinština 5; přepis 3; український 4; ukr 2;
ukr - transkript 2; hebrejština - transkript 1; uk - transkript 2;
čeština GT 1; čeština - GT 1; cesky 1. Nejde o normalizované jazykové kódy,
některé české varianty mohou obsahovat slovenský text. Názvy nepřejmenovávat
podle detekce jazyka. Jazyková varianta je součást stejné písně.

Používaná ID: v1–v10, r0–r4, b1–b2, samostatné r a b a dvojice v1a/v1b
až v5a/v5b. Nevnucovat jen číslované sloky. V korpusu jsou pouze atributy
slide@name, variant@name, section@name, repetition@name a repetition@main;
stabilní ID zatím není. Zvláštní názvy souborů a již poškozená diakritika
v názvech Kancionálek nejsou důvodem k automatické opravě nebo přejmenování.

### Pořadí a opakování

| Konstrukce | Význam a požadované ovládání |
| --- | --- |
| `v1 r1 v2` | Pořadí karet, vložení a přesun tlačítky i tažením |
| `(v1 r1)` | Skupina se implicitně opakuje dvakrát |
| `(b1)*4` | Skupina s číselným počtem; ne `b1*4` |
| `r1.9` | Výběr jednoho řádku přes ovládací prvek |
| `r1.1:2` | Včetně obou mezí; konec musí být větší než začátek |
| `((v1) (r1))` | Vnořené skupiny, zachovat strom a hranice |
| `v1 @r1` | Připojit k předchozímu bloku při dostupné kapacitě |

Výrazy v korpusu: 62 se závorkami, 12 s hvězdičkou, 9 s tečkou,
3 s dvojtečkou a 1 s @; kategorie se překrývají. Příklad @:
`k_panu_ruce_pozvedam.xml`: `v1 (v1.1) r1 r1 v1 @r1`.
Vnořené opakování např. `vzyvam_jmeno_jezis.xml`.
Závorky se nesmějí zploštit na kopie sekcí: krátký prezentační text a navigace
rozlišují hranice opakovaných skupin. @ nyní připojuje k předchozímu bloku,
nikoli k následujícímu; sál běžně 8 řádků, stream 4, ale kapacita je
věcí prezentačního profilu. První web nemusí emulovat projektorové styly.

Parser rozlišuje velikost písmen a odděluje ASCII mezerou. Prezentační vstup
spojuje neprázdné fyzické řádky guide mezerou. Kanonický nový zápis generovat
s mezerami a explicitním násobením skupin, původní nezměněný guide zachovat.
Limity současného parseru: 16384 znaků, 32 úrovní, 4096 kroků/řádků;
kontrolovat i rozbalení s délkami textů a více jazyky. Nerozbalovat velké skupiny
před kontrolou limitu. Historicky přijímá `.0`, nulové opakování a prázdné
skupiny; nové UI je nevytváří, import je zachová a označí jako rizikový.
Rozsahy ověřovat také proti prezentačním řádkům každé vybrané varianty.

Po normalizaci fyzických řádků přijato 856/860 guide. Čtyři odmítnutí:

- `buh_vsech_narodu.xml`: dvakrát `v1 r1 v2 b`, neexistující b.
- `duchu_svaty_jsi_tu_vitany_(suchdol_version).xml`: `b1.2*4`, násobení
  bez skupiny; doporučená oprava přes vizuální opakování vybraného řádku.
- `jak_vzacna_milost_otcova.xml`: `V1 V2 V3`, neshoda velikosti písmen.

Nic z toho neopravovat automaticky. Vadný guide ukázat jako uzamčený importovaný
blok s diagnostikou a nabídnout explicitní sestavení náhrady. Uživatel nemusí
psát interní syntaxi. Změny textu nesmějí potichu smazat nepochopené pořadí.
Duplicitní názvy nebo více main označit a zachovat; řešení kolize musí být
výslovné. Chybějící sekce mezi jazyky hlásit, protože prezentace používá průnik
sekcí zvolených jazyků. Sjednocení při inventuře není důkaz kompatibility všech
jazykových kombinací. Neplatné XML odmítnout bez ztráty aktuálního konceptu;
neportovat tolerantní starý řádkový parser jako tichou opravu.

## 3. Technická architektura

Zvoleno pro implementaci: izolovaná složka **`web-song-editor/`**, TypeScript,
Vite a prosté DOM komponenty bez aplikačního frameworku. Statická aplikace,
žádný backend ani vazba na desktopové GUI; vývojář má Node, uživatel jen
prohlížeč. Tento dokument neurčuje aktuální verze balíčků — při implementaci
ověřit podporované verze a vytvořit lockfile. V této etapě nic neinstalovat.

Navržené moduly: `src/domain/` pro uspořádaný model a strom pořadí,
`src/xml/` pro DOMParser/XMLSerializer a validaci, `src/construct/` pro port
gramatiky, `src/ui/` pro formuláře a karty, `src/io/` pro soubory a později TXT.
Interní klíče objektů UI oddělit od XML section ID a song-id. Ukládat pole,
ne mapy podle názvu. U importovaných uzlů uchovat původní umístění a metadata;
needitované guide ponechat v původní podobě. Parser a serializer nesmějí
záviset na UI. Testovací JS runtime a Vitest, pro průchod prohlížečem Playwright;
kompatibilní fixture výstupy porovnat se současným Pythonem, ne pouze s vlastním
portem. Web nevkládat do `docs/`, aby se nepletla dokumentace a publikovaný web.

File input a File API pro čtení, Blob a download pro výstup. Žádný přístup
k libovolným cestám disku. Vykreslovat text přes textContent/textarea.
Před parsováním odmítnout DTD, hlídat velikost souboru a strukturální limity;
konkrétní limit XML stanovit podle největší skutečné písně a testu odezvy.
Změny sekcí aktualizují reference ve všech pořadích; odstranění nabídne
konkrétní dopad a neprovede tiché přečíslování legacy ID.

## 4. Etapy a podmínky dokončení

1. **Základ editoru:** vytvořit izolovanou aplikaci, název, jazyk, bloky Sloka,
   Refrén, Bridge a vlastní typ, texty, vizuální pořadí, otevření a stažení XML,
   dirty stav a sdělení o ručním nahrazení. Nová ID v1/r1/b1 generovat interně.
   První řez umí jednoduché guide; složité importy uchová a bezpečně označí.
   Není ještě splněna úplná kompatibilita knihovny.
2. **Úplná kompatibilita:** více jazyků a pojmenovaných pořadí, main, skupiny,
   vnoření, počty, řádky/rozsahy, @, legacy ID, nested repetition, duplicity,
   metadata a chybové stavy. Celý korpus projde modelovým roundtripem,
   validní guide diferenčním testem a nevalidní se nezmění bez zásahu uživatele.
   Kompatibilita neznamená automaticky opravit staré vadné písně.
3. **TXT import/export:** verzovaný UTF-8 formát, song-id v hlavičce, explicitní
   oddělovače jazyků/sekcí/pořadí a escaping oddělovačů. Navrhnout samostatnou
   specifikaci s ukázkami před implementací. Zachovat pořadí, Unicode a mezery;
   úplná metadata a strom musí mít reprezentaci, jinak export předem označit
   jako ztrátový a vyžádat vědomou volbu. TXT bez ID nepárovat podle názvu.
4. **GitHub Pages a uživatelské ověření:** build do `web-song-editor/dist`,
   relativní base a žádné routerové závislosti na serverových přepisech.
   Samostatný workflow nasazuje jen build webu. Otestovat projektovou URL,
   načtení a download v cílových prohlížečích a reálný import do používaného EXE.
   Kapelníci vyzkouší novou píseň, úpravu, více jazyků a výslovnou kopii;
   zapsat zpětnou vazbu před dalšími funkcemi. Hosting nyní neprovádět.
5. **Vzhled:** až po ověření funkcí upravit grafiku a responzivní rozložení.
   Přístupnost formulářů a ovládání klávesnicí musí fungovat už od základu.

## 5. Identita a výslovné kopie

Návrh: **UUID v4 v kořenovém atributu `song-id`**, bez namespace, generované
kryptografickým API prohlížeče. Název ani cesta nejsou identita. Přejmenování,
změna textu, jazyka či pořadí zachová ID. Pouhé stažení jiného jména souboru
nevytváří novou píseň. Jazyková varianta není samostatná verze.

Akce **„Vytvořit kopii“** vytvoří nové UUID a vyžádá vlastní název, například
„Domov (Suchdol version)“. Původní koncept ponechat dostupný; jasně zobrazit,
že se pracuje s kopií. Obyčejné Uložit/Stáhnout nové UUID negeneruje.

Kompatibilita ověřena čtením kódu a experimentem: `Song.attributes` zachová
song-id přes `dumps → loads`; současný WidgetSource načetl dočasné XML s ID,
varianty a repetition a ponechal ID v modelu. Desktop tento atribut zatím
neinterpretuje ani negeneruje, což nebrání promítání. Editační cesta kopíruje
atributy přes deepcopy. Nejde o důkaz všech distribuovaných historických EXE:
ručně ověřit používanou distribuci a následné uložení jejím editorem.
Při fallbacku pro vadné XML může být neznámý atribut ztracen; negarantovat
identitu přes takový opravný import. ID není bezpečnostní údaj ani autorizace.

Starší XML bez ID: při prvním otevření přidělit konceptu UUID a při prvním
stažení ho zapsat, nikdy neměnit původní soubor na disku. Opětovné otevření
stejného starého souboru bez ID může vytvořit jiné UUID. Vysvětlit proto, že
pro další práci se používá nově stažený soubor s ID. Chybné nebo víceznačné ID
nesmí být potichu nahrazeno; nabídnout explicitní opravu či vytvoření kopie.

Budoucí migrace knihovny: nejprve záloha, čtecí inventura a report existujících,
chybějících, chybných a duplicitních ID; pak výslovně schválené doplnění UUID
jen chybějícím souborům, mapovací protokol a idempotentní ověření roundtripu.
Duplicity ID řešit jednotlivě (dvě revize versus úmyslné kopie), nikdy podle
jména. **Migrace celé knihovny se nyní neprovádí.** Ruční kopie souboru zachová
ID a není náhradou akce Vytvořit kopii.

Pro budoucí TXT a synchronizaci přenášet song-id a samostatnou revizní informaci
(např. hash výchozího normalizovaného obsahu). Hash je detekce změny, nikoli
identita. Stejné ID s odlišným obsahem znamená možný konflikt, ne automatické
přepsání. Import bez ID nabídne novou píseň nebo výslovné přiřazení uživatelem;
názvy mohou být pouze nápovědou. Konkrétní revizní protokol je odložen.

## 6. Kontrolní seznam funkcí a testů

- [ ] Nová píseň, načtení, úprava, stažení, opětovné otevření; XML přijme desktop.
- [ ] Sloka/Refrén/Bridge/vlastní blok; přidání, odstranění a přesun klávesnicí.
- [ ] Více jazyků bez přejmenování, společné reference a diagnostika chybějících sekcí.
- [ ] Více pořadí, main a jeho fallback; žádné ztracené nested/duplicitní repetition.
- [ ] Skupiny a vnoření, počet, řádky a rozsahy, @; zachované hranice skupin.
- [ ] Všechny skutečné legacy identifikátory; case sensitivity a neznámé reference.
- [ ] 859 XML modelových roundtripů; nezměněné texty, pořadí a metadata.
- [ ] Diferenční test portu proti Python parseru a prezentačním řádkům;
  regresní fixture čtyř vadných guide a testovací písně mimo songs.
- [ ] Prázdné názvy/texty, duplicity, chybějící repetition, více main, neznámá metadata.
- [ ] UTF-8/BOM, diakritika, ukrajinština, XML entity, CR/LF, mezery a prázdné řádky.
- [ ] Vadné XML a nepodporované struktury bez ztráty rozpracované písně;
  DTD, příliš velký vstup a extrémní násobení bezpečně odmítnuty.
- [ ] Zachování UUID při úpravě/přejmenování a opětovném importu; nové UUID jen
  pro novou píseň/kopii, legacy bez ID a konflikt ID mají jasný postup.
- [ ] Změna/odstranění sekce řeší všechny reference bez tichého přepisování.
- [ ] Stažení jasně odlišeno od nahrazení souboru; odchod a otevření jiného
  souboru chrání neexportované změny, zrušení dialogu nic nezmění.
- [ ] TXT roundtrip včetně ID, všech jazyků a pořadí; změněný název nemění identitu.
- [ ] GitHub Pages pod cestou repozitáře, běžné desktopové i mobilní prohlížeče,
  klávesnice, žádné uploady písní a žádná publikovaná soukromá knihovna.

## 7. Historické předání průzkumu (2. 11. 2026)

### Dokončeno a změněné soubory

Přečteno `C:/Users/moski/Documents/AGENTS.md` (požaduje české shrnutí změn).
V repozitáři nebyl nalezen další AGENTS.md. Prozkoumán model, repository,
editační a prezentační cesta, parser, dokumentace, testy a reálná knihovna.
Jediný zamýšlený změněný soubor této etapy: `docs/web-song-editor-plan.md`.
Desktop, XML knihovna, konfigurace i závislosti zůstaly bez úprav.
Žádná implementace editoru, migrace, nasazení ani commit nebyly provedeny.

### Provedené kontroly a výsledky

- Čtecí inventura: 859/859 načteno; podrobné počty a čtyři chyby guide výše.
- In-memory `loads(dumps(song)) == song`: prošlo všech 859 souborů;
  jde o modelovou, nikoli bajtovou shodu nebo záruku projekce všech kombinací.
- UUID atribut na kopii Domov: prošel repository roundtrip a aktuální
  WidgetSource v dočasném souboru. Knihovna nebyla zapsána.
- Existující sada repository + compatibility + parser + limits spuštěná
  modulem unittest: 34 testů, 3 chyby. Dvě PermissionError/WinError 5 při
  `os.replace` v dočasných souborech, jedna chyba importu test_release_stability
  kvůli cestě při modulovém spuštění. Neoznačovat celou sadu za úspěšnou;
  příčina přístupu k souborům nebyla prokázána.
- Následně parser + limits s `tests` na sys.path: **25 testů OK**.
  In-memory korpusový roundtrip obchází problematický zápis, není jeho opravou.
- Python ve workspace sandboxu nešel spustit; kontroly proběhly po schválení
  spuštění mimo sandbox. První inventura narazila na kódování konzole,
  výpis opakován s bezpečným zobrazením Unicode.

### Omezení a rozhodnutí

Nebylo spuštěno GUI ani historické distribuované EXE. Neověřen hosting,
prohlížeče ani TXT (dosud neexistují). Není ověřena úplná shoda s každou
historickou verzí SuperPresenteru. Návrh UUID je kompatibilní s aktuální
zdrojovou cestou; jeho zavedení do existující knihovny je samostatná práce.
Žádné automatické opravy vadných guide, jazykových názvů nebo diakritiky.
Jednoduchá statická aplikace a stromové pořadí jsou rozhodnutí pro další etapu.

### Další krok a ruční kontrola

Příští chat má začít tímto dokumentem a implementovat pouze etapu 1 v nové
složce, s jasným bezpečným režimem složitých importů. Nezasahovat do desktopu.
Před vydáním dokončit etapu 2, neprezentovat omezený prototyp jako plně
kompatibilní editor celé knihovny.

Uživatel má nyní ručně projít rozsah etap, návrh kopie a UUID, čtyři vadné guide
a rozhodnout o jejich zamýšleném významu před pozdější explicitní opravou.
Při implementaci ověřit kopii XML s song-id v používaném EXE: otevřít,
promítnout, upravit, uložit a zkontrolovat zachování ID i textu. Původní XML
pro tuto kontrolu zálohovat. Také zopakovat zápisové testy v prostředí bez
chyb přístupu, než jejich výsledek považujeme za uzavřený.

Po kontrole provést ruční commit dokumentu; agent commit nevytváří.

## 8. Předání implementace (3. 11. 2026)

### Hotovo

Izolovaný statický TypeScript/Vite editor s prostými DOM komponentami; žádný
backend, databáze, přihlášení ani nasazení. Jednoduché přístupné formuláře,
ovládání tlačítky i klávesnicí, bez ladění designu. Desktop a knihovna nejsou upraveny.

- Nová píseň, název, import místního UTF-8 XML a stažení přes Blob/download.
- Sloka, refrén, bridge a vlastní typ s generovaným ID; texty, přidání,
  odebrání a přesuny částí. Odebrání vypíše dopad na všechny varianty i pořadí,
  vyžádá potvrzení a atomicky odmítne vyprázdnění kteréhokoli pořadí.
- Vizuální posloupnost celých částí, opakované reference, přesuny a odebrání
  jednotlivých výskytů. Jedna změna refrénu se projeví všude; žádné psaní značek.
- Náhled výsledné posloupnosti. Importované jazykové varianty i pojmenovaná
  pořadí se přepínají; počáteční výběr main → default → první.
- Zachování UUID při přejmenování, editaci a opětovném otevření; legacy XML
  bez ID dostane UUID konceptu. Explicitní kopie požaduje odlišný vlastní název
  a nové UUID, původní koncept zůstává v paměti dostupný tlačítkem návratu.
- Dirty stav, potvrzení před novou/otevřenou písní i zahozením rozpracované
  kopie a beforeunload. Hlídá se i rozpracovaný původní koncept při práci s kopií.
- Povinné sdělení, že download nenahradí původní soubor, vysvětlení legacy ID
  a možného číslování názvu staženého souboru prohlížečem.

### Soubory a technická rozhodnutí

- `web-song-editor/package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`,
  `tsconfig.json`, `vite.config.ts`, `index.html`, `.gitignore`: izolovaný projekt,
  reprodukovatelné závislosti, explicitně povolený build esbuildu, relativní base.
- `src/domain/song.ts`: model dokumentu, identita, kopie a operace částí.
  Zdrojem pravdy je uspořádaný XML DOM; pole odkazují na původní uzly,
  nikoli na slovníky podle jména. Tím se zachovají atributy a umístění metadat.
- `src/xml/songXml.ts`: striktní import, validace a XMLSerializer export;
  původní nepřepsané guide zůstávají přesně v DOM, CR se zapisuje jako entita.
- `src/construct/simple.ts`: úmyslně pouze jednoduchá podmnožina gramatiky.
  Nejde o dokončený port parseru; další konstrukce se odmítají, nezplošťují.
- `src/io/files.ts`, `src/ui/main.ts`, `src/ui/style.css`: soubory, formuláře,
  karty částí a pořadí, náhled, ochrana konceptů. Text se nevkládá jako HTML.
- `tests/editor.test.ts`: doménové/XML kontroly a čtecí inventura obou sad;
  `tests/verify_desktop.py`: porovnání přes současný repository/presenter/parser;
  `playwright.config.ts`, `tests/browser/editor.spec.ts`: skutečný Chromium průchod.
- `README.md`: lokální spuštění, ověření a omezení. Tento předávací dokument
  je aktualizován; dříve byl v pracovním stromu nesledovaný a zůstává bez commitu.

Verze byly ověřeny při instalaci; lockfile obsahuje TypeScript 5.9.3,
Vite 7.3.7, Vitest 4.1.12, jsdom 27.4.0, Playwright 1.64.1. Node v prostředí:
24.22.1, pnpm 11.25.0. Podmínky Node pro Vite ověřeny v oficiální příručce
https://vite.dev/guide/. Instalace potřebovala mimo sandbox systémové CA Windows
(`NODE_USE_SYSTEM_CA=1`); ověřování TLS nebylo vypnuto.

### Automaticky ověřeno

- TypeScript kontrola + produkční build: OK; výsledkem je pouze izolovaný web,
  žádné importy knihovny písní do aplikačního kódu. Build má relativní asset URL.
- Vitest: **12 testů OK**, včetně entity escaping, Unicode, CR, prázdných řádků,
  metadat, nested repetition, UUID, kopie, atomického odebrání, limitů a odmítání.
- Čtecí inventura skutečných sad: **861 souborů = 859 songs + 2 testovací**.
  **783 přijato**, **78 bezpečně odmítnuto** (76 z knihovny + oba testovací).
  Odmítnutí zahrnují složitá/neplatná pořadí, duplicity a chybějící strukturu.
  Není to plná kompatibilita knihovny; žádná automatická oprava neproběhla.
- Všech **783** přijatých souborů prošlo webovým import–exportem a porovnáním
  modelu přes současný SongRepository, metadat a viditelných textů skutečného
  WidgetSource. Každý exportovaný guide přijímá současný Python parser a limit
  rozbalení. Navíc prošla nová píseň s opakovaným refrénem a XML entitami.
- Playwright/Chromium: **1 integrační scénář OK**: dvě sloky a refrén,
  posloupnost v1–r1–v2–r1, změna obou výskytů refrénu, download, zachování ID,
  zrušená nová píseň, odlišné ID kopie, návrat původního konceptu, reimport
  downloadu a odmítnutí vadného XML bez ztráty konceptu.
- XML skutečně stažené Chromiem načetl **SongRepository i WidgetSource bez
  fallbacku či varování**; ověřeny text refrénu a pořadí současným parserem.
- Výsledky vznikly pouze v ignorovaném `web-song-editor/test-output/`:
  `corpus.json` obsahuje cesty přijatých exportů a důvody odmítnutí, dále jsou
  zde roundtrip XML, nová píseň a skutečný browser download. Originály se pouze četly.
- Spouštění Pythonu a některé Node/pnpm/prohlížečové operace blokoval sandbox;
  úspěšná finální ověření proběhla po povolení mimo něj. První Playwright běh
  timeoutoval na lokálním serveru, finální běh používá samostatný port 5187.
- Historické zápisové testy desktopu z oddílu 7 nebyly touto etapou opraveny
  ani jejich problémy prohlášeny za vyřešené. Desktopové GUI nebylo spuštěno.

### Bezpečný rozsah a zbývající omezení

XML do 1 MiB (největší skutečná píseň měla 5588 B), 10 000 elementů a 64 úrovní;
guide do 16 384 znaků, 4096 výskytů i řádků souhrnně přes jazyky. Limit 1 MiB
je konzervativní ochrana; není výsledkem formálního výkonového benchmarku.
UTF-8 s BOM i bez, ostatní deklarovaná kódování a neplatné UTF-8 se odmítají.

Skupiny, řádkové výběry/rozsahy, @, neznámé reference, rozdílné části jazyků,
duplicitní/prázdná jména, více main, vadné ID, DTD, vnořený obsah section/repetition
a instrukce mimo kořen se odmítají s diagnostikou. Aktuální koncept zůstane.
Neznámé atributy a kořenové elementy se uchovávají inertně; přesné formátování
XML/deklarace není smlouvou. Složité importy nemají zatím režim čtení ani
vizuální explicitní náhradu guide: v této etapě jsou celé odmítnuty ke změnám.

Nevytváří se další jazykové varianty a pojmenovaná pořadí, nepřejmenovávají se
stávající ID částí ani nemění main. Přesuny jsou tlačítky, tažení není doplněno.
Náhled není emulace čištění, stránkování a stylů projektoru. Koncepty jsou jen
v paměti, dostupná je jedna kopie a původní koncept; bez autosave a historie.
Download znamená zahájení stažení, prohlížeč nepotvrzuje skutečný zápis na disk.
Beforeunload závisí na prohlížeči. Hosting, TXT a jiné prohlížeče nejsou ověřeny.

### Ruční testy, které zbývají

1. Spusťte web podle `web-song-editor/README.md`, zvolte Nová píseň a název
   „Zkouška editoru“. Do v1 napište první sloku. Přidejte Sloku (v2), napište
   druhou sloku. Přidejte Refrén (r1) a napište refrén.
2. Výchozí pořadí již obsahuje v1. Postupně klikněte Zařadit r1, Zařadit v2,
   Zařadit r1. Ověřte sloka 1 – refrén – sloka 2 – refrén. Vyzkoušejte přesuny
   výskytů i částí nahoru/dolů; přesun části nesmí měnit pořadí přehrávání.
3. Změňte text r1 pouze v kartě části. V náhledu musí být nový refrén dvakrát.
   Přidejte diakritiku, znak &, < a prázdný řádek.
4. Stáhněte XML; původní soubor se tím nepřepisuje. Na testovací kopii knihovny
   otevřete stažené XML v používaném SuperPresenter EXE a promítněte celé pořadí.
   Ověřte text, opakování a zamýšlené prázdné řádky podle desktopového čištění.
   Zkontrolujte song-id, uložte přes desktopový editor a ověřte, že ID zůstalo.
5. Otevřete export znovu ve webu, změňte název/text, znovu stáhněte: song-id musí
   být stejný. Vytvořte výslovnou kopii s jiným názvem: musí mít jiné song-id;
   tlačítko návratu musí vrátit původní koncept včetně jeho rozpracovaných změn.
6. Rozpracujte změnu, zvolte Nová píseň nebo otevřete jiné platné XML; zrušte
   potvrzení a ověřte zachování všech polí. Vyzkoušejte také zavření/obnovení
   stránky a varování prohlížeče, včetně neexportovaného původního konceptu při
   práci s exportovanou kopií. Zrušení výběru souboru nesmí změnit píseň.
7. Zkuste vadné XML a složitý guide, například `vzyvam_jmeno_jezis.xml`:
   očekává se srozumitelné odmítnutí a zachování současného konceptu. Vyzkoušejte
   i UTF-8 BOM, více jazyků a pořadí u podporované písně a ovládání klávesnicí.
8. Odeberte část použitou vícekrát: potvrzení musí uvést počet odkazů;
   zrušení nic nezmění, potvrzení odstraní odkazy ve všech pořadích/jazycích.
   Odstranění poslední použité části musí skončit vysvětlením bez změny dokumentu.

### Další krok

Ručně projít scénář v používaném EXE a cílových prohlížečích. Poté etapa 2:
stromový port celé gramatiky s diferenčními testy, bezpečný uzamčený režim
složitých importů a výslovná náhrada vadného guide; následně plná editace variant,
pojmenovaných pořadí, main a kolizí. Teprve po úplné kompatibilitě řešit TXT,
hosting a vzhled. Není provedena migrace knihovny ani commit.

**Připomenutí: po kontrole vytvořit ruční commit; agent ho nevytváří.**
