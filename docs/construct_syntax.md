# Syntaxe constructu a kompatibilita

Odvozeno z `WidgetSource.readInstructions`, `longText`, `shortText` a metod
pro navigační skupiny v commitu `0965cf4`. Kompletní katalog složených výrazů
je v [construct_inventory.md](construct_inventory.md). Písně nebyly měněny.

## Pravidla

| Zápis | Význam | Příklad v songs |
|---|---|---|
| `v1 r1 v2 r1` | Sekce v uvedeném pořadí, rozlišuje velikost písmen. | `znovu_-_premyslim_nad_obeti.xml` (začátek) |
| `(v1 v2)` | Celá skupina dvakrát, závorky nejsou pouhé seskupení. | `dobrorec_duse_ma_hospodinu.xml` |
| `(b1)*4` | Celá skupina čtyřikrát; lze i `(b1) * 4`. | `at_pozehnan_je_buh.xml` |
| `r1.9` | Jeden řádek sekce, běžně číslováno od 1. | `muj_svet.xml` |
| `r1.1:2` | Řádky 1 až 2 včetně; druhé číslo musí být větší. | `hoden_je_beranek.xml` |
| `(b1.1)*3 b1.2` | Opakovaný jeden řádek a potom další řádek. | `at_srdce_me_tebe_vida.xml` |
| `((v1) (r1)) (v1)` | Vnořené skupiny; každá závorka má vlastní opakování. | `vzyvam_jmeno_jezis.xml` |

Celkem 60 výrazů obsahuje závorky, 12 hvězdičku, 7 tečku (z toho 3 dvojtečku),
1 vnoření. Kategorie se překrývají a zahrnují i vadné výrazy.

- Oddělovačem je ASCII mezera, nikoli libovolný whitespace. Opakované mezery
  jsou přípustné. Parser text nestripuje, aby zachoval pozice. Dosavadní XML
  import spojuje neprázdné fyzické řádky mezerou a UI nadále provádí své stripování.
- Jméno sekce je přesná hodnota ze seznamu dostupných sekcí. Parser nevyžaduje
  číslo za prvním písmenem: `r`, `b`, `r0`, `v1a`, `v1b` fungují. Token končí
  na mezeře, tečce nebo závorce; dvojtečka a hvězdička nejsou oddělovače jména.
- Čísla jsou nezáporné ASCII číslice, bez znaménka. Podle upřesnění uživatele
  jsou kolem `*`, `.` a `:` i uvnitř závorek povolené mezery:
  `( r2 . 3 ) * 3` znamená totéž jako `(r2.3)*3`.
  Mezery mezi sekcemi zůstávají oddělovači: `v1 v2` jsou dvě sekce v tomto
  pořadí. Mezery uvnitř ID nebo čísla se neslepují (`v 1` není `v1`).
  Počet opakování platí pouze pro skupinu. `v1*2` ani `b1.2*4` nejsou násobení
  sekce/řádku. Druhý případ skutečně existuje v databázi a oba parsery jej odmítají.
- Bez mezer funguje například `(v1)r1` nebo `v1.1:2r1`; jde o historické
  chování tokenizace, nikoli doporučení nového zápisu.
- `.2:2` je neplatný rozsah; pro jediný řádek je `.2`. Původní anglická
  zpráva omylem tvrdila, že druhé číslo má být menší; podmínka byla opačná.

## Strukturované API

```python
from superpresenter.services.construct_parser import parse_construct

construct = parse_construct('v1 (r1.1:2)*3', ['v1', 'r1'])
# Construct.instructions: tuple[SectionStep | RepeatGroup, ...]
instructions, used_sections = construct.to_legacy()
```

`SectionStep` obsahuje `section`, `position`, `start_line` a `end_line`.
Obě meze `None` znamenají celou sekci; samotné `start_line` jeden řádek;
obě čísla uzavřený interval. `RepeatGroup` obsahuje uspořádané `children`,
`repeat`, pozici otevírací závorky a `reuse_lines=True`. Opakování sekčního
kroku jednoznačně určují jeho nadřazené skupiny; strom zachovává jejich hranice.
Datové třídy jsou neměnné, bez GUI a projektorů. Parser ani překlad do starých
instrukcí nerozbalují násobení a nepoužívají rekurzi pro vnořené skupiny.

V `longText` se skupiny fyzicky rozbalují. V `shortText` zůstávají řádky skupiny
jednou a navigační indexy se opakují; jejich začátek a konec se označí podle
stylu `repeat_start` a `repeat_end`. Proto nelze nahradit skupinu pouhým seznamem
kopií sekcí. Samostatná syntaxe pro připnutí libovolného řádku neexistuje;
konkrétní obrazovkové indexy či značky nelze určit bez textu a stylů.

