# Samostatný webový editor písní — plán a předání

Stav k 3. 11. 2026: příprava GitHub Pages dokončena; aktuální nasazení a kontroly v oddílu 25. Veřejná publikace zatím neověřena (HTTP 404).
Aktuální předání DOCX, výsledky a ruční scénář jsou v oddílu 12; TXT v oddílu 11.
Nové zadání nahrazuje původní požadavek identity v TXT z oddílů 3–6 a 10:
TXT nyní nemá hlavičku ani ID; při shodě názvu vyžaduje ruční rozhodnutí.
Oddíly 7–8 popisují historický stav před těmito změnami.
Původní průzkum a historické předání jsou ponechány jako kontext.
Tento dokument je trvalý kontext pro další chaty. Před implementací znovu přečíst
aktuální AGENTS.md a ověřit případné změny níže uvedených zdrojů.

## 1. Cíl a rozsah

Kapelník otevře web bez instalace, vytvoří píseň nebo otevře místní XML,
upraví text, jazyky, bloky a pořadí a stáhne kompatibilní XML. Nejprve ověřit
funkčnost, teprve potom řešit vzhled. Aplikace bude později na GitHub Pages.
Bez serverové části, databáze, účtů a synchronizace. Písně zůstávají v prohlížeči;
knihovna `songs/` se nemá automaticky publikovat ani přibalovat do webu.

Aktuální pořadí: 3. TXT, 4. DOCX, 5. layout a pohodlné ovládání, 6. finální vizuální vzhled, 7. GitHub Pages a uživatelské ověření. Databáze, historie změn a automatická synchronizace desktopu
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
3. **TXT import/export:** hotový jednoduchý formát bez technické hlavičky a ID;
   aktuální pravidla a omezení v oddílu 11 a `docs/song-txt-format.md`.
4. **Word DOCX:** hotový přenos textů se stejným rozhodováním jako TXT;
   aktuální pravidla a omezení v oddílu 12 a `docs/song-docx-format.md`.
5. **Layout a pohodlné ovládání:** aktuální etapa. Rozlišit název, texty,
   pořadí a náhled, dát prostor psaní a zpřístupnit akce, klávesnici a malé
   obrazovky. Jednoduchý neutrální vzhled; předání a kontroly v oddílu 13.
6. **Finální vizuální vzhled:** navázat na ověřené pracovní postupy a rozložení.
   Až zde řešit konečnou paletu, vizuální styl a případné dekorace.
7. **GitHub Pages a uživatelské ověření:** build do `web-song-editor/dist`,
   relativní base a žádné routerové závislosti na serverových přepisech.
   Samostatný workflow nasazuje jen build webu. Otestovat projektovou URL,
   načtení a download v cílových prohlížečích a reálný import do používaného EXE.
   Kapelníci vyzkouší novou píseň, úpravu, více jazyků a výslovnou kopii;
   zapsat zpětnou vazbu. Hosting nyní neprovádět.

Databáze, přihlášení a synchronizace nejsou součástí těchto změn.

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

## 9. Předání kompatibility a obnovy (3. 11. 2026)

### Rozsah a chování

Použity pokyny `C:/Users/moski/Documents/AGENTS.md`; další AGENTS.md nenalezen.
Změny jsou izolované ve webovém editoru a dokumentaci. Desktopové zdroje,
závislosti, knihovna XML ani konfigurace desktopu nebyly změněny. Bez databáze,
serveru, hostingu, TXT a návrhu finálního vzhledu. Commit nebyl vytvořen.

- Jazykové varianty lze přepínat, přidávat a výslovně přejmenovat. Nový jazyk
  dostane všechny existující ID s prázdnými texty; nejde o automatický překlad.
  Pořadí částí lze měnit pro aktuální jazyk, bez nutnosti shodných částí ve všech
  jazycích. Chybějící odkazované části se hlásí; export je přesto zachová.
  Tlačítko „Odebrat jazyk“ po potvrzení odstraní vybraný jazyk a jeho texty;
  poslední jazyk odstranit nelze. Vnořená pořadí se přesunou ke kořeni na místo
  odebírané varianty, aby zůstalo zachováno jejich pořadí, metadata i main.
  Potvrzení upozorní na části, které po odebrání neexistují v jiném jazyce;
  případné odkazy se nemažou a zobrazí se jako uzamčené s diagnostikou.
- Pořadí lze přidat, přejmenovat a výslovně nastavit jako jediné výchozí.
  Původní umístění repetition pod variantou zůstává. Duplicity jmen, prázdná
  jména a více main se zachovávají; výběr má číslo, umístění a vysvětlení
  fallbacku první main → default → první. Ke sloučení podle jména nedochází.
- Stromový editor nabízí opakování bloku, seskupení se sousedem, vnoření,
  počet opakování, rozpuštění skupiny do jednoho průchodu, přesuny i výběry
  řádků/rozsahů a připojení k předchozímu bloku. Není třeba psát syntaxi.
  Skupiny se nezplošťují; nově upravený guide používá explicitní násobení.
- Každý neupravený guide zůstává přesně ve svém původním textu. XML DOM
  zachovává texty, neznámé atributy, metadata a umístění uzlů. Odstranění části
  přepisuje pouze pořadí, která na tuto část skutečně odkazovala.
- Neplatné guide, neznámé reference a rizikové historické konstrukce (řádek 0,
  prázdná skupina, nulové opakování) zůstávají uzamčené. Texty lze upravit,
  původní výraz prohlédnout a XML stáhnout po upozornění na všechny problémy.
  „Sestavit náhradní pořadí“ po potvrzení výslovně nahradí vybraný výraz první
  částí; poté se používá běžný vizuální editor. Před náhradou lze stáhnout originál.
  Neplatné XML se odmítne s podrobností parseru, aktuální koncept zůstává.
- Odstranění části ukáže dopad v každém pořadí, včetně odkazů uvnitř skupin.
  Zrušení nemění nic. Po potvrzení se odstraní odkazy ve všech jazycích a
  vyprázdněné skupiny. Vyprázdnění celého pořadí je atomicky odmítnuto.
  Jakékoli uzamčené pořadí blokuje mazání částí, protože dopad nelze zaručit.
- Chybějící pořadí ani prázdný název se při importu automaticky nedoplňují.
  Nové pořadí vzniká až výslovnou akcí. Export s prázdným názvem používá
  název souboru `pisen.xml`; desktop může název pro prezentaci odvodit ze souboru.
- Identita běžné úpravy i exportu zůstává stejná; pouze nová píseň, legacy
  import bez ID a výslovná kopie generují UUID. Kopie nezmění původní koncept.
- Místní úložiště prohlížeče průběžně zachovává XML, identitu, dirty stav,
  výběry a případný původní koncept při práci s kopií. Po obnovení se načtou.
  Nejde o sdílené ani trvalé uložení; závisí na stejném prohlížeči, profilu
  a adrese webu. Vymazání dat, anonymní režim či kvóta mohou obnovu znemožnit.
  Selhání zápisu je viditelné. Nečitelný koncept se automaticky nepřepíše:
  lze stáhnout surovou JSON zálohu a až výslovně povolit nový místní koncept.
  Stále je nutné stahovat XML a ručně ho umístit do knihovny SuperPresenteru.

### Změněné soubory

- `src/construct/tree.ts`: port gramatiky, uspořádané typy, limity před
  rozbalením, serializace a práce s odkazy. Starý `simple.ts` zůstává pomocnou
  přísnou podmnožinou; UI ho již pro pořadí nepoužívá.
- `src/domain/song.ts`: stromové operace, diagnostika napříč jazyky, kontrola
  prezentačních řádků, varianty, pojmenovaná pořadí, výchozí a bezpečné mazání.
- `src/xml/songXml.ts`: oddělení strukturálních chyb od zachovaných vadných
  guide, podrobnosti chyb XML, podpora duplicitních/nested a chybějících pořadí.
- `src/ui/main.ts`, `src/io/files.ts`: formuláře, strom, ochrany, obnova
  konceptů a JSON záloha. Všechny importované hodnoty se vykreslují jako text.
- `tests/editor.test.ts`, `tests/verify_desktop.py`,
  `tests/browser/editor.spec.ts`: sémantika korpusu, diferenční strom/řádky,
  prohlížečové změny, identity, neplatné guide a obnovení kopie i originálu.
- `web-song-editor/README.md` a tento dokument: ovládání, výsledky a omezení.

### Automatické kontroly

- TypeScript a produkční Vite build: OK. Knihovna písní se do buildu nebalí.
- Vitest: **13 testů OK**, včetně celého aktuálního korpusu **862 XML**
  (860 v `songs/`, včetně souboru `.xml`, a 2 v `Testovací písně/`). Všechna
  se načetla a exportovala; originály se pouze četly. Aktuální počet se liší
  od historické inventury; test dynamicky prochází dostupné soubory.
- **862 sémantických roundtripů ověřeno Pythonem**: rovnost SongRepository
  modelů, metadat, umístění repetition a skutečných textů WidgetSource.
  Přidělené legacy UUID se při porovnání zohlední. U prázdného XML názvu se
  ignoruje jen prezentační název odvozený z odlišné cesty testovacího exportu.
  Nevyžaduje se stejné formátování XML, atributové pořadí ani odsazení mezi uzly.
- **865 guide**: **861 shodných stromů** proti Python parseru, včetně skupin,
  počtů, řádků/rozsahů a pin; **4 shodně odmítnuté**, zachované beze změny
  (`buh_vsech_narodu` dvakrát, Suchdol `b1.2*4`, `V1 V2 V3`). Dalších
  10 souborů nemá žádné pořadí. Webové čištění řádků je porovnáno s WidgetSource
  pro každou část každého jazyka; limity se ověřují i s více jazyky.
