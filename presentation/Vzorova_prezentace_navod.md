# Vzorová prezentace PresentationPresenteru

V aplikaci použijte **Soubor → Otevřít** a vyberte `Vzorova_prezentace.ppres` z této složky. Nejde o import PPTX. Doporučený první krok je Uložit jako pod vlastním názvem, abyste si zachovali originál ukázky.

PresentationPresenter nyní otevřete také tlačítkem **prez** v SuperPresenteru. To spouští novou verzi `presentation_presenter_v2.py`; další kliknutí během jejího běhu nezakládá druhý proces. Ve společném EXE se používá přepínač `--presentation-editor`, který spouští stejnou novou aplikaci. Již vytvořené EXE se změní až novým sestavením distribuce.

Hned napravo od **prez** je v SuperPresenteru tlačítko **bible**. Otevře samostatný výběr biblické pasáže s náhledem, překlady, volbou čísel a souvislého textu / veršů pod sebou. Výsledek lze zkopírovat do schránky; tlačítko pro vložení do prezentace zde není. Vložení je dostupné jen v Bibli otevřené z editoru PresentationPresenteru. Opakovaný klik během běhu nezakládá druhý proces; po zavření lze Bibli znovu otevřít. Společné EXE podporuje také přímý přepínač `--bible`.

Pokud při zavírání SuperPresenteru ještě běží prezentace nebo Bible spuštěná jeho tlačítkem, objeví se volby **Zavřít vše**, **Jen SuperPresenter** a **Zrušit**. Volba Jen SuperPresenter ponechá tyto nástroje (i případnou projekci prezentace) běžet samostatně. Zavřít vše požádá jejich okna o běžné zavření: prezentace se může zeptat na uložení a zrušení tohoto dotazu ponechá prezentaci otevřenou, i když už SuperPresenter skončil. Zrušit v prvním dialogu ponechá otevřené všechny aplikace. Samostatně spuštěné nástroje mimo tlačítka SuperPresenter neukončuje. Vyzkoušejte obě volby a storno na pracovní kopii ukázky.

Soubor obsahuje 24 upravitelných úseků, při výchozím nastavení 57 snímků včetně černých předělů a čtyři vložené PNG: korálový obdélník na šířku, tyrkysový na výšku, žlutý čtverec a fialový široký obdélník. Nepotřebuje externí obrázky. Nastavení dokumentu: sál 4:3, stream 16:9, prostor kamery vpravo dole. Kamera je rezervovaná plocha; aplikace do ní nepřipojuje video.

Při ověřování společného zavření zkuste také spuštění přes projektový Python ve virtuálním prostředí nebo společné EXE: vlastní okno může běžet v navazujícím procesu spouštěče. Zavřít vše musí stále vyvolat standardní dotaz prezentace na uložení; jeho storno musí ponechat prezentaci otevřenou.

## Co uvidíte v jednotlivých úsecích

