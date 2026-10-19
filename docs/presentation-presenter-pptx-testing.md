# PPTX import — postup ověření

Import je převod obsahu do našich úseků, ne přehrávač PowerPointu. Nevyžaduje PowerPoint, LibreOffice ani novou Python závislost. Originál PPTX se pouze čte. Výsledek se ukládá do `.ppres` s vloženými obrázky.

## Umístění ovládání

- **Soubor → Přenos → Import PPTX**, vedle Import JSON.
- **Úseky → Úpravy úseků → Sloučit s následujícím**, pod dvojicemi přidání/mazání a duplikování. V malé šířce použijte stávající vodorovný posuvník ribbonu.
- Import otevře samostatné modální okno. První karta ukazuje zároveň sál a stream, šipky procházejí všechna odvozená pokračování a černé předěly. Druhá karta obsahuje úplné mapování původních snímků, upozornění a převedený text.
- Zaškrtávátko pro spojení stejného odkazu je nahoře. Vložení je dole, dostupné ihned při platném převodu. Kliknutí na Vložit je samotné potvrzení; obecný varovný text ani souhlasový checkbox se nezobrazují. Konkrétní upozornění zůstávají na druhé kartě.

## Ruční scénáře

1. Spusťte novou instanci `python -B presentation_presenter_v2.py`. V Soubor → Přenos zvolte Import PPTX a vyberte `songs/zdrojove soubory/Prezentace - stream vzor.pptx`. Očekávání: nadpis **odkaz**, tělo začíná **Text text…**, dekorativní obdélník kamery není novým obrázkem. Na druhé kartě je upozornění na dekorace. Zkontrolujte oba výstupy a vložte. Úvodní nedotčený prázdný úsek se nahradí.
2. Na kopii vaší šablony vytvořte dva sousední snímky s odkazem **Jan 16:4–21**, první s textem A a druhý B. Se zapnutým spojováním očekávejte jeden úsek, nejprve odstavec A a potom B. Po vypnutí dva úseky. Původní ruční hranice se při spojení nezachovává, dělení určuje náš systém pro oba výstupy.
3. Mezi stejné dva snímky vložte skutečný černý snímek. Očekávání: dva úseky i se zapnutým spojováním a černý předěl před druhým. Zkuste také černý začátek, černý konec a dva černé snímky za sebou; sousední černé se sjednotí s upozorněním. Prázdný snímek s neurčeným pozadím se nemá automaticky považovat za černý.
4. Dejte za sebe **Jan 16:4–21** a **Římanům 8:1–4** bez černého snímku. Musí zůstat dva samostatné úseky bez přidaného předělu. Prázdné nadpisy se automaticky nespojují.
5. Import zrušte. Současný dokument, historie, souborová cesta i živá session mají zůstat stejné. Potom import vložte do existující prezentace: umístí se za vybraný úsek. Jedno Zpět vrátí celý import, Znovu ho obnoví. Neztratí se předchozí obsah. Pokud je na konci importu černý snímek a za vloženým blokem následuje původní úsek, předěl se přenese před něj.
6. V Úsecích vyberte první ze dvou úseků a použijte Sloučit s následujícím. Předem se zobrazí potvrzení, včetně upozornění na odstranění vnitřního předělu a jiný druhý název. Zůstává hlavička prvního, pořadí odstavců a jejich formátování; vnější předěly zůstávají. Jeden krok Zpět vrátí oba původní úseky. Poslední úsek nelze sloučit s neexistujícím následujícím.
7. Vyzkoušejte skutečné odrážky PowerPointu: tři položky, jednu pododrážku a v položce měkký konec řádku Shift+Enter. Očekávání: tři naše položky, správná podúroveň a měkký konec stále uvnitř téže položky. Pouhé vizuální zalomení dlouhého textu není další odrážka. Textový znak „•“ napsaný ručně není skutečné odrážkové formátování a zůstane textem. Hlubší seznamy než tři úrovně a vlastní číslování hlásí zjednodušení.
8. Vložte do PPTX dva běžné PNG/JPEG obrázky. Očekávání: dvě obrázková média v naší automatické mřížce, původní pozice se nepřebírají; poměry stran zůstávají. Výchozí obrázky jsou pouze na prvním pokračování úseku, lze změnit ve stávajícím obrázkovém editoru. Ve streamu zkontrolujte rezervu kamery. Při ručním sloučení se mřížka přepočte pro oba výstupy a volba prvního/všech pokračování se zachová.
9. Do kopie přidejte tabulku, graf, poznámky, animaci nebo externě propojený obrázek. Před vložením musí být vidět konkrétní upozornění. Nevěrné či chybějící prvky lze odmítnout zrušením importu a připravit zdroj jinak; tato verze neumí jejich vykreslení do obrázku. Nepřevedený obsahový snímek se ponechá jako prázdný úsek s upozorněním, nikoli tiše vynechá.
10. Změňte poměry sálu a streamu a importujte dlouhý text. V obou náhledech musí být totožný obsah, rozdílně zalomený, bez kamery přes text. Ověřte chybové hlášení při neproveditelném layoutu; vložení musí být zakázané.
11. Při běžící projekci importujte nebo slučte úseky. Živý obsah a pořadí zůstávají původní až do **Použít do projekce**. Potom ověřte oba skutečné výstupy. Toto je fyzická QA, automatické testy ji nenahrazují.
12. Výsledek uložte jako `.ppres`, zavřete testovací instanci a otevřete soubor znovu. Musí fungovat bez původního PPTX i zdrojových obrázků. Porovnejte originální PPTX před/po importu (například SHA-256): nesmí se změnit. Na zkušební kopii běžné prezentace ověřte i staré otevření/uložení, JSON import a samostatný SuperPresenter.