- Chromium/Playwright: **5 scénářů OK**. Základní editace a identita; jazyky,
  počet skupiny, pojmenované/výchozí pořadí, obnova kopie i originálu a
  zrušené/potvrzené mazání; uzamčený vadný guide po editaci, exportu a reloadu.
  Čtvrtý scénář ověřil ochranu nečitelného místního konceptu a stažení přesné
  JSON zálohy bez automatického přepsání. Skutečné základní i pokročilé XML načetl desktopový loader
  bez fallbacku. Vadný guide v dalším downloadu zůstal nezměněn.
  Pátý scénář ověřil zrušení i potvrzení odebrání jazyka, přesun jeho pořadí,
  zachování identity, obnovu stránky a export. Doménový test navíc kontroluje
  duplicity/main, chybějící část a atomické odmítnutí odstranění posledního jazyka.
- Existující desktopové testy parseru a limitů:
  `python -m unittest discover -s tests -p test_construct*.py`: **25 OK**.
  Nejde o kompletní sadu desktopového GUI. Doplňkově znovu spuštěny existující
  `test_song_repository.py`: 10 testů, 1 chyba v korpusovém zápisu; a
  `test_song_compatibility.py`: 1 test, 4 chyby podtestů. Všechny chyby jsou
  PermissionError/WinError 5 při `os.replace` dočasného XML, i mimo sandbox.
  Stejná třída problému byla zaznamenána už v oddílu 7; přesná příčina není
  prokázána a v této webové etapě se neopravovala. Tyto sady nejsou úspěšné.
- Vitest, Python a Chromium vyžadovaly povolení mimo sandbox (blokovaný rename
  dočasných souborů / spuštění Pythonu). Žádné závislosti nebyly instalovány.
  Výstupy a report zůstávají jen v ignorovaném `web-song-editor/test-output/`.

### Známá omezení a další práce

Náhled není projektor: nepočítá kapacitu stránek, styly ani skutečné spojování @.
Řádková čísla odpovídají desktopovému odstranění prázdných řádků a levého
odsazení; diagnostika ověřuje všechny jazyky. Nově přidaný jazyk má prázdné
texty, proto může výběr řádků dočasně uzamknout pořadí. Po doplnění textu
stisknout „Znovu ověřit pořadí po změně textů“ (nebo přepnout pořadí).

Uzamčené konstrukce nelze jednotlivě opravovat vizuálně; lze je zachovat nebo
výslovně sestavit náhradu. Poškozené XML a ID, DTD, namespace známých uzlů,
vnořený obsah section/repetition, prázdná/duplicitní ID částí či jazyků se
odmítají. Početní hodnoty mimo bezpečná celá čísla JS se vizuálně neupravují.
Limity XML 1 MiB / 10 000 uzlů / 64 úrovní, guide 16 384 znaků / 32 skupin /
4096 kroků a řádků. Překročený guide se zachová uzamčený, nerozbaluje se.
Pouze UTF-8, přesné formátování XML není smlouvou.

Není mazání celých pojmenovaných pořadí, přejmenování ID částí,
drag-and-drop, historie ani řešení souběžné práce více oken (poslední místní
zápis vyhraje). Udržuje se jedna kopie a její originál. JSON záloha nečitelného
konceptu nemá samostatné importní UI. Místní úložiště nenahrazuje export.
Testován Chromium; Firefox, Safari, mobilní prohlížeče, hosting a distribuované
EXE zbývají ručně. Zatím neprohlašovat kompatibilitu všech historických EXE.

### Co ručně otestovat

1. Vícejazyčná píseň: přepnout jazyky, upravit každý samostatně, přidat jazyk
   a doplnit text. Export/reimport musí zachovat názvy, texty a song-id.
2. Více pořadí: přidat a přejmenovat pořadí, nastavit výchozí; otevřít export
   znovu. U nested/duplicitních pořadí ověřit jejich zachování a rozlišení.
3. Pokročilé opakování: `vzyvam_jmeno_jezis.xml`,
   `k_panu_ruce_pozvedam.xml` a obě Testovací písně; změnit počet, skupinu,
   vnoření, řádky a připojení pomocí ovladačů. Ověřit průchod v desktopu.
4. Odstranění používané části: zrušit a pak potvrdit, ověřit všechna pořadí
   a jazyky. Poslední odkazovanou část ani část při uzamčeném guide nesmazat.
5. Neplatný soubor: vadné XML nesmí nahradit koncept. Vadný odkaz se musí
   zobrazit jako uzamčený; změna textu ani export ho nesmí tiše odstranit.
6. Obnovení stránky: rozpracovat originál i kopii, obnovit stránku a ověřit
   obě práce a identity. Vyzkoušet také zakázané/plné místní úložiště.
7. Exporty otevřít v používaném SuperPresenter EXE na testovací kopii knihovny,
   přehrát všechny varianty/pořadí, uložit desktopovým editorem a ověřit ID.
   Běžná úprava musí zachovat ID, „Vytvořit kopii“ musí mít nové ID.

**Po ruční kontrole připomínáme commit; agent žádný nevytváří.**

## 10. Předání jednoduchého TXT (3. 11. 2026)

Použity pokyny `C:/Users/moski/Documents/AGENTS.md` (české shrnutí); další
AGENTS.md v projektu ani nadřazených kontrolovaných adresářích nenalezen.
Předchozí oddíly jsou historický kontext. Word/DOCX, hosting, desktopové zdroje,
knihovna písní ani závislosti se v této etapě nemění. Commit nebyl vytvořen.

### Rozhodnutí a soubory

- `web-song-editor/src/io/songTxt.ts`: samostatný parser, náhled, tvorba modelu
  a export. Lidské nadpisy Sloka/Refrén/Bridge, čísla, case a diakritika,
  volitelná dvojtečka, prázdné odkazy na dřívější definici. Vnitřní prázdné
  řádky nejsou oddělovačem částí. Odlišné texty stejného ID blokují import;
  explicitní řešení vytvoří nové volné číslo a ukáže výsledné reference.
- TXT v1 má dva technické řádky (verze a JSON s identitou/jazykem/pořadím/main).
  Hlavičku uživatel nemá měnit. Import bez ID vyžaduje výslovnou volbu nová
  píseň versus úprava otevřené; název nikdy nerozhoduje. Stejné ID se zachovává
  i při přejmenování. Není detekce revizí ani automatické slučování.
- `src/ui/main.ts`: tlačítko exportu s upozorněním, TXT file input, náhled
  všech textů, pořadí a problémů, výslovné řešení konfliktů a volba cíle.
  Náhled nemění koncept. Použití vyžaduje potvrzení náhrady a stávající ochranu
  neexportovaných změn včetně originálu kopie. Import je atomický.
- `src/io/files.ts`: společné striktní UTF-8 čtení s limitem 1 MiB a TXT MIME.
  Export používá BOM + CRLF pro Poznámkový blok. TXT export nemaže dirty stav.
- `docs/song-txt-format.md`: specifikace, escaping, zacházení s mezerami,
  limity, stručný návod a konkrétní ruční průchod až do používaného EXE.
  `web-song-editor/examples/ukazkova-pisen.txt`: ukázka s pevnou testovací
  identitou, třemi definicemi a pořadím v1 r1 v2 r1. README odkazuje na oba soubory.
- `tests/txt.test.ts`, `tests/browser/txt.spec.ts`, `tests/verify_txt_desktop.py`:
  automatické ověření parseru, exportu, UI a skutečného browser XML v desktop loaderu.

### Záměrně omezený přenos bez tiché ztráty

TXT přenáší jeden jazyk a jedno ploché pořadí. Zachovává jména jazyka a pořadí
a hodnotu main v hlavičce. Více jazyků, více pořadí, nested repetition,
pokročilé konstrukce, metadata, vlastní ID, nepoužité/prázdné části a texty,
které formát neumí přesně vyjádřit, export blokují s doporučením XML.
Není ztrátové potvrzení ani automatická projekce vybrané varianty.
Úprava aktuální identity přes TXT také vyžaduje reprezentovatelný současný
koncept, aby nepřišel o jeho další funkce. Import jiné identity je explicitní
otevření jiné písně s potvrzením náhrady. Pořadí karet definic po importu vychází
z prvního výskytu v TXT; upozornění exportu na to výslovně pamatuje.
Původní XML formátování a přesný zápis plochého guide nejsou součástí TXT smlouvy.

### Ověření a zbývající ruční kontrola

- TypeScript + produkční build: OK.
- Vitest: 18/18 OK (13 původních + 5 TXT), včetně současné korpusové sady.
  Po finální ochraně neelementového textu opět 5/5 cílených TXT testů OK.
- Česká diakritika, BOM, CRLF, interní prázdné řádky, escapované nadpisy,
  více prázdných opakování, neexistující reference, konflikty a explicitní
  varianty, zachování ID i přes XML a odmítnutí ztrátových exportů ověřeny.
- Chromium: nový TXT scénář OK; kompletní sada sériově 6/6 OK.
  První souběžný běh měl 5/6 OK a timeout staršího testu při page.goto;
  sériové opakování prošlo. Počáteční běh v sandboxu nedosáhl na testovací
  server; Vitest blokoval EPERM při rename. Testy dokončeny mimo sandbox.