| Úsek | Ukázka a očekávaný výsledek |
|---|---|
| 01 | Úvod, větší tučné písmo a barevný text. Před úvodem je černý snímek. |
| 02 | Samostatné odstavce, název úseku a odkaz. V editoru vyzkoušejte změnit obě pole. |
| 03 | Tučné písmo, kurzíva, podtržení, barva, velikosti 28/48 a font Georgia vedle Calibri. Styly jsou skutečně upravitelné, nejde o obrázek textu. |
| 04 | Odrážky ve třech úrovních a návrat k běžnému odstavci. |
| 05 | Číslovaný seznam s vnořenou položkou. |
| 06 | Dva dlouhé odstavce, automaticky rozdělené do pokračování. Oba výstupy mají společný rozsah obsahu, ale různé zalomení řádků. |
| 07 | Jedna dlouhá odrážka přes více snímků, po ní další bod. |
| 08–10 | Stejná skutečná pasáž Jan 3:16–18 (CSP): souvisle bez čísel, souvisle s čísly a verše pod sebou s čísly. |
| 11–12 | Dva úseky za sebou bez černého předělu mezi nimi; různé odkazy. |
| 13–14 | Dvě navazující části se stejným odkazem připravené ke zkoušce sloučení. Popisný text není citace z Přísloví. |
| 15 | Samostatný obrázkový úsek; obdélník zachová poměr stran, stream jej umístí mimo kameru. |
| 16 | Čtyři obrázky různých proporcí v automatické mřížce. |
| 17 | Smíšený text s obrázkem, obtékání a pokračování. |
| 18 | Ruční pozice a velikosti dvou obrázků, samostatné pro sál a stream; propojení výstupů je vypnuté. Vyzkoušejte přímé tažení přes Upravit obrázky. |
| 19 | Obrázek pouze na prvním pokračování. |
| 20 | Obrázek opakovaný na všech pokračováních. |
| 21 | Text připravený ke zkoušce oddělení návrhu od živé projekce. |
| 22 | Samostatné okno Zdrojové úseky, výběr a přesouvání myší. |
| 23 | Společné ukládání výchozích nastavení a písmo platné jen pro tuto prezentaci. |
| 24 | Závěr a následný koncový černý snímek. |

Počet pokračování se může změnit podle dostupných písem, velikostí textu, poměrů stran a kamery.

## Doporučené pokusy

Na kartě **Úseky** ve skupině **Zdrojové úseky** klikněte na **Zobrazit všechny…**. V novém okně kliknutím vyberete úsek do editoru. Přetáhněte ho na jiné místo: světlá čára ukazuje hranici vložení, u horního a spodního okraje seznam automaticky posouvá. Změna se provede až po puštění myši uvnitř seznamu; Escape nebo puštění mimo seznam přesun zruší. Vyzkoušejte Zpět/Znovu a původní tlačítka Nahoru/Dolů. Seznamy zobrazují název, při prázdném názvu biblický či jiný odkaz. Přesun mění návrh; živou projekci až po potvrzení.

1. **Náhled a navigace:** projděte prezentaci šipkami ovládání i klávesnice. U dlouhého úseku sledujte šedé označení právě zobrazené části v editoru. Porovnejte sál a stream, jejich proporce a rezervu kamery. Zmenšete okno a ověřte, že oba náhledy zůstávají dostupné. Ovládání klávesami zkoušejte mimo psaní v textovém poli.
2. **Úpravy a historie:** označte část textu v úseku 03, změňte styl, velikost nebo font. Vyzkoušejte také psaní s nově vybraným stylem, zpět a znovu. Zduplikujte úsek, změňte pořadí a kopii odstraňte.
3. **Dělení textu:** v úseku 06 přidejte další odstavec. Pozorujte přepočet pokračování a společný obsah obou výstupů. Změňte velikost písma a vraťte změnu zpět.
4. **Předěly:** projděte přechod 11 → 12. Zapněte předěl na hranici a sledujte změnu. Vyzkoušejte počáteční i koncový černý snímek. Předěly nejsou prázdné textové úseky.
5. **Sloučení:** vyberte úsek 13 a použijte **Sloučit s následujícím**. Výsledný obsah má obsahovat obě části ve správném pořadí a aplikace jej rozdělí podle svých pravidel. Vyzkoušejte zpět. Stejný odkaz sám o sobě při běžném otevření souboru nic automaticky neslučuje.
6. **Bible:** otevřte biblické okno a vyhledejte Jan 3:16–18. Přepněte čísla a „Každý verš na nový řádek“, vložte výsledek do kopie prezentace. Zkuste také Jan 3:36–4:2, výběr překladu a našeptávání názvu knihy. Tyto volby ovlivňují nové vložení, již uložené úseky 08–10 nepřepínají.
7. **Obrázky:** v úseku 16 změňte pořadí obdélníků a použijte automatické rozmístění. V úseku 18 změňte ruční umístění streamu, porovnejte sál a zkuste znovu propojení / automatické přepočítání. Porovnejte všechna pokračování úseků 19 a 20.
8. **Poměry stran:** změňte poměr sálu na 16:9 nebo streamu na 4:3, prohlédněte přepočtení a vraťte původní hodnoty. Poměry jsou vlastností celého výstupu, ne jednotlivých úseků.
9. **Kamera:** v Nastavení otevřte Kamera streamu. Zkuste šířku a výšku s pravým spodním kotvením, vlastní polohu a odstup textu. Použijte ukázkovou projekci a potom Použít pro prezentaci. Uložení výchozích hodnot mění i budoucí nové prezentace, proto jej používejte jen záměrně.
10. **Živá projekce:** vyberte příslušné monitory a spusťte projekci podle možností svého vybavení. U úseku 21 změňte text v návrhu: živý výstup zůstane stejný do potvrzení změn do projekce. Vyzkoušejte navigaci, dočasnou černou obrazovku a ukončení. Nespouštějte kamerovou kalibraci současně s běžnou projekcí.
11. **Uložení a znovuotevření:** uložte upravenou kopii jako `.ppres`, zavřete ji a znovu otevřete. Obdélníky jsou vložené v souboru; nepoužívají cesty k obrázkům na disku.