`Construct.to_legacy()` vrací totožný zásobníkový program (`all`, `line`, `lins`,
`conn`, `mult`) a sekce v pořadí prvního výskytu. `WidgetSource.readInstructions`
jej ukládá do dosavadních polí až po úspěšném parsování. Vrací `Construct`,
chyby vyhazuje jako výjimky. Jediné produkční volání zachytává `ConstructError`
a zobrazí jeho zprávu. Číselné chybové kódy už nejsou součástí produkčního parseru.
Renderery, navigace a výpočet skupin zůstaly beze změny.

## Chyby

Všechny dědí z `ConstructError(ValueError)` a obsahují `position`: index od 0
v přesném vstupním textu, také uvedený v čitelné zprávě.

| Výjimka | Pozice |
|---|---|
| `ParenthesisError` | Neuzavřená otevírací nebo přebytečná uzavírací závorka. |
| `UnknownSectionError` | Začátek neznámého tokenu. |
| `InvalidRangeError` | Začátek druhého čísla neplatného intervalu. |
| `ExpectedNumberError` | Místo očekávané číslice za `.`, `:` nebo `*`, případně konec textu. |
| `EmptyConstructError` | 0 pro prázdný text nebo pouze mezery. |

## Zachované zvláštnosti a omezení

- `.0` se historicky mění na Python index -1, tedy poslední řádek. `.0:2`
  zahrne poslední řádek a pak první dva. Parser to zachovává; nejde o nově
  doporučené číslování. V aktuální databázi takový zápis není.
- `()*2`, prázdné skupiny a násobení nulou původní parser přijímá. Přijímá je
  i služba, ale staré renderery u prázdných/nulových skupin mohou selhat.
  V aktuální databázi nejsou. Prázdný construct nyní vyvolá konkrétní výjimku;
  aplikace jej odmítala už před touto etapou před spuštěním parseru.
- Rozsah nad počet řádků nelze ověřit pouze ze jmen sekcí; dosavadní renderery
  doplňují prázdné texty. Není přidána validace délek ani změna navigace.
- V aplikaci se používá průnik sekcí vybraných jazykových variant, stejně jako
  dříve. Inventář XML používá sjednocení, aby našel i výrazy uvnitř variant.
- Velká opakování jsou ve službě kompaktní, ale staré renderery je mohou
  nákladně rozbalit. Zavedení limitů by bylo samostatnou změnou chování.
- Dosavadní `importRepetitions` nečte text na stejném řádku jako otevírací
  XML tag. Například u `hoden_je_beranek.xml` tak vrací prázdný guide; XML
  inventář a test parseru jej čtou přes ElementTree, jako editor. Tento problém
  importeru nebyl opravován. Test přes skutečný importer kontroluje neprázdné
  výsledky; prázdný vstup se samostatně testuje jako `EmptyConstructError`.
- `short2` u některých opakovaných skupin počítá více položek, než je uloženo
  v krátkém textu, a vyvolá `IndexError` (např. `at_srdce_me_tebe_vida.xml`).
  Regresní test ověřuje stejnou chybu původní i nové cesty; její oprava by
  zasahovala do navigace, která je výslovně mimo tuto etapu.
- Historický parser je ponechán pouze jako neměnná testovací reference
  `tests/fixtures/legacy_construct_parser.py`, nikoli jako produkční fallback.
  Testy srovnávají přijetí/odmítnutí i přesné instrukce na celé databázi,
  skutečný import s výběrem variant a výstupy stávajících rendererů.

## Explicitní připnutí (etapa 6)

Nový prefix `@` před výběrem určuje připnutý výskyt: `v1 @v1.4 v2`
nebo `v1 @v1.3:4 v2`. Vyžaduje jeden nebo dva sousední řádky od 1;
celá sekce, nula a delší rozsahy nejsou povolené (`InvalidPinError`).
`SectionStep.pinned` má bez označení hodnotu `False`. Závorky zachovávají
význam opakování: `(@v1.4)*3` jsou tři explicitní výskyty. Samotný výběr
ani `RepeatGroup.reuse_lines` tento nový příznak nenastavuje.

XML guide zůstává obyčejný text. `to_legacy()` překládá označený výběr
stejně jako neoznačený, bez nové instrukce pro staré renderery. API
`resolve_sections(construct, variant)` předá příznak stacionárnímu generátoru.
Čísluje neprázdné LF řádky po odstranění krajních mezer; model XML nemění.
Neexistující připnutý řádek je chyba adaptéru i validátoru.

Generátor připojí označený blok pouze před následující obsah, pokud se celý
součet vejde do 8. Jinak ponechá blok samostatný, i na konci písně. Dlouhou
následující sekci z tohoto důvodu nepřeskupuje. Sousední označené bloky
slučuje zprava při stejné kontrole kapacity. Stream dělí každou hotovou
stránku po nejvýše 4 řádcích. Obsah nikdy neodvozuje z textové shody.
Podrobné příklady, kompatibilita, omezení současného GUI a výsledky testů
jsou v README v etapě 6; tato pravidla nahrazují starší návrh atributu sekce.