- Skutečné XML stažené Chromiem po úpravě TXT načetl aktuální SongRepository
  a WidgetSource bez fallbacku/varování. Ověřeno v1 r1 v2 r1 a české texty.
  Výstupy zůstávají v ignorovaném test-output; původní XML se nezapisovala.
- Poznámkový blok ani distribuované SuperPresenter EXE nebyly automatizovány.
  Je nutné ručně provést export TXT → úpravu v Poznámkovém bloku → import
  s kontrolou stejného ID a tří definic → kontrolu v1 r1 v2 r1 → XML →
  přehrání v používaném EXE na testovací kopii knihovny. Přesné kroky obsahuje
  `docs/song-txt-format.md`, oddíl „Ruční průchod až do SuperPresenteru“.

**Po ruční kontrole vytvořte commit; agent ho nevytváří.**

## 11. Zjednodušení TXT podle uživatelské zpětné vazby (3. 11. 2026)

Toto je aktuální zadání a nahrazuje chování z oddílu 10: uživatel výslovně
odmítl technickou hlavičku i volbu „Vyberte cíl“ a požádal o výběr jednoho
jazyka k offline úpravě. Export nyní obsahuje jen první řádek s názvem,
nadpisy bez dvojteček a texty. UUID zůstává pouze v editoru/XML.

### Změny a rozhodnutí

- `src/io/songTxt.ts`: prostý TXT bez hlavičky a povinných dvojteček,
  prázdná šablona Název písně / Sloka 1 / Refrén 1 / Bridge 1. Parser přijímá
  sloka1, Sloka 1, SLOKA 1, varianty diakritiky, volitelnou dvojtečku i
  nečíslovanou Sloku (v1). Shodné texty stejného nadpisu sdílejí definici;
  odlišné vyžadují řešení, při němž se stejný alternativní text také neskladuje
  znovu. Starý formát s hlavičkou lze číst, ale jeho identita se nepřebírá.
- Export umožňuje vybrat jeden jazyk a jedno pořadí i z vícejazyčné písně
  s metadaty a více pořadími. UI výslovně vysvětluje omezený rozsah TXT
  a doporučuje XML zálohu. Skupiny, řádky, @, nepoužité/prázdné části
  vybraného jazyka a další nepřevoditelné údaje daného textu stále blokuje;
  nic tiše nezplošťuje. TXT není úplný roundtrip XML.
- `src/ui/main.ts`: odstraněno „Vyberte cíl“. Bez shody názvu vzniká nová
  píseň; jazyk nové písně je viditelně předvyplněný jako čeština a lze jej změnit.
  Při shodě názvu s otevřeným konceptem/původním konceptem kopie nabídne
  přepsání textů zvoleného jazyka nebo novou píseň s jiným názvem.
  Název spouští pouze nabídku, nikdy automatické přepsání. Nový název musí
  být odlišný od známých konceptů. Kontrola ignoruje case a okolní mezery.
  **Web nemá knihovnu a nevyhledává názvy všech XML na disku.**
- `updateLanguageFromTxt` pracuje na klonu: při přepsání textů zachová
  UUID, název, ostatní jazyky, atributy, metadata, vynechané části a všechna
  původní pořadí včetně main a umístění. Nové části přidá jen do vybraného
  jazyka (UI upozorní na chybějící protějšky). Změněné TXT pořadí přidá jako
  nové nevýchozí TXT/TXT 2; shodné s aktuálním plochým pořadím nic nepřidává.
  Původní pokročilé výrazy se nikdy nepřepisují. Změny textů mohou nově
  vyvolat diagnostiku jejich řádkových výběrů; to se nezamlčuje.
- Ochrana rozpracovaného konceptu i originálu kopie zůstává. Zrušení náhledu,
  přepsání či zadání nového názvu práci nemění. TXT download nemaže dirty stav.
- `examples/ukazkova-pisen.txt` upraven na prostý zápis;
  `examples/sablona-pisne.txt` nově obsahuje prázdnou šablonu (oba UTF-8 BOM/CRLF).
  `README.md` a `docs/song-txt-format.md` popisují nový postup i ruční test.
  `tests/txt.test.ts`, `tests/browser/txt.spec.ts`, `tests/verify_txt_desktop.py`
  ověřují novou podobu, název, šablonu, konflikty i zachování druhého jazyka.

### Ověření

- TypeScript a produkční build: OK.
- Vitest: 20/20 OK, včetně původní korpusové sady a 7 TXT testů.
- Chromium sériově: 6/6 OK. TXT scénář ověřuje download prázdné šablony,
  nový import bez volby cíle, výběr jazyka vícejazyčného exportu, absenci
  hlavičky/dvojteček, zrušení a potvrzení přepsání jednoho jazyka při shodě
  názvu, zachování UUID a ukrajinštiny, novou píseň s odlišným názvem/UUID,
  neexistující odkazy, konflikty a opakované alternativní texty.
- Skutečný XML download po TXT úpravě češtiny načetl SongRepository a
  WidgetSource bez fallbacku/varování; ověřeno v1 r1 v2 r1, český refrén
  a zachovaný ukrajinský text. GUI Poznámkového bloku ani používané EXE
  nebyly automatizovány. Výstupy jen v ignorovaném test-output.
- Sandbox opět blokoval rename dočasných souborů Vitestu (EPERM), úspěšné
  testy byly provedeny s povolením mimo sandbox. Žádné závislosti se neinstalovaly.

### Ruční průchod

Import ukázky jako nové písně → doplnění druhého jazyka → XML záloha → export
vybrané češtiny do TXT → úprava refrénu v Poznámkovém bloku bez změny názvu
→ import a náhled → shoda názvu a potvrzení přepsání češtiny → kontrola
v1 r1 v2 r1, stejného UUID a nedotčeného druhého jazyka → XML → testovací
knihovna používaného SuperPresenter EXE a přehrání obou jazyků. Dále změnit
TXT pořadí a ověřit nové nevýchozí TXT pořadí i zachování původního.
Podrobné kroky jsou v `docs/song-txt-format.md`.

Word/DOCX, hosting, migrace ani desktop se neimplementovaly. Knihovna písní
se nezapisovala. **Po ruční kontrole vytvořte commit; agent ho nevytváří.**

## 12. Word DOCX se stejným tokem jako TXT (3. 11. 2026)

Uživatel následně výslovně požádal i o Word. Starší odložení DOCX v předchozích
oddílech proto neplatí. Rozsah a ochrany vycházejí z aktuálního TXT v oddílu 11.
Přečten `C:/Users/moski/Documents/AGENTS.md`; další projektový AGENTS.md nenalezen.
Desktop, knihovna XML ani hosting se nemění; commit nebyl vytvořen.

### Implementace a soubory

- `web-song-editor/src/io/songDocx.ts`: OOXML export skutečného DOCX ZIP balíčku
  s běžnými odstavci, A4, černým písmem a Word Title stylem názvu. Název a nadpisy
  bez technické hlavičky a povinných dvojteček. Export vybraného jazyka a pořadí
  používá stejný převod textu jako TXT, bez automatické projekce složitých guide.
  Prázdná šablona obsahuje Název písně / Sloka 1 / Refrén 1 / Bridge 1.
- Import čte lokálně `word/document.xml` a content types. Textové úseky spojuje,
  odstavce i ruční zalomení převádí na řádky. Zachovává Unicode, mezery,
  tabulátory a prázdné řádky. Podporuje namespace WordprocessingML Transitional
  i Strict, prefixy nehrají roli. Nepotřebuje Word styly pro rozpoznání nadpisů.
- `src/ui/main.ts`: oba formáty sdílejí stejný kód náhledu, řešení konfliktů,
  shody názvu, nové písně a potvrzeného přepsání jazyka. Přidána tlačítka
  Stáhnout DOCX, Stáhnout prázdnou DOCX šablonu a vstup Importovat DOCX.
  Export nabízí jazyk a pořadí a vysvětluje rozsah dokumentu.
- `src/io/songTxt.ts`: společná aktualizace jazyka přijímá jméno formátu pro
  přidané pořadí. DOCX změna pořadí vytvoří nevýchozí DOCX/DOCX 2; původní
  pořadí, jejich umístění a main zůstanou. Při shodném pořadí nic nepřidává.
  ID, ostatní jazyky, atributy, vynechané části a metadata se zachovávají stejně
  jako při TXT aktualizaci. Výchozí import jiného názvu je nová píseň s novým ID.
- `src/io/files.ts`: binární download se správným DOCX MIME, čtení DOCX
  s vlastní kontrolou velikosti a přípony. TXT/XML/JSON downloady zůstávají.
- `package.json`, `pnpm-lock.yaml`: přímá závislost fflate 0.8.3 pro ZIP.
  Dokumentace ověřena v primárním zdroji https://github.com/101arrowz/fflate.
  Instalace mimo sandbox po EPERM, se systémovými CA Windows po prvním TLS
  odmítnutí; ověřování certifikátů nebylo vypnuto. Knihovna se bundluje lokálně,
  není CDN, server ani upload. Build po změně přibližně 57 kB JS / 22.5 kB gzip.
- `examples/ukazkova-pisen.docx`, `examples/sablona-pisne.docx`: ukázka a šablona;
  `docs/song-docx-format.md`, README a odkaz v TXT specifikaci: nový návod.
- `tests/docx.test.ts`, `tests/browser/docx.spec.ts`,
  `tests/verify_docx_word.ps1`, `tests/verify_docx_desktop.py`: převod, UI,
  skutečný Word i následné XML. `tests/fixtures/word-edited.docx` je ukázka
  skutečně upravená a uložená Wordem, po odstranění osobních metadat a rsid.