## Funkce mimo obsah souboru

### Přímé úpravy obrázků v hlavním náhledu

Na kartě **Domů → Obrázky** je pod **Rozložení obrázků** nové tlačítko **Upravit obrázky**. Zapíná a vypíná přímé úpravy v hlavním náhledu. Zvolte náhled sálu nebo streamu; je-li zobrazena živá verze, zapnutí přepne na rozpracovanou verzi. Klikněte na obdélník: objeví se světlý rámeček se čtyřmi rohy. Tažením plochy jej přesunete, tažením libovolného rohu změníte velikost při zachování proporcí a protějšího rohu. U hran snímku a kamery platí dosavadní limity. Mřížka ani ostatní obrázky se při úpravě jednoho nepřeskupují.

Během tažení se mění jen obrazová ukázka, text zůstává na místě. Po puštění se přepočítá obtékání i pokračování. Pokud by rozložení nemělo místo pro text, úprava se odmítne se zprávou a předchozí stav zůstane. Každý dokončený tah lze vrátit jedním **Zpět**. **Escape** během tažení ho zruší, další Escape nebo nové kliknutí na tlačítko režim vypne. Přepnutí výstupu, snímku nebo změna dokumentu rozpracovaný tah ruší. Úprava streamu jej podle dosavadních pravidel odpojí od sálu; úprava sálu ponechá propojený stream propojený. Živá projekce se mění až přes Použít do projekce.

Zkouška: v úseku 18 posuňte jeden obdélník, druhý má zůstat na svém místě. Zmenšete jej za různé rohy a zkuste Zpět/Znovu i Escape. Pak přepněte na stream. V úsecích 19 a 20 porovnejte pravidla opakování obrázků. Původní dialog Rozložení obrázků zůstává dostupný pro přesné rozměry, propojení a obnovu automatické mřížky.

Pro porovnání v praxi otevřete **Nastavení → Úpravy obrázků** a použijte přepínací tlačítko **Úprava obrázků napřímo**. Zatlačené tlačítko znamená zapnuto. Výchozí stav je zapnutý; dříve výslovně uložená volba zůstává zachovaná. Přepnutí platí hned; pro další spuštění je uložte společným **Uložit defaultně** napravo v Nastavení. Při zapnutí obrázky v rozpracovaném náhledu reagují přímo na kliknutí a tažení; tlačítko Upravit obrázky zůstává viditelné, ale neaktivní, protože zapnutí režimu není potřeba. Escape zruší tah nebo označení, trvalé přímé úpravy nevypne. Vypnutí volby znovu vyžaduje zapnutí režimu tlačítkem Upravit obrázky. Živý náhled nelze přímo upravovat; zapnutí této volby při jeho zobrazení přepne na rozpracovanou verzi.

