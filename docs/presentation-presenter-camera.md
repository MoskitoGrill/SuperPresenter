# Nastavení prostoru pro kameru streamu

Otevřete **Nastavení → Složky a kamera → Kamera streamu…**.

- **Zleva / Shora** určují začátek oblasti v procentech šířky/výšky snímku.
- **Šířka / Výška** určují velikost oblasti. U pravého okraje zůstává pravá hrana a šířka se mění doleva, u levého doprava. U spodního okraje se výška mění nahoru, u horního dolů. Volně umístěná kamera zachovává střed a mění se rovnoměrně na obě strany, nejvýše k nejbližšímu okraji. Posuvníky nepustí obdélník mimo snímek; při změně velikosti se automaticky přepočte také poloha.
- **Odstup textu** přidává bezpečné místo kolem kamery. Používá stejnou normalizovanou geometrii jako vlastní dělení textu (procento šířky vodorovně a výšky svisle).
- **Načíst výchozí** vrátí posuvníky na hodnoty uložené v aplikaci. Samo nezmění prezentaci.

Náhled ukazuje zkušební text v aktuálním poměru streamu 16:9 nebo 4:3. Růžová čára označuje přesnou oblast kamery, přerušovaná žlutá její bezpečný odstup a tyrkysová okraj celého snímku. První ukázkový snímek používá stejné měření a dělení textu jako aplikace. Při extrémně velké oblasti, kde ukázkový text nelze vůbec vysázet, zůstávají dostupné geometrické okraje.

## Zkušební projekce

1. Zastavte běžnou prezentaci. Zkušební projekce je samostatná a nesmí překrýt živou prezentaci.
2. Vyberte monitor ukázky. Přednastaví se monitor vybraný pro stream v aplikaci; volba v tomto dialogu ho nepřepisuje.
3. Pro výstup do streamu vyberte jeho monitor a zapněte **Celá obrazovka**. Pokud máte jediný monitor, ponechte test v okně. Celá obrazovka na monitoru s kalibračním dialogem je odmítnuta, aby zůstaly dostupné posuvníky.
4. Klikněte na **Promítnout ukázku**. V běžném streamovém skládání sledujte souběh růžového okraje s vaší kamerou a upravujte posuvníky. Ty mění lokální náhled i testovací výstup; nejde o připojování kamery do aplikace.
5. **Ukončit ukázku** nebo Escape ve zkušebním projekčním okně test ukončí. Zavření nastavovacího dialogu zavře také jeho zkušební výstup. Odpojení monitoru či změna jeho geometrie test zastaví.

## Jednorázové a výchozí hodnoty

- **Použít pro prezentaci** změní pouze rozpracovanou prezentaci. Lze vrátit přes Zpět. Při uložení `.ppres` se geometrie přenese s prezentací.
- **Použít a uložit výchozí** provede totéž a uloží hodnoty pro nové prezentace, také po restartu. Výchozí hodnoty platí i pro starý JSON import, který původní geometrii neobsahuje; PPTX vložený do prezentace používá její aktuální nastavení.
- Otevření existujícího `.ppres` respektuje geometrii uloženou v tomto souboru a nenahrazuje ji aplikačním defaultem.
- **Zavřít** bez použití zahodí rozpracované posuvníky. Dokud nestisknete Použít, nemění se dokument, historie ani uložené preference.
- Pokud běží živá session, použití mění pouze návrh; skutečné výstupy aktualizujte běžným **Použít do projekce**. Samotná testovací projekce je během živé session zablokovaná.
- Před použitím se ověří přepočet celé aktuální prezentace. Pokud se text nebo obrázky nevejdou, změna se neprovede a dialog zůstane k opravě. Při chybě ukládání výchozího nastavení zůstávají původní hodnoty i prezentace.

## Ruční ověření

Vyzkoušejte posun a změnu rozměrů v obou poměrech stran; porovnejte lokální a testovací okraj s reálnou kamerou ve streamovém skládání. Ověřte opakovaný start/stop, Escape, zavření dialogu a odpojení výstupního monitoru. Potom zvolte jednorázové použití a Zpět, trvalé použití a novou prezentaci po restartu, uložení/otevření `.ppres` a přepočet dlouhého textu a obrázků. Změna kamery může změnit počet společných pokračování pro sál i stream; obsah obou zůstává společný.

Automatické testy `python -B -m unittest tests.presentationpresenter.test_camera_settings -v` nenahrazují fyzickou kontrolu dvou externích monitorů, smíšeného DPI ani skutečného streamového skládání.