### Rozsah a limity

Přenášejí se texty a pořadí, ne fonty, barvy, Word styly, stránkování a cíle
odkazů. UI před použitím importu zobrazuje toto omezení. Záhlaví, zápatí,
komentáře a samostatné poznámky se nepřenášejí a vyvolají upozornění.
Tabulky, obrázky/textová pole, vložené objekty, pole, reference poznámek,
sledované změny a přímo číslované seznamy se odmítají s radou používat běžné
odstavce a nejprve přijmout/odmítnout revize. Čísla zděděná ze stylů nejsou
prostý text; definice automatického číslování vyvolají upozornění k náhledu.
Starší .doc, makra a heslem šifrované dokumenty nejsou podporovány.

ZIP do 5 MiB, nejvýše 256 položek, hlavní XML do 1 MiB, content types do 64 KiB,
nejvýše 30 000 XML elementů / 64 úrovní. Kontrola úplného ZIP zakončení,
poškozeného XML, DTD/entities a duplicitních položek. Průběžné rozbalování
v malých vstupních blocích kontroluje i skutečnou délku výstupu nezávisle na
ZIP deklaraci. Žádné položky se nezapisují na disk ani nevykonávají, externí
vztahy se nenačítají. Chyba importu nepoškodí otevřený koncept.

### Ověřeno

- TypeScript a produkční build OK. Vitest **27/27 OK** (20 předchozích + 7 DOCX).
  Po doplnění kontroly zakončení ZIP a upozornění na číslování znovu 7/7 DOCX OK.
- Chromium sériově **7/7 OK** včetně stávajícího TXT a editoru; finální DOCX
  scénář zopakován po vyčištění Word fixture, OK. Ověřen download šablony,
  skutečný Wordem uložený vstup, rozpoznání českých textů a prázdných bloků,
  výběr jazyka exportu, absence ID/hlavičky, náhled, zrušení a potvrzení
  přepsání češtiny při zachování ukrajinštiny a ID, přidání DOCX pořadí
  i odmítnutí dokumentu s tabulkou bez ztráty konceptu.
- Windows Microsoft Word skrytě otevřel oba vygenerované dokumenty bez
  opravného režimu, změnil refrén, nastavil tučné písmo a uložil DOCX. Tento
  reálný soubor prošel browser importem. Volitelný helper otevírá jen vlastní
  test-output soubory a Word zavírá; nepoužívá otevřené uživatelské dokumenty.
- Dovednost documents: pokus `render_docx.py` selhal, protože na Windows není
  LibreOffice/soffice.exe. Diagnostika potvrzena mimo sandbox. Pro QA byly
  oba DOCX převedeny instalovaným Wordem na PDF a baleným pdf2image na PNG;
  obě jednotlivé stránky vizuálně zkontrolovány, bez ořezů a chyb diakritiky.
  Interní PDF/PNG zůstávají jen v ignorovaném test-output, nejsou deliverable.
- Skutečné XML stažené Chromiem po DOCX aktualizaci načetly SongRepository
  a WidgetSource bez fallbacku či varování; ověřeno v1 r1 v2 r1, české texty
  a zachovaný ukrajinský text. Prezentační čištění prázdných řádků odpovídá desktopu.
  Distribuované SuperPresenter EXE zatím tímto průchodem ručně ověřeno není.
- EPERM rename dočasných souborů Vitestu v sandboxu vyžadoval povolené testy
  mimo sandbox. Žádné změny původní knihovny, žádný commit.

### Ruční průchod až do používaného EXE

Stáhnout DOCX vybraného jazyka → ve Wordu upravit refrén a uložit .docx se
stejným názvem → Importovat DOCX → zkontrolovat tři definice a v1 r1 v2 r1
→ při shodě názvu potvrdit přepsání správného jazyka → ověřit ID a druhý jazyk
→ stáhnout XML → vložit do testovací kopie knihovny používaného SuperPresenteru
→ promítnout oba jazyky a celé pořadí → po desktopovém uložení ověřit song-id.
Změněné pořadí dokumentu kontrolovat jako nové nevýchozí DOCX. Podrobný scénář
včetně šablony a odmítaných případů je v `docs/song-docx-format.md`.

**Po ruční kontrole vytvořte commit; agent ho nevytváří.**


## 13. Etapa 5 — layout a pohodlné ovládání (3. 11. 2026)

Aktuální pořadí etap je **5. Layout a pohodlné ovládání → 6. Finální vizuální
vzhled → 7. Nasazení na GitHub Pages a uživatelské ověření**. Starší odkazy
na hosting ve čtvrté etapě jsou historické. Přečten nadřazený
`C:/Users/moski/Documents/AGENTS.md`; projektové AGENTS.md nenalezeny.
Databáze, přihlášení, synchronizace ani nasazení nebyly implementovány.

### Pracovní postupy a rozhodnutí

- Nová / otevřená píseň: hlavní lišta Nová píseň, popsaný vstup Otevřít XML,
  Stáhnout XML a Vytvořit kopii. Na notebooku zůstává lišta při posouvání
  dostupná, na mobilu je v běžném toku, aby nezakrývala pracovní plochu.
  Název je samostatné výrazné pole před pracovními oblastmi.
- Psaní: části mají lidské názvy Sloka 1 / Refrén 1 / Bridge 1, širší textová
  pole s výškou alespoň 13 rem a možností zvětšení. Legacy/vlastní ID se
  nepřejmenovávají. Správa jazyků je sbalená, běžný výběr jazyka zůstává venku.
  Přidání části rovnou zaměří její text. Pořadí definic a pořadí přehrávání
  jsou samostatné oblasti s vlastními tlačítky přesunu.
- Pořadí: očíslované výskyty, lidské názvy při zařazení a tlačítko Upravit text,
  které přesune fokus do sdílené definice. Vysvětlení rozlišuje odstranění
  výskytu od textové části. Přesun tlačítky funguje bez přetahování; fokus
  následuje přesunutý výskyt. Opakování bloku a počet jsou dostupné přímo,
  seskupení, připojování a volba řádků jsou v pokročilých volbách. Aktivní
  číselné rozsahy zůstávají viditelné, aby nebyla použitá omezení skrytá.
- Náhled: při šířce od 1100 px vedle textů a pořadí, zůstává dostupný při
  posouvání. Mezi 761–1099 px dvě kolony, náhled pod pořadím. Do 760 px
  jediný sloupec; odkazy Texty částí / Pořadí / Náhled přesunou i fokus.
  Dlouhý náhled má na desktopu vlastní posouvání. Nadále nejde o emulaci
  stránkování nebo grafiky projektoru.
- XML/TXT/DOCX: rozšířené souborové akce a šablony jsou pod jasnou nabídkou
  Import, TXT / Word a šablony. Náhled importu, konflikty, volba jazyka a
  bezpečné potvrzené přepsání zůstávají zachovány. Úspěšné otevření a předání
  exportu prohlížeči mají viditelnou stavovou zprávu; neprohlašuje se dokončený
  zápis na disk. TXT/DOCX nadále nemažou stav neexportovaných změn.
- Rozpracování a obnova jsou viditelné mimo nápovědu, podrobnosti místního
  úložiště a identity jsou sbalené. Opraven funkční problém: běžný automatický
  zápis při renderu ihned přepisoval zprávu o obnovené práci. Nyní informace
  o obnově zůstává během daného otevření stránky zachována.
- Klávesnice: nativní formuláře a details, viditelný fokus, cíle alespoň 44 px,
  popsané vstupy souborů, zachování fokusu formulářových ovladačů a tlačítek
  po překreslení. Hlášení používají role=status; průběžný náhled není živou
  oblastí, aby při psaní nepřerušoval čtení. Potvrzení ztráty práce, mazání
  textů a náhrady importu zůstávají; běžné psaní/přesuny potvrzení nemají.

### Změněné soubory a kompatibilita

`web-song-editor/src/ui/main.ts`, `src/ui/style.css`: rozložení, ovládání,
popisky, fokus a stavové zprávy. Existující browser testy `editor.spec.ts`,
`txt.spec.ts`, `docx.spec.ts` přizpůsobeny lidským názvům a rozbalení nabídek;
nový `tests/browser/layout.spec.ts` kontroluje malé okno a pracovní průchod.
Tento dokument aktualizuje plán a předání. Model, parsery, XML/TXT/DOCX
serializace, UUID pravidla, desktop, knihovna písní i závislosti jsou beze změn.
Žádný commit nebyl vytvořen.

### Provedené kontroly a jejich hranice

- TypeScript `tsc --noEmit` a produkční Vite build: OK.
- Vitest: **27/27 OK**, včetně existující korpusové kompatibility a TXT/DOCX.
- Chromium / Playwright sériově: **9/9 OK** v závěrečném běhu. Sada pokrývá novou
  píseň, XML otevření/export, sdílený refrén, identitu/kopii, více jazyků,
  skupiny, pojmenovaná pořadí, rušení mazání, neplatné importy, obnovu i
  TXT/DOCX import/export. Nové průchody mají viewport **1280 × 720 a 390 × 844**,
  přidání části s fokusem, zařazení přes Enter, přesun tlačítkem, skok do textu,
  sdílenou úpravu refrénu, fokus náhledu, absenci vodorovného přetékání,
  obnovu a download XML.
- Skutečné snímky plné stránky i viewportu jsou v ignorovaném `test-output/`.
  Vizuálně zkontrolován notebookový třísloupcový layout a mobilní jediný
  sloupec, bez vodorovných ořezů. Plnostránkový screenshot může zachytit
  sticky lištu v poloze odpovídající aktuálnímu scrollu; viewport snímek
  ukazuje její skutečnou polohu po návratu nahoru.