Při živém náhledu **Escape zastaví projekci** i se zapnutými přímými úpravami obrázků. V rozpracovaném náhledu má přednost zrušení právě taženého obrázku nebo jeho označení; pokud není co rušit, Escape pokračuje do běžného projekčního ovládání. Zkouška: spusťte projekci, klikněte do živého náhledu a stiskněte Escape. Pak v návrhu označte obrázek a ověřte, že první Escape nejdříve zruší označení.

### Jedno společné ukládání výchozích nastavení

Na kartě **Nastavení** je úplně napravo jediné **Uložit defaultně**. Uloží současné hodnoty skupin Zobrazit ovládací tlačítka, Výchozí písmo, Chování lišty a Úpravy obrázků pro budoucí spuštění / nové prezentace. Přepínání viditelnosti, lišty a přímých úprav nejdříve platí jen během aktuálního běhu; bez společného uložení se do příštího spuštění nepřenese. Složky a kamera si zachovávají vlastní dialogy a jejich dosavadní ukládání.

Přepínače viditelnosti ovládacích tlačítek a Úprava obrázků napřímo mají sjednocenou šedou, font, okraje a vzhled pod myší podle přepínače Trvale rozbalit / Přes obsah. Jejich funkce ani společné ukládání se tím nemění.

Obsah skupin pásu karet je vodorovně vystředěný mezi oddělovacími čárami, s drobným odstupem přibližně 5 px po obou stranách. Skupiny se zbytečně neroztahují do volné šířky; delší popisek skupiny může vyžadovat více místa. Tlačítka se neroztahují až k pravé čáře skupiny.

Malé **Uložit** vedle fontu a velikosti nastaví výchozí styl pro nový obsah jen v aktuální prezentaci. Dosavadní texty a jejich formátování se nezmění. Výchozí styl je součástí souboru `.ppres`, takže pro uchování použijte také běžné Soubor → Uložit. Změnu lze vrátit pomocí Zpět. Nová nebo jiná prezentace tuto místní volbu nepřevezme; při otevření použije vlastní uložený styl, nebo u starších souborů globální výchozí písmo.

Zkouška: u úseku 23 změňte velikost ve Výchozím písmu, stiskněte malé Uložit a přidejte nový úsek. Má použít tuto velikost. Po uložení a otevření `.ppres` má volba zůstat. Nová prezentace má používat globální hodnoty. Potom změňte více skupin v Nastavení a použijte společné Uložit defaultně; po restartu mají přetrvat všechny tyto volby.

- **Import PPTX:** potřebuje samostatný vstupní PPTX. V nabídce Soubor vyberte Import PPTX, projděte náhled a konkrétní upozornění a až potom vložte výsledek. Zdejší soubor není zkouškou věrnosti převodu PowerPointu. Volitelné spojení sousedních snímků se stejným nadpisem je funkcí importu.
- **Import starého JSON:** potřebuje soubor původního Presenteru. Použijte Import JSON; očekávejte omezení převodu popsaná importem.
- **Výchozí složky:** Nastavení → Nastavit složky. Zkuste výchozí cesty pro import, otevření, uložení a obrázky. Jde o nastavení aplikace, které tato prezentace nepřepisuje.
- **Monitory, profily a ovládání:** vyzkoušejte skutečné dostupné monitory, profily rozložení, velikosti/viditelnost ovládání a režim pásu karet podle nabídky aplikace. Tyto preference se nepřenášejí v ukázkovém dokumentu.
- Obnovu po pádu ani fyzické chování více monitorů nelze doložit otevřením vzorového souboru. Ukázka není náhradou provozního ověření na cílovém počítači.