## Automatické ověření

Z kořene projektu:

```powershell
python -B -m unittest tests.presentationpresenter.test_pptx_import -v
python -B -m unittest discover -s tests/presentationpresenter -v
```

Ve zdejším prostředí je ověřený runtime `C:/Users/moski/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`. Sandbox může blokovat Temp; testy potřebují povolený zápis do své dočasné složky a vlastní Tk okna. Nic neinstalují a neukládají uživatelská nastavení.

`tests/presentationpresenter/visual_pptx_import.py <výstupní_složka>` vytvoří dočasnou syntetickou PPTX, vlastní QA okno a pět snímků UI. Před zachycením ověří, že cílový výřez patří tomuto oknu. Nespouštět současně s jinými GUI testy kvůli fokusu.

## Hranice podpory

- Běžné nešifrované `.pptx` v PresentationML namespace Office 2007+. `.ppt`, šifrované prezentace a plná kompatibilita variant OOXML nejsou slíbené.
- Naše výchozí písmo, velikost a barva; základní B/I/U podle dostupných přímých a podporovaných zděděných vlastností. Pozice, mezery, zarovnání a vizuální styly PowerPointu se nenapodobují.
- Automatický nadpis: standardní titulkové pole, potom pole pojmenované Nadpis/Title/Odkaz; jinak odhad horního pole s upozorněním. Více polí těla: pořadí objektů v PPTX s upozorněním, ne zaručené pořadí čtení. Opravy lze provést po importu v editoru, případně import zrušit.
- Černé předěly: jednoznačné prázdné snímky se solidním černým pozadím (včetně rozpoznaného zděděného motivu) nebo jednoduchým černým obdélníkem přes celý snímek. Složitě složená či nejasná černá grafika se automaticky za předěl nepovažuje.
- Obrázky: podporované rastrové formáty dle stávajícího média adaptéru; přenosný výsledek PNG. Vektorové, propojené nebo nečitelné obrázky se hlásí, nestahují se z internetu. Ořez/rotace/efekty a rozmístění se nepřenášejí.
- Čtení omezeno na 100 MiB vstupu, 250 MiB deklarovaných rozbalených dat, 10 000 ZIP součástí, 1 000 původních snímků, 5 MiB na XML a stávající limity médií/`.ppres`. Import je synchronní; velké soubory mohou krátce blokovat UI. Nejde o test maximální kapacity ani několikahodinové projekce.
- Žádný renderer celých snímků, Office automatizace, LibreOffice, video ani přehrávání animací. Stávající build a SuperPresenter se nemění; nový distribuční balíček v této práci nevzniká.