- Sandbox blokoval Vitest rename (EPERM) a místní browser server; úspěšné
  běhy proběhly s povolením mimo sandbox. Nic se neinstalovalo.
- Neprovedeno: uživatelské hodnocení pohodlí, úplný průchod pouze klávesnicí,
  čtečka obrazovky, dotyková klávesnice skutečného mobilu, Firefox/Safari,
  200% zoom, dlouhá reálná píseň se všemi pokročilými variantami a používané
  distribuované EXE. Automatické malé viewporty nenahrazují skutečný mobil.

### Konkrétní ruční scénáře pohodlí

1. Nová píseň: pojmenovat „Zkouška pohodlí“, napsat čtyři řádky Sloky 1,
   přidat Refrén, Sloku 2 a Bridge. Po přidání má kurzor rovnou psát do nové
   části. Posoudit šířku, výšku a čitelnost při delším textu.
2. Sestavit Sloka 1 → Refrén 1 → Sloka 2 → Refrén 1 → Bridge 1.
   Výchozí Sloka 1 už v pořadí je. Tlačítky přesunout Bridge před poslední
   refrén, odebrat jen jeho výskyt a znovu ho zařadit. Text Bridge musí zůstat.
   Vyzkoušet Opakovat tento blok a změnit počet opakování.
3. U druhého refrénu zvolit Upravit text a změnit jeden řádek. Oba refrény
   v náhledu musí ukazovat tutéž změnu a nesmí vzniknout druhá definice.
4. Přejít odkazem Náhled, zkontrolovat celý sled i opakování a vrátit se
   k textům. Při dlouhé písni posoudit pohodlí posouvání náhledu.
5. Stáhnout XML, otevřít právě stažený soubor, upravit název a text. ID musí
   zůstat stejné. Zkusit novou píseň a zrušit varování; práce musí zůstat.
   Obnovit stránku a ověřit hlášení obnovy i texty.
6. Rozbalit Import, TXT / Word a šablony, stáhnout TXT jednoho jazyka,
   upravit refrén v Poznámkovém bloku a importovat. Zkontrolovat náhled,
   nejprve zrušit, potom potvrdit přepsání správného jazyka. Zkontrolovat
   pořadí a stáhnout XML. Původní soubor musí uživatel nahradit ručně.
7. Zopakovat v okně 1280 × 720, potom v šířce přibližně 390 px a na skutečném
   telefonu. Ověřit přístup ke všem akcím, žádný vodorovný posuv, použitelnost
   se zobrazenou softwarovou klávesnicí a čitelnost dlouhých názvů/textů.
8. Bez myši použít Tab / Shift+Tab, Enter / mezerník, odkazy oblastí,
   rozbalení nabídek, psaní, přidání části, přesun výskytu a export. Fokus
   musí být viditelný a po přesunu zůstat u příslušného výskytu. Zopakovat
   při 200% zoomu a zkontrolovat, že lišta nezakrývá zaměřený ovladač.

### Předání do etapy 6

Další etapa řeší konečnou paletu a grafický styl. Zachovat význam oblastí,
čitelnost, prostor textu, viditelný fokus a popisky, sdílené části a ochrany
ztráty práce. Současná šedá/bílá a modrý fokus/odkazy slouží jen orientaci;
nejsou finálním designem. Nejsou přidány stíny, dekorace ani animace.
Delší písně a vnořená pořadí stále mohou vyžadovat více posouvání; prioritu
dalším úpravám dát podle ručních scénářů, nikoli měnit formáty nebo identity.
Nasazení až v etapě 7. **Po ruční kontrole připomenout commit; agent jej nevytváří.**

## 14. Upřesnění horního menu — PC má přednost (3. 11. 2026)

Toto upřesnění nahrazuje příslušné rozhodnutí o horní liště z oddílu 13.
Primárně se nyní ladí PC, další přizpůsobení mobilu až následně.

- Hlavička je **Baptisté Šumperk**. Logo BJB Šumperk se doplní později,
  až bude dodáno; nyní se nevymýšlí náhradní logo.
- Menu: **Nová píseň → Kopie stávající písně → Otevřít → Importovat →
  Stáhnout šablonu**. Otevřít nyní vyvolává výběr XML z počítače;
  výběr počítač/databáze patří až k budoucí databázi, není implementován.
- Importovat používá jediný souborový dialog s TXT i DOCX. Typ se určí
  z přípony bez další volby uživatele; náhled zůstává před použitím importu.
  Jiná přípona se odmítne bez změny práce.
- Stáhnout šablonu rozbalí volbu **TXT / Word**. Po stažení se nabídka zavře.
- Průběžný řádek změn s UUID ani hlášení „Otevřená píseň“ se nevykreslují.
  Identita v modelu/XML a ochrany neexportovaných změn zůstávají funkční.
  Obnova a informace o místním konceptu jsou v patičce. Zprávy o exportu
  se zobrazují jen po příslušné akci.
- Stažení XML je u náhledu. Další možnosti stažení TXT/DOCX a podrobnosti
  místního uložení jsou dole, aby neprodlužovaly horní pracovní prostor.
- Opraveno zachování rozbalených nabídek při překreslení: místo pozice v poli
  se používá jméno nabídky a cesta výskytu. Přidané části dříve mohly zavřít
  jinou nabídku, zejména možnosti exportu.

Změněny `src/ui/main.ts`, `src/ui/style.css`, browser testy a tento dokument.
Testy identity nyní kontrolují interní datový atribut místo odstraněného
stavového řádku. Formáty ani pravidla identity se nemění, žádná databáze,
přihlášení, synchronizace, logo ani commit se nepřidávají.

Ruční kontrola PC: postupně kliknout Nová píseň, Kopie stávající písně,
Otevřít (XML), Importovat nejprve TXT a pak DOCX stejným tlačítkem, stáhnout
obě šablony z rozbalovací nabídky. Ověřit zrušení souborového dialogu i náhledu,
obnovu stránky a informaci o obnově až dole. Připomenout commit po kontrole.

Ověření tohoto upřesnění: TypeScript a produkční build OK; všech sedm
stávajících Chromium scénářů XML/TXT/DOCX prošlo. Dva upravené layoutové
scénáře po opravě testovacího API také prošly (2/2). Kontrolují pořadí menu,
společný souborový dialog s oběma příponami, odstraněný stavový řádek a obnovu
v patičce. Vizuálně zkontrolován skutečný PC screenshot 1280 × 720.
Snímky zůstávají v ignorovaném test-output. Modelové testy se znovu nespouštěly,
protože se model a převody neměnily; jejich předchozí výsledek je v oddílu 13.
Úplné ruční posouzení pohodlí uživatelem zbývá. Commit nebyl vytvořen.

## 15. Zjednodušení menu a prázdný název (3. 11. 2026)

Aktuální zadání nahrazuje předchozí nabídku kopie a přeskoků mezi oblastmi.

- Akce Kopie stávající písně byla z editoru odstraněna. Běžné stažení nadále
  ponechává rozepsanou píseň otevřenou a nemění její identitu. Existující XML
  song-id se nemění; ukládání souboru dál používá název. Modelovou metodu kopie
  tato úprava nemaže a starší místní koncept s originálem lze stále obnovit,
  aby aktualizace nezahodila dřívější práci. Nové kopie v UI nevznikají.
- Nová píseň má skutečně prázdný název a jen placeholder „Zadejte název písně“.
  Uživatel nemusí mazat předvyplněný text. Importované názvy se nemění.
- Stáhnout šablonu otevírá plovoucí panel TXT / Word nad tlačítkem bez změny
  výšky lišty či posunu obsahu. Escape, kliknutí mimo a výběr formátu nabídku
  zavřou. Pokud je při posunuté sticky liště nad tlačítkem málo místa, panel
  se otevře pod ním, aby nezmizel mimo okno; stále nepřesouvá obsah.
- Odkazy Texty částí / Pořadí / Náhled jsou odstraněny. Samotné pracovní
  oblasti zůstávají vedle sebe jako dříve.

Změněny `src/ui/main.ts`, `src/ui/style.css`, výchozí název v
`src/domain/song.ts`, navazující browser testy a tento dokument. Žádná změna
serializace, pravidel identity, databáze ani přihlášení. Žádný commit.

Ruční kontrola PC: Nová píseň → rovnou napsat název bez mazání; zkontrolovat,
že v menu není kopie ani odkazy oblastí; otevřít šablony a ověřit plovoucí
panel nad tlačítkem bez posunu názvu a textů; zkusit Escape i kliknutí mimo;
stáhnout XML a pokračovat v úpravách téže písně. Zbývá uživatelské posouzení
pohodlí; mobil se dál prioritně neladí.

Ověřeno po úpravě: TypeScript a produkční build OK, Vitest 27/27,
Chromium 9/9. Layoutové testy ověřují prázdný název, menu bez kopie,
chybějící navigaci oblastí, polohu panelu nad tlačítkem a nezměněné souřadnice
pole názvu po otevření nabídky. Skutečný snímek `templates-1280.png` byl
vizuálně zkontrolován. Snímky zůstávají v ignorovaném test-output.

## 16. Dvousloupcové sestavení pořadí a výběr řádků (3. 11. 2026)

Toto zadání nahrazuje předchozí podobu pořadí a směr otevření šablon.
Stále má přednost pohodlné použití na PC.

### Ovládání

- Šablony se otevírají **pod tlačítkem**, jako plovoucí panel nad obsahem
  stránky. Obsah ani lišta se neposouvají. Escape a kliknutí mimo zůstávají.
