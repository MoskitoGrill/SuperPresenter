# Převod a ověření českých Biblí – 20. 10. 2026

Vstup: uživatelem dodané OpenSong XML CZ_Kb, CZ_Csp, CZ_Cep, CZ_Nbk21 a CZ_Nbk.
Výstup: bible_BKR.json, bible_CSP.json, bible_EKU.json, bible_B21.json a bible_NKB.json.
Původní aplikační JSON jsou zálohované v previous-json/. Vstupní XML nebyla změněna.
Kontrolní součty vstupů, počty knih/kapitol/veršů a jednotlivé opravy včetně původních hodnot jsou v audit.json.
Opakovatelný převod: scripts/import_verified_bibles.py <adresář se vstupy>.

## Ověřené opravy

- BKR Žalm 55: druhý verš označený 23 je verš 24. Text beze změny.
  Zdroj: https://www.bible.com/bible/44/PSA.55.BKR
- BKR Žalm 65: druhý verš označený 13 je verš 14. Text beze změny.
  Zdroj: https://www.ccel.org/bible/czech/ps/ps065.html
  CCEL uvádí dvě souběžná číslování; použito číslování s nadpisem jako veršem 1, které používá vstup.
- B21 Žalm 119: u všech 77 veršů 100–176 poslední číslice čísla přetekla do textu.
  Číslo bylo složeno zpět, číslice odstraněna z textu. Všech 77 výsledných textů bylo
  strojově porovnáno s nezávisle publikovanou B21 na Bible Gateway. Porovnání ignoruje
  mezery, interpunkci, velikost písmen a diakritiku; každý normalizovaný text se shoduje.
  Slovní znění vstupu se neměnilo. Nadpisy hebrejských oddílů z webu se do textu nepřenášejí.
  Zdroj: https://www.biblegateway.com/passage/?search=Psalm+119&version=B21
  Stažená referenční stránka: B21-Psalm119.html.
- B21 Dt 9:24 byl celý přilepený na konec 9:23 jako „24Bouřili…“.
  Text byl rozdělen na existující hranici; žádné slovo nebylo doplněno ani přepsáno.
  Zdroj: https://www.biblegateway.com/passage/?interface=print&search=P%C3%A1t%C3%A1+Moj%C5%BE%C3%AD%C5%A1ova+9&version=B21
- NKB: odstraněno 39 prázdných zástupných knih NULL. Obsahuje pouze Nový zákon:
  27 knih, 260 kapitol, 7 958 neprázdných veršů. Starý zákon nebyl doplňován jiným překladem.

## Technické úpravy

XML převedeno na strukturu kniha → kapitola → verš → text v UTF-8.
Názvy knih převedeny na kanonické názvy aplikace včetně Izajáš → Izaiáš,
Jeremjáš → Jeremiáš, Jakubův → Jakub. Všechny změny názvů jsou vypsány v auditu.
Odstraněny pouze krajní mezery textů, stejně jako při načítání v aplikaci.
ČSP a ČEP nemají žádnou úpravu slovního obsahu ani číslování.

## Rozsah ověření a zachované mezery

Zkontrolovány duplicity, platná čísla, souvislost kapitol, neprázdné texty,
znak náhrady U+FFFD a identifikace všech knih. BibleService načetl všech pět
překladů bez varování a jeho načtené texty byly porovnány se všemi výstupními verši.

V B21 zůstalo 16 mezer v novozákonním číslování (15 kapitol), přesný seznam je v auditu.
Tyto mezery nebyly opravovány ani doplňovány textem jiného překladu. Jejich jednotlivé
ediční zdůvodnění zde není potvrzeno; nejsou důkazem nově vzniklé chyby převodu.
Kontrola neznamená porovnání všech přibližně 133 tisíc veršů s tištěnými vydáními.
Byly ověřeny všechny zásahy do číslování/textu, ostatní slovní obsah zůstává ze vstupů.
