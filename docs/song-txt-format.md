# TXT pro Poznámkový blok

Aktuální podoba podle upraveného zadání 3. 11. 2026: **bez technické hlavičky,
identity a povinných dvojteček**. TXT je jednoduchý text vybraného jazyka;
plná záloha a přenos do SuperPresenteru zůstávají XML. Stejný tok pro Word
popisuje [návod DOCX](song-docx-format.md).

## Rychlý postup

1. Pro novou píseň klikněte **Stáhnout prázdnou TXT šablonu**. Obsahuje
   „Název písně“, „Sloka 1“, „Refrén 1“ a „Bridge 1“. Nahraďte první řádek
   názvem a pod jednotlivé nadpisy dopište text. Nepotřebný nadpis smažte celý.
2. Pro úpravu existující písně klikněte **Stáhnout TXT**, vyberte jazyk
   a pořadí a potvrďte **Stáhnout vybraný jazyk do TXT**. Původní píseň
   ponechte otevřenou. Pro plnou zálohu si stáhněte také XML.
3. Soubor upravte v Poznámkovém bloku a uložte jako UTF-8. BOM i Windows
   konce řádků CRLF jsou přijímány; export je používá.
4. Přes **Importovat TXT** soubor načtěte. Před použitím zkontrolujte náhled
   všech definic, pořadí a případných problémů.
5. Standardně import vytvoří novou píseň s novým UUID; jazyk nové písně
   lze před importem změnit (předvyplněna čeština, obsah se nepřekládá).
   Při shodě názvu s otevřeným konceptem nebo jeho dostupným originálem
   místo toho nabídne přepsání textů zvoleného jazyka nebo novou píseň
   s jiným názvem. Před přepsáním je potvrzení. Rozpracované koncepty navíc
   chrání stávající potvrzení zahození neexportovaných změn.

Web nevidí knihovnu na disku: **shodu názvů kontroluje jen s otevřenou písní
a jejím případným originálem při práci s kopií**, nikoli se všemi místními XML.
Srovnání ignoruje velikost písmen a okolní mezery, zachovává rozdíly diakritiky.
Shoda názvu pouze nabízí volbu, nikdy nepřepisuje automaticky.
Chcete-li vrátit úpravu do původní písně, ponechte v TXT její název. Při změně
názvu se TXT nabídne jako nová píseň; název lze změnit až v editoru po aktualizaci.

## Příklad a pravidla

```text
Ukázková píseň

Sloka 1
Text první sloky.

Refrén 1
Text refrénu.

Sloka 2
Text druhé sloky.

Refrén 1
```

Vzniknou tři definice v1, r1, v2 a pořadí v1 r1 v2 r1. Každý nadpis vytváří
jeden výskyt v pořadí. Prázdný blok odkazuje na dříve definovanou část
stejného typu a čísla; neexistující ani dopředné odkazy nejsou povoleny.
Prázdná stažená šablona tedy slouží k doplnění, nelze ji importovat bez textů.

- Nadpis je samostatný řádek Sloka, Refrén/Refren nebo Bridge. Velikost písmen,
  diakritika, mezera před číslem a koncová dvojtečka nejsou podstatné:
  `sloka1`, `Sloka 1`, `SLOKA 1:` i `Slóka1` znamenají v1.
- Samotné `Sloka`, `Refrén`, `Bridge` znamenají číslo 1. Opakované shodné
  texty stejného nadpisu se sloučí do jedné definice, výskyty v pořadí zůstanou.
  Jediná nečíslovaná sloka se v editoru zobrazí jako v1.
- Odlišný text stejného nadpisu vyvolá varování a blokuje import. Explicitní
  **Vyřešit odlišné texty vytvořením variant** vytvoří další volné číslo
  stejného typu (r2 apod.), zachová první text a ukáže nové reference.
  Stejný nový text opakovaný znovu používá tuto variantu. Následující prázdné
  odkazy téhož nadpisu míří na poslední rozpoznanou variantu; původní
  neprázdný text přepne odkaz zpět na původní část. Čísla pozdějších nadpisů
  jsou rezervována. Varianta zde znamená textovou část, nikoli nový jazyk.
- Prázdné řádky uvnitř textu nevytvářejí části. Jeden prázdný řádek hned za
  nadpisem a jeden před dalším nadpisem/koncem jsou oddělovače; další jsou text.
  Ostatní odsazení a mezery se zachovávají. Blok jen s bílými znaky je odkaz.