- Pořadí má vlevo seznam dostupných částí vybraného jazyka, vpravo sestavený
  sled. Kliknutí na část ji přidá na konec; stejnou část lze zařadit vícekrát.
  Fokus se po přidání vrací na stejné tlačítko, takže Enter přidává opakovaně.
- Vpravo jsou kompaktní očíslované výskyty. Přesun se provádí přetažením,
  s vyznačením vložení před/za cílový řádek. Klávesnice: zaměřit výskyt a
  Alt + šipka nahoru/dolů; fokus následuje přesunutý výskyt. Křížek odebere
  jen výskyt. Kliknutí na název výskytu zaměří sdílený text k úpravě.
- Pod seznamem dostupných částí je **Řádky**. Modální dialog nabídne výběr
  části a její skutečný prezentační text. Kliknutím na text řádku/checkbox
  se označuje výběr. Prázdné řádky se při prezentaci vynechávají a nejsou
  očíslovány jako vybratelné. Není třeba znát čísla nebo syntaxi XML.
- Lze označit souvislý i nesouvislý výběr. Sousední řádky vytvoří jeden
  rozsah, oddělené úseky více po sobě jdoucích výskytů. U řádkového výskytu
  v pořadí tlačítko Řádky otevře úpravu se současným výběrem. Zrušení/Escape
  neaplikují změny. Prázdný výběr ani část bez textu nejdou přidat.
- Skupiny se v běžném seznamu přesouvají jako celek; jejich hranice se
  nezplošťují. Vnoření, počty opakování, seskupení, připojení k předchozímu
  a původní číselné rozsahy zůstávají v **Pokročilé úpravě skupin a opakování**.
  Správa pojmenovaných/výchozích pořadí je v samostatné sbalené nabídce.
  Vadné/nepochopené importované výrazy zůstávají chráněné jako dříve.

### Prázdný koncept a kompatibilita

Nová píseň v UI začíná s prázdným pořadím, aby první kliknutí na Sloku 1
nevytvořilo její nečekanou duplicitu. Odstranit lze i poslední výskyt a pořadí
znovu sestavit. Prázdné pořadí se místně obnoví; náhled vyzve k přidání části.
Export prázdného pořadí stále vyžaduje dosavadní potvrzení diagnostiky XML,
protože prázdný výraz není přehratelné pořadí. Parser ani XML gramatika se
nerozšiřují. Texty lze před sestavením pořadí běžně odstraňovat — opravena
blokace mazání nepoužité části pouhou přítomností prázdného pořadí.
Neprázdné vadné výrazy mazání nadále blokují a poslední odkazovaná část se
nesmí automaticky smazat z platného pořadí.

Výběr řádků ověřuje stávající model také proti ostatním jazykům a limitům.
Neplatnou změnu odmítne bez změny guide; dialog chybu vysvětlí a zůstane
otevřený. Jazyky s odlišným počtem řádků vyžadují uživatelskou opravu textu
nebo výběru. Song-id, atributy, metadata, formáty TXT/DOCX i XML zůstávají.

### Soubory, ověření a omezení

Nový `web-song-editor/src/ui/orderBuilder.ts`: kompaktní sestavovač, DnD,
klávesnice a modální výběr řádků. `src/ui/main.ts` a `style.css`: integrace,
rozložení, sbalené pokročilé funkce a směr šablon. `src/domain/song.ts`:
mazání nepoužité části vedle prázdného pořadí. Browser testy upraveny na nové
ovládání; nový `tests/browser/order-builder.spec.ts` ověřuje skutečný drag,
klávesnici, zrušení dialogu, souvislé i oddělené řádky, Unicode, prázdné řádky,
XML export/reimport a odstranění celého sledu. Modelový test chrání opravu
mazání při prázdném pořadí i odmítnutí mazání při chybném neprázdném guide.

Skutečné snímky sestavovače a dialogu v `test-output/order-builder.png` a
`order-lines-dialog.png` vizuálně zkontrolovány. Nové browser scénáře prošly
v Chromium; skutečný DnD test používá přetažení myší, nikoli volání modelu.
Sada stále kontroluje viewporty 1280 × 720 a 390 × 844, ale mobilní dotykový
přesun nebyl implementován ani ověřen. Delší/hlubší skupiny se editují v
pokročilé části; nové kompaktní DnD nepřesouvá jednotlivé děti mezi skupinami.
Úplné ruční posouzení pohodlí, jiné prohlížeče a distribuované EXE zbývají.

### Ruční ověření PC

1. Vytvořit píseň, napsat Sloku 1, přidat Refrén 1, Sloku 2 a Bridge 1.
2. Vlevo kliknout Sloka 1 → Refrén 1 → Sloka 2 → Refrén 1 → Bridge 1.
   Vpravo má být přesně těchto pět výskytů. Opakovaný refrén sdílí text.
3. Přetáhnout Bridge před druhý refrén; potom první výskyt na konec.
   Ověřit indikátor vložení a náhled. Zkusit přesun i Alt + šipkami.
4. Řádky → Sloka 2 → označit dva řádky přímo v textu → nejprve Zrušit,
   znovu otevřít a potvrdit. Ověřit přidaný rozsah a obsah náhledu.
5. U rozsahu zvolit Řádky a změnit výběr na dva oddělené úseky. Ověřit jejich
   pořadí v náhledu. Změnit sdílený refrén a ověřit oba jeho výskyty.
6. Stáhnout XML, znovu otevřít a ověřit řádky, pořadí a stejnou identitu.
   Nakonec otevřít šablony: panel pod tlačítkem nesmí posunout editor.

Databáze, přihlášení, synchronizace ani hosting se nepřidávají. Po ruční
kontrole připomenout commit; agent jej nevytváří.

Závěrečné kontroly etapy 16: TypeScript a produkční build OK; Chromium
**10/10 OK**, Vitest **28/28 OK** včetně korpusové kompatibility. Testy
proběhly s povolením mimo sandbox kvůli dříve ověřeným omezením serveru
a dočasných souborů. Žádná instalace závislostí, žádný commit.

## 17. Hromadné označování řádků myší a stabilita přesunu (3. 11. 2026)

- V dialogu Řádky lze podržet levé tlačítko nad textem nebo checkboxem
  a táhnout přes celý úsek. Začátek na neoznačeném řádku úsek přidává,
  začátek na označeném úsek odebírá. Tažení funguje oběma směry a při návratu
  kurzoru zkracuje rozsah vůči původnímu výběru. Dříve vybrané vzdálené úseky
  zůstávají zachovány. Jednotlivé klikání, mezerník i zrušení dialogu zůstávají.
- Použity pointer události se zachycením ukazatele, aby uvolnění myši mimo
  konkrétní řádek nezanechalo aktivní gesto. Pro dotyk zůstává nativní klikání
  a posouvání; dotykové hromadné označování se zatím nezavádí.
- U přesouvání pořadí značka vložení již nemění výšku a rozměry řádku
  (místo silnějšího borderu používá vnitřní značku). Neaktualizuje se znovu,
  pokud zůstává na stejném místě. Sjednocen kurzor uchopení, nastaven move
  dropEffect a nativní tooltip přesunut do aria-description.
- Uživatelův přesný jev blikajícího/mizejícího systémového kurzoru se nepodařilo
  samostatně reprodukovat. Změny odstraňují možné příčiny v hitboxech a
  přepínání stavů, ale úplné odstranění tohoto projevu musí potvrdit uživatel
  ve svém prohlížeči; automatický test nezachytí vykreslení systémového kurzoru.

Změněny `src/ui/orderBuilder.ts`, `src/ui/style.css`,
`tests/browser/order-builder.spec.ts` a tento dokument. Formáty, metadata,
identity, parser i pravidla výběru řádků se nemění.
TypeScript a produkční build OK; Chromium **11/11 OK**. Nový test provádí
skutečné tažení myši přes čtyři řádky, opačným tažením ruší výběr, ověřuje
kliknutí na text, checkbox, mezerník a zrušení přes Escape. Původní drag pořadí
s XML roundtripem i TXT/DOCX průchody stále procházejí. Modelová sada se znovu
nespouštěla, protože se model neměnil. Mobilní gesto a jiné prohlížeče zbývají.

Ruční kontrola PC: po načtení stránky zkusit najet a přetáhnout výskyt bez
čekání; ověřit klidný kurzor i značku vložení. Řádky → táhnout přes více řádků
shora dolů, potom zdola nahoru; zkusit odebrání úseku začátkem na označeném
řádku a následné jednotlivé kliknutí. Potvrdit a zkontrolovat náhled.
Commit nebyl vytvořen; po kontrole jej připomenout.

## 18. Opakované přidávání vybraných řádků (3. 11. 2026)

Pod tlačítkem Řádky je nově seznam **Vybrané řádky**, například
„Sloka 1 · řádky 2–3“. Každý potvrzený výběr se zobrazí jednou; kliknutím
se jeho řádky přidají na konec pořadí. Fokus zůstane na tlačítku, takže lze
opakovat i Enterem. Nesouvislý výběr z jednoho dialogu má společné tlačítko,
které znovu vloží všechny jeho úseky ve stejném pořadí.

Výběry jsou reference na současné texty, nikoli kopie jejich obsahu. Zůstávají
v nabídce i po odebrání všech jejich výskytů. Ukládají se spolu s místním
konceptem a obnoví se při reloadu (načtení kontroluje tvar a rozsahy dat).
Otevření jiné písně seznam obnoví z jejích řádkových rozsahů. XML/TXT/DOCX
nedostávají nová metadata ani nový formát; XML neukládá historii uživatelských
výběrů. Importovaný rozsah se také nabídne jako opakovatelná položka.
Pokud výběr přesahuje aktuální text jazyka, tlačítko je neaktivní s vysvětlením.

