# Word DOCX pro offline úpravy písní

DOCX používá stejná pravidla jako [TXT](song-txt-format.md), pouze se otevírá
ve Wordu. Soubor obsahuje název a běžné odstavce s nadpisy Sloka 1, Refrén 1,
Bridge 1 a texty. Nemá technickou hlavičku, identitu ani povinné dvojtečky.
Nadpisy nemusí mít speciální styl. Podporován je **.docx**, nikoli starší .doc,
DOCM, dokumenty s makry nebo šifrované dokumenty chráněné heslem.

## Rychlý postup

1. Nová píseň: **Stáhnout prázdnou DOCX šablonu**. Ve Wordu nahraďte
   „Název písně“ vlastním názvem a pod nadpisy doplňte text. Nepoužité nadpisy
   smažte celé. Prázdná šablona bez doplněných textů není platnou písní.
2. Úprava existující písně: **Stáhnout DOCX**, vyberte jazyk a pořadí a klikněte
   **Stáhnout vybraný jazyk do DOCX**. Ponechte původní píseň otevřenou
   a název v dokumentu neměňte. Pro plnou zálohu si stáhněte také XML.
3. Dokument upravte ve Wordu a uložte jako běžný **Dokument Word (.docx)**.
   Nadpisy mohou být i `sloka1`, `Sloka 1`, `SLOKA 1:` nebo samotné `Sloka`.
   Používejte běžné odstavce. Enter i ruční zalomení Shift+Enter se čtou jako
   konce řádků; automatické zalomení dlouhého textu podle šířky stránky nikoli.
4. Zvolte **Importovat DOCX**. Zkontrolujte náhled definic, pořadí a problémů.
   Shodné nadpisy se stejným textem mají jednu definici a více výskytů.
   Prázdný blok opakuje dřívější definici. Neexistující odkazy import blokují;
   odlišné texty stejného nadpisu vyžadují explicitní vytvoření variant.
5. Import standardně založí novou píseň s novým UUID. Při shodě názvu
   s otevřenou písní nebo dostupným originálem kopie nabídne přepsání
   textů vybraného jazyka nebo novou píseň s jiným názvem. Žádné přepsání
   neproběhne automaticky. Kontrola neprohledává knihovnu na disku.
6. Při přepsání jednoho jazyka zůstanou zachované UUID, ostatní jazyky,
   vynechané části, atributy a metadata i všechna původní pořadí. Pokud se
   dokument liší pořadím od aktuálně vybraného plochého pořadí, přibude nové
   nevýchozí pořadí **DOCX** (případně DOCX 2). Původní výrazy se nenahrazují.
   Nové části jsou jen ve vybraném jazyce; chybějící protějšky editor diagnostikuje.

## Co se přenáší a co ne

Přenášejí se **texty a pořadí částí**, Unicode, odstavce, ruční zalomení,
mezery, tabulátory a prázdné řádky podle stejných oddělovacích pravidel jako TXT.
Rozdělení textu do více Word runů kvůli tučnému písmu či kontrole pravopisu
nemění rozpoznání nadpisu. Nadpisy číslujte přímo textem, nikoli automatickým seznamem.

Fonty, tučné písmo, barvy, Word styly, rozložení stránek a cíle odkazů se
nepřenášejí; náhled na to upozorňuje. Záhlaví, zápatí, komentáře a samostatné
poznámky se do písně nepřebírají a jejich přítomnost vyvolá upozornění.
Tabulky, obrázky, vložené objekty/textová pole, pole, reference na poznámky,
sledované změny a přímo číslované seznamy se odmítají s vysvětlením. Revize
nejprve přijměte nebo odmítněte ve Wordu; píseň případně zkopírujte do běžných
odstavců. Automatická čísla zděděná ze stylu nejsou text a nepřenášejí se;
přítomnost definic číslování vyvolá upozornění. Vždy zkontrolujte náhled.

Export obsahuje jen vybraný jazyk a jedno jednoduché pořadí. Ostatní jazyky,
pojmenovaná pořadí, main, identitu a XML metadata soubor DOCX neobsahuje;
UI to uvádí před stažením. Skupiny, výběry řádků, @, vlastní ID a nepoužité
či prázdné části vybraného jazyka zůstávají mimo rozsah jednoduchého exportu;
použijte XML. DOCX download nemaže dirty stav a nepřepisuje soubory na disku.

DOCX se zpracuje místně v prohlížeči, žádné dokumenty se neuploadují.
Nečtou se externí vztahy, nevykonávají se makra ani obsah dokumentu.
Limit souboru je 5 MiB, hlavního rozbaleného XML 1 MiB a 256 ZIP položek;
XML má limit 30 000 elementů a 64 úrovní. Platí také limity společného TXT
parseru a pořadí. Rozbalování je průběžně omezené i při nepravdivých ZIP délkách.
Chyba načtení, zrušení náhledu nebo potvrzení nepřepíší otevřený koncept.

Ukázky: `web-song-editor/examples/ukazkova-pisen.docx`,
`web-song-editor/examples/sablona-pisne.docx`.

## Konkrétní ruční test Word → editor → XML → SuperPresenter

1. Otevřete ukázku DOCX v editoru jako novou píseň. Ověřte tři definice
   a pořadí **v1 → r1 → v2 → r1**. Poznamenejte si UUID. Přidejte druhý jazyk
   a doplňte jeho texty. Stáhněte XML zálohu.
2. Stáhněte DOCX češtiny s hlavním pořadím. Ve Wordu změňte refrén na
   „Příliš žluťoučký kůň zpívá.“, část textu zvýrazněte tučně a uprostřed sloky
   přidejte prázdný odstavec. Název ponechte; dokument uložte jako .docx.
3. Importujte DOCX. V náhledu ověřte tři části, nový text a v1 r1 v2 r1.
   Při shodě názvu vyberte češtinu. Nejprve přepsání zrušte a zkontrolujte
   zachování práce; poté ho potvrďte. UUID a druhý jazyk se nesmí změnit,
   refrén musí být v náhledu dvakrát. Tučné písmo se nepřenáší.
4. Zkuste doplnit další výskyt Refrén 1 a import zopakujte: přibude nevýchozí
   pořadí DOCX, původní zůstane. Nové pořadí vyberte a případně nastavte jako výchozí.
5. Stáhněte XML, otevřete ho znovu ve webu a ověřte texty, jazyky, UUID a pořadí.
   XML vložte do **testovací kopie** knihovny používaného SuperPresenteru,
   otevřete v používaném EXE a přehrajte celé pořadí v obou jazycích. Ověřte
   diakritiku a desktopové zpracování prázdných řádků. Po uložení desktopovým
   editorem zkontrolujte song-id.
6. Vyplňte prázdnou šablonu a zkuste nový import. Zkuste také konfliktní
   text stejného refrénu, neexistující prázdný Bridge 2 a dokument s tabulkou:
   musí být náhled či chyba a původní práce musí zůstat nedotčená.

Po ruční kontrole vytvořte commit; agent ho nevytváří.