- Doslovný řádek textu vypadající jako nadpis začněte `\`, např. `\Refrén 1`.
  Doslovné počáteční zpětné lomítko zdvojte. Export to provádí automaticky.
- První neprázdný řádek je název. Starší zápis `Název: Píseň` se také přijímá.
  Stará technická TXT hlavička se při importu přečte pro kompatibilitu, ale její
  identita ani jazyk se nepoužijí. Nový export hlavičku nevytváří.
- Čísla jsou přesné řetězce (01 a 1 jsou různá ID). Limity: 1 MiB a 4096 výskytů,
  dále běžné limity pořadí a prezentačních řádků editoru.

## Jeden jazyk a více pořadí bez ztráty původní písně

Výběr exportu jasně upozorňuje: TXT obsahuje **jen vybraný jazyk a jedno
jednoduché pořadí**, neobsahuje UUID, jména jazyků/pořadí, main ani metadata.
Není plnou zálohou; další jazyky, pořadí a metadata uchovává původní XML.
Jejich přítomnost již TXT export neblokuje. Vybraný jazyk musí mít neprázdné
texty částí s ID v/r/b + číslo a vybrané pořadí musí být ploché. Skupiny,
výběry řádků, připojování @, vlastní ID, nepoužité/prázdné části vybraného
jazyka a nepřevoditelné texty stále vyžadují XML; nic se tiše nezplošťuje.

Při potvrzeném přepsání jazyka:

- Zachová se původní UUID, název, atributy a metadata. Změní se jen texty částí
  stejného ID ve vybraném jazyce; ostatní jazyky a vynechané části zůstanou.
- Nové části se přidají pouze do vybraného jazyka. UI předem upozorní, že pro
  prezentaci ve více jazycích mohou jejich protějšky chybět; editor to diagnostikuje.
- Všechna původní pořadí zůstanou přesně včetně nested umístění, main a výrazů.
  Pokud je TXT pořadí shodné s právě vybraným plochým pořadím, nic se nepřidává.
  Jinak přibude nevýchozí pořadí TXT (případně TXT 2 atd.). Pro přehrání nové
  posloupnosti ho výslovně vyberte a případně nastavte jako výchozí.
- Změna textů může ovlivnit platnost řádkových výběrů zachovaných pořadí.
  Editor je pak označí diagnostikou; původní výraz se nepřepisuje.

Nová píseň dostává nové UUID, jeden zadaný jazyk a default/main pořadí podle TXT.
TXT nemá revizní hash ani automatické párování identity. Přenos mezi prohlížeči
nebo bez otevřeného originálu proto zakládá novou píseň; pro zachování identity
nejdříve otevřete původní XML a ponechte shodný název TXT.
Stažení TXT neruší dirty stav. Stažení XML ani TXT nepřepisuje soubor na disku.

## Ruční test až do SuperPresenteru

1. Importujte `web-song-editor/examples/ukazkova-pisen.txt` jako novou píseň.
   Ověřte tři části a v1 → r1 → v2 → r1. Poznamenejte si UUID z editoru.
2. Přidejte druhý jazyk, doplňte jeho texty a stáhněte XML zálohu.
   Klikněte Stáhnout TXT, vyberte češtinu a hlavní pořadí a stáhněte.
3. V Poznámkovém bloku upravte refrén na „Příliš žluťoučký kůň zpívá.“
   a přidejte prázdný řádek dovnitř sloky. Název ponechte; uložte UTF-8/CRLF.
4. Importujte TXT. Ověřte náhled a nabídku shody názvu. Vyberte češtinu,
   nejprve přepsání zrušte a zkontrolujte zachování práce. Potom přepsání potvrďte.
   UUID, druhý jazyk a původní pořadí musí zůstat; refrén musí být upravený dvakrát.
5. Doplňte do TXT další výskyt refrénu a import opakujte. Ověřte nové pořadí
   TXT a zachování původního pořadí. Nové vyberte a případně nastavte jako výchozí.
6. Stáhněte XML, otevřete znovu ve webu a ověřte identitu, oba jazyky a pořadí.
   Vložte XML do **testovací kopie** knihovny používaného SuperPresenteru,
   promítněte oba jazyky i obě pořadí a zkontrolujte diakritiku. Po uložení
   desktopovým editorem zkontrolujte song-id. Původní knihovnu nahraďte až po kontrole.
7. Zkuste shodu názvu → nová s jiným názvem: musí vzniknout jiné UUID.
   Stáhněte a vyplňte prázdnou šablonu a vyzkoušejte i její import.

Po kontrole vytvořte ruční commit; agent jej nevytváří.