Změněny `src/ui/orderBuilder.ts`, `src/ui/main.ts`, `src/ui/style.css`,
`tests/browser/order-builder.spec.ts` a tento dokument. Přidání je nadále
validováno modelem, nepřiděluje novou identitu a neupravuje definici části.
Při odmítnutém přidání se neuloží nový výběr. Databáze ani synchronizace nejsou.

Ověřeno: TypeScript a produkční build OK; Chromium **12/12 OK**. Nový scénář
vytvoří nesouvislý výběr 1, 3, znovu ho přidá kliknutím i Enterem, ověří jednu
položku v nabídce, obnovu konceptu, odebrání všech výskytů a opětovné přidání,
i sdílené aktualizace textu v náhledu. Vizuálně zkontrolován skutečný screenshot
`test-output/reusable-lines.png`. Modelové testy znovu neběžely, model se neměnil.

Ruční kontrola: vybrat několik řádků, potvrdit, pod Řádky dvakrát kliknout na
vzniklé tlačítko. V pořadí a náhledu musí být tři průchody stejného výběru.
Obnovit stránku a zkusit tlačítko znovu. Zbývá uživatelské posouzení pohodlí.
Commit nebyl vytvořen; po ruční kontrole jej připomenout.

## 19. Jediné pole Název opakování a zápis podle jména (3. 11. 2026)

Toto zadání nahrazuje nabídky Pokročilá úprava skupin a opakování a Správa
pořadí. Obě jsou odstraněny. Nad sestavovačem je pouze **Název opakování**,
bez seznamu existujících jmen a bez přepínání pořadí. Prázdné pole má pouze
placeholder `default`; při zápisu XML se použije název `default`. Vyplněný
název se po oříznutí okolních mezer použije přesně, například `kapela 1`.
Jména se rozlišují stejně jako v XML, včetně velikosti písmen.

### Sémantika uložení

- Pole určuje cíl zápisu sestaveného pořadí. Při jeho psaní se nepřepíná ani
  nenačítá jiné pořadí. Běžný uživatel upraví sled a zadá své zavedené jméno.
- Při stažení XML se existující opakování stejného jména **nahradí** aktuálním
  sledem, nikoli přidá jako `kapela 1 2` nebo další stejnojmenný uzel.
  Zachová se umístění i ostatní atributy cílového uzlu.
- Nové jméno vytvoří nové opakování; ostatní pojmenovaná pořadí zůstanou.
  Nově zvolený cíl se stane výchozím (`main=1`), aby se po otevření XML
  načetlo právě uložené pořadí. Pouhá úprava již vybraného cíle jeho původní
  označení main nepřepisuje. Čistý prázdný počáteční `default` se při prvním
  uložení pod jiným jménem neponechává jako neplatná prázdná varianta.
- Rozpracovaný sled je oddělený od uložených XML pořadí. Změna názvu tak
  nezničí původní verzi a zrušený export ji nenahradí. Název i sled se obnovují
  s místním konceptem. Po XML downloadu se pracovní stav překreslí proti
  právě zapsanému modelu; opraveno pokračování v úpravách po stažení, které
  jinak mohlo zapisovat do již odpojeného starého pracovního objektu.
- TXT/DOCX export nabízí jazyk, ale již ne výběr pořadí; použije aktuálně
  sestavený sled. Omezení jejich formátu a doporučení úplné XML zálohy trvá.
- Import s více opakováními automaticky otevře dosavadní výchozí výběr
  (první main, jinak default, jinak první). Ostatní uzly se zachovají bez UI
  přepínače. U duplicitního cílového jména, které není právě načteným zdrojem,
  se odmítne víceznačné přepsání s doporučením jiného názvu; neodstraňují se
  tiše žádné staré uzly. Nezměněný právě načtený duplicitní zdroj lze zachovat.

Importované skupiny/vnoření/počty zůstávají v modelu i exportu a přesouvají
se jako celek; ovladače pro změnu jejich vnitřního obsahu už nejsou v UI.
Vadné guide stále zobrazují diagnostiku a explicitní akci sestavení náhrady.
Metadata, jazyky a song-id se nemění, žádná databáze nebo synchronizace není.
Stažení XML nadále nenahrazuje původní soubor na disku automaticky.

### Soubory a provedené kontroly

- `src/ui/main.ts`: jediné pole, pracovní koncept pořadí a jeho obnova,
  aplikace názvu při exportu, aktuální pořadí pro TXT/DOCX, odstranění nabídek.
- Nový `src/ui/namedOrder.ts`: transakční zápis klonovaného modelu podle názvu,
  zachování ostatních pořadí/metadat a ochrana víceznačných cílů.
- `src/ui/orderBuilder.ts`: opraven popis importované skupiny po odebrání
  pokročilé nabídky. Browser testy editoru/DOCX přizpůsobeny novému ovládání.
- Nové `tests/browser/named-order.spec.ts` a `tests/named-order.test.ts`:
  default, nové jméno, opakované přepsání bez duplicit, přepsání jiného
  existujícího cíle, obnova názvu/rozpracovaného sledu, XML reimport,
  nested cílové uzly, atributy, metadata a neměnnost vstupního modelu.
- TypeScript + produkční build: OK. Vitest **29/29 OK**, Chromium **13/13 OK**.
  Skutečný screenshot `test-output/named-order.png` vizuálně zkontrolován.
  Testy proběhly mimo sandbox s povolením kvůli známým omezením serveru a
  dočasných souborů. Žádné nové závislosti, žádný commit.

### Ruční kontrola

Vytvořit pořadí a nechat název prázdný → XML má `default`. Přidat refrén,
vyplnit `kapela 1` a stáhnout XML → přidat další refrén a znovu stáhnout se
stejným názvem → v XML má být právě jedno `kapela 1` s aktualizovaným sledem.
Otevřít stažený soubor a ověřit název i náhled. Zkusit obnovu stránky před
stažením; rozepsané jméno i sestavený sled musí zůstat. Jiné prohlížeče a
používané distribuované EXE zbývají ručně. Po kontrole připomenout commit.

## 20. Rozbalovací náhled dole v bloku pořadí (3. 11. 2026)

Trvale zobrazený pravý panel náhledu je odstraněn. Pracovní plocha má na PC
jen dva sloupce: texty a ovládání pořadí, oba s větší dostupnou šířkou.
Úplně dole uvnitř bloku Pořadí přehrávání je sbalená část **Náhled výsledného
pořadí**. Kliknutí, Enter nebo mezerník zobrazí dosavadní obsah náhledu přímo
pod názvem; stejným ovládáním se opět schová. Po načtení stránky je zavřená,
při běžném překreslení editoru se stav rozbalení zachová. Náhled nadále reaguje
na texty a sestavený sled. Tlačítko Stáhnout XML je nad rozbalovacím náhledem,
aby bylo dostupné i při jeho zavření.

Změněny `src/ui/main.ts`, `src/ui/style.css`, stávající browser scénáře
`tests/browser/layout.spec.ts` a tento dokument. Bez změny modelu, formátů,
identity, databáze nebo synchronizace.

Ověřeno: TypeScript a produkční build OK; Chromium **13/13 OK** včetně
výchozího skrytí náhledu, jeho umístění jako poslední části bloku pořadí,
dvousloupcové pracovní plochy a otevření/zavření klávesnicí. Skutečné snímky
sbaleného i rozbaleného layoutu při šířce 1280 px vizuálně zkontrolovány;
jsou v ignorovaném test-output. Modelové testy se neopakovaly, model se neměnil.
Ruční pohodlí uživatelem zbývá: rozbalit dole náhled, ověřit celý sled,
sbalit jej a pokračovat v úpravách. Commit nebyl vytvořen.

## 21. Jednoduché karty textových částí (3. 11. 2026)

Z textových karet odstraněna tlačítka Část nahoru / Část dolů. Pořadí
přehrávání se ovládá výhradně ve vlastním sestavovači. Místo tlačítka Odebrat
část je vpravo nahoře v hlavičce každé karty křížek s přístupným popiskem
„Odebrat část: Sloka 1“ apod. Zachovány kontroly a potvrzení skutečného
odstranění textu ze všech jazyků i dopadů na reference v pořadích.

Nové části se vytvářejí pouze tlačítky **Sloka / Refrén / Bridge**, bez
předpony Přidat:. Nabídka vytvoření vlastního bloku je odstraněna. Existující
legacy či vlastní ID v importovaném XML se nepřejmenovávají ani nemažou;
změna pouze omezuje vytváření z UI. Model a kompatibilita formátů se nemění.

Změněny `src/ui/main.ts`, `src/ui/style.css`, popisky v navazujících browser
testech a tento dokument. TypeScript + produkční build OK; Chromium
**13/13 OK**, včetně zrušení i potvrzení mazání křížkem, ochrany uzamčeného
guide a zachování ostatních jazyků/pořadí. Skutečný PC screenshot vizuálně
zkontrolován. Modelová sada se neopakovala, model se neměnil.

Ruční kontrola: přidat Sloku, Refrén a Bridge; zkusit křížek vpravo nahoře,
nejprve zrušit, poté potvrdit a zkontrolovat sestavené pořadí. Commit nebyl
vytvořen; po kontrole jej připomenout.

## 22. Stáhnout jinak v horním menu (3. 11. 2026)

Vedle Stáhnout šablonu je nově stejné rozbalovací ovládání **Stáhnout jinak**
s volbami **TXT / DOCX**. Panel se zobrazuje pod tlačítkem přes obsah a
neposouvá pracovní plochu. Výběr formátu zavře nabídku a otevře modální
exportní dialog s dosavadním výběrem jazyka, vysvětlením omezení formátu
a potvrzením stažení. Použije se právě sestavené pořadí. Zrušení/Escape
vrací fokus do menu; kliknutí mimo či Escape také zavírá plovoucí nabídky.
Původní nabídka Další možnosti stažení dole byla odstraněna. Stažení XML
v bloku pořadí zůstává dostupné beze změny.

Změněny `src/ui/main.ts`, `src/ui/style.css`, existující browser testy
TXT/DOCX/layoutu a tento dokument. Formáty, identita, ochrany exportu a stav
neexportovaných XML změn se nemění. Bez databáze, synchronizace či závislostí.
TypeScript a produkční build OK; Chromium **13/13 OK**, včetně obou exportů
přes nové menu. PC screenshot zkontrolován. Modelová sada se neopakovala,
protože se převody ani model neměnily. Ručně zbývá posoudit pohodlí nového
menu: Stáhnout jinak → TXT / DOCX → jazyk → stažení nebo zrušení. Commit
nebyl vytvořen; po kontrole jej připomenout.

## 23. Odstranění nápovědy a jazyky úplně dole (3. 11. 2026)

Rozbalovací blok **Uložení, obnova a identita písně** je včetně své nápovědy
odstraněn. Funkce místního ukládání/obnovy, ochrana nečitelných záloh,
varování před ztrátou práce a zachování song-id se nemění. Krátká informace
o obnově či chybě úložiště zůstává dole jako dosud.

**Jazyková varianta** i celá **Správa jazyků** jsou nyní v samostatném bloku
**Jazyky** úplně na konci stránky, pod pracovními oblastmi i stavovou zprávou.
Správa je stále rozbalovací a obsahuje původní přidání, přejmenování a
odebrání jazyka s kontrolami. Texty částí tak nahoře začínají přímo bez
jazykových ovladačů. Přepnutí dole stále mění texty, náhled i dostupné části.

Změněny `src/ui/main.ts`, `src/ui/style.css`, odkaz kontrolního browser testu
na zachované hlášení obnovy a tento dokument. TypeScript a produkční build
OK; Chromium **13/13 OK**, včetně více jazyků, rušení/mazání jazykové varianty,
TXT/DOCX importů a nečitelné zálohy. PC screenshot celého layoutu zkontrolován.
Modelové testy se neopakovaly, model ani formáty se neměnily. Žádná databáze,
synchronizace, změna identity nebo commit.

Ruční kontrola: sjet úplně dolů, přepnout variantu a ve Správě jazyků přidat
jazyk. Vrátit se k textům a ověřit správný jazyk i náhled. Uživatelské
posouzení pohodlí zbývá; po kontrole připomenout commit.

## 24. Jednotná nabídka Stáhnout (3. 11. 2026)

Stáhnout jinak je přejmenováno na **Stáhnout**. Rozbalovací menu vedle šablon
obsahuje **XML / TXT / DOCX**. XML spouští původní kompatibilní export včetně
zápisu opakování podle názvu a ochrany problematických guide; po akci se menu
zavře a fokus vrátí na Stáhnout. TXT/DOCX zachovávají dialog volby jazyka.
Samostatné Stáhnout XML uvnitř bloku pořadí je odstraněno.

Změněny `src/ui/main.ts`, navazující browser testy a tento dokument.
TypeScript a produkční build OK; Chromium **13/13 OK**, všechny XML exportní
scénáře nyní používají nové menu. PC screenshot zkontrolován. Model ani
formáty se nemění, modelové testy se neopakovaly. Ruční kontrola: v menu
Stáhnout vyzkoušet XML, TXT a DOCX. Commit nebyl vytvořen; po kontrole jej
připomenout.

## 25. GitHub Pages a předání kapelníkům (3. 11. 2026)

Toto je aktuální stav a nahrazuje historické zákazy hostingu i staré popisy
UI v oddílech výše. Funkce a dosavadní finální jednoduchý vzhled jsou zachovány;
layout byl ověřen na 1280 a 390 px. Bez databáze, přihlášení a synchronizace.

- Připraven `.github/workflows/web-song-editor-pages.yml`: Node 24,
  pnpm 11.25.0, frozen lockfile, produkční build, kontrola artefaktu,
  Chromium nad hotovým buildem a upload pouze `web-song-editor/dist`.
  Automatické spuštění pro změny webu pouze na `Sbor`, také ruční spuštění.
  Deploy je podmíněn větví `Sbor`; `test` slouží pouze pro vývoj.
- Vite `base: './'` zůstává; browserové scénáře nyní používají relativní
  navigaci a preview produkčního sestavení pod `/SuperPresenter/`.
  `EDITOR_URL` umožňuje tytéž scénáře proti veřejné adrese bez lokálního serveru.
- Nový `scripts/check-dist.mjs` odmítá nepovolené soubory a absolutní cesty.
  Zkontrolovaný artefakt má pouze index.html + jeden JS + jeden CSS,
  bez knihovny písní, testů, konceptů či jiných uživatelských dat.
- V patičce je výslovná informace: společná knihovna zatím není zavedena,
  změny se automaticky nepředávají do SuperPresenteru, přenos XML je ruční.
  Doplněno upozornění, že lokální koncept nenahrazuje zálohu XML.
- Krátký návod nasazení, všech šest kapelnických scénářů a šablona zpětné
  vazby: `docs/web-song-editor-deployment.md`.

### Adresa a skutečný stav nasazení

Cílová adresa: **https://moskitogrill.github.io/SuperPresenter/**.
Přímá HTTP kontrola 3. 11. 2026 vrátila **404 Not Found**. Web tedy není
ověřen jako publikovaný; funkční veřejná adresa zatím není k dispozici.
GitHub CLI ani GitHub konektor pro nasazení nejsou dostupné. Žádný commit,
push ani nasazení nebyly provedeny. Uživatel musí commitnout/pushnout změny,
v Settings → Pages zvolit GitHub Actions a ověřit úspěch workflow a URL.
Podrobný postup v předávacím dokumentu. Databáze zůstává budoucí samostatná etapa.

### Kontroly a omezení

Produkční TypeScript/Vite build OK. Vitest 29/29 OK. První kompletní průchod
produkčním Chromium: 13/13 OK (XML/TXT/DOCX import/export, opakování, změna
pořadí, obnova konceptu, mobilní layout). Kontrola obsahu dist OK.
Následně přidán produkční scénář načtení assetů pod cestou repozitáře,
práce a XML exportu bez sítě a obnovy po opětovném připojení.

Desktop: 862 skutečných XML roundtripů + nová píseň a základní Chromium
export přijaty repository/WidgetSource/parserem. Opraveno zastaralé očekávání
v `tests/verify_desktop.py`: po současném scénáři se původní live zachová
s 3 opakováními a vznikne nové výchozí short, nikoli 4 opakování původního.
DOCX browser export přijat současným desktopovým loaderem.

Uživatel na HTTPS nepotřebuje instalaci ani lokální server. `file://` není
podporované spuštění; offline nové načtení bez PWA není garantováno. Lokální
obnova závisí na úložišti prohlížeče, profilu a adrese. Test používaného EXE,
Safari/Firefox a ruční kapelnické ověření zbývají. Po nasazení spustit testy
s EDITOR_URL a projít scénáře na skutečné adrese. Připomenout uživateli commit,
ale nevytvářet jej automaticky.

Závěrečný výsledek: **14/14 produkčních Chromium scénářů OK**, včetně nového
ověření práce bez sítě; **29/29 Vitest OK**. Obě desktopové kontrolní utility
po aktualizaci očekávání prošly celé: 862 roundtripů + nová píseň, skutečné
XML downloady, více jazyků a skupin, legacy guide a DOCX výstup. Skutečný
screenshot produkčního desktopového layoutu byl vizuálně zkontrolován.
`git diff --check` bez chyb. Veřejnou aplikaci nebylo možné funkčně otestovat,
protože cílová URL vrací 404. Přímé ověření po nasazení zůstává povinné.

## 26. Větev pro publikaci

Na přání uživatele byl současný `test` bez konfliktů sloučen do existující
větve **`Sbor`**. Sloučení je připravené, bez vytvoření commitu a bez push.
Workflow publikuje výhradně z `Sbor` (push trigger i podmínka deploy jobu),
`test` zůstává vývojová větev. Před dokončením merge commitu zahrnout také
upravený workflow, tento plán, předávací návod a ignorování cache `.vite/`.
GitHub Pages nastavit na GitHub Actions a případné omezení prostředí na `Sbor`.

## 27. Budoucí tlačítko Uložit a nadpis

Nadpis nyní zní „Baptisté Šumperk: Editor písní“. V horní liště je za ostatními
akcemi tlačítko „Uložit“, odsazené pružnou mezerou úplně doprava. Je skutečně
disabled a šedé; popisek vysvětluje budoucí ukládání do společné databáze.
Tlačítko neprovádí žádnou akci. Databáze zůstává samostatnou budoucí etapou.
Změněny main.ts, style.css a očekávání stávajícího layout testu.
Produkční build OK. Commit ani push nejsou součástí úpravy.
Layout ověřen na produkčním buildu: Chromium 2/2 OK (1280 a 390 px).
