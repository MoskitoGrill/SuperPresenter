# Etapa 5 — čekající uživatelské ověření (9. 10. 2026)

Stav: ČEKÁ. Tyto kontroly nebyly provedeny automatickou diagnostikou.
Použijte ZIP `dist/3.0.0-20261009-140605/SuperPresenter-3.0.0-win64.zip`.
Zapisujte datum, Windows, GPU, rozlišení/DPI, model projektoru, kabel,
režim monitorů, použitý profil a výsledek každého kroku.

## Izolace dat na cílovém PC

Rozbalte celý ZIP do nové zapisovatelné složky, například
`C:\Users\Public\Documents\SuperPresenter-test-3.0.0`. Nepoužívejte ostrou
distribuci ani ostré písně. Upravujte pouze dodané kopie. V PowerShellu:

```powershell
$testRoot = 'C:\Users\Public\Documents\SuperPresenter-test-3.0.0'
$env:APPDATA = Join-Path $testRoot 'test-appdata'
$testExe = Join-Path $testRoot 'SuperPresenter-v3\SuperPresenter.exe'
New-Item -ItemType Directory -Path $env:APPDATA -Force | Out-Null
$testProcess = Start-Process -FilePath $testExe -WorkingDirectory $env:TEMP -PassThru
```

APPDATA je změněné pouze v tomto PowerShellu a jeho potomcích. Všechny další
testovací starty provádějte z něj. Po skončení PowerShell zavřete. Zálohu
ostrých dat a původního `%APPDATA%\SuperPresenter` uchovejte před přechodem
na produkční provoz. Kopii s prázdným názvem `songs/.xml` neupravujte kvůli testu.

## Projektor a odpojení/připojení — ČEKÁ

1. Připojte projektor, ve Windows nastavte rozšířenou plochu. V aplikaci
   přiřaďte skutečný monitor a spusťte sálový stacionární styl; podle sestavy
   přidejte streamový výstup. Ověřte čitelnost, diakritiku, obrázky, fullscreen
   a hranice obrazu. Přepněte alespoň 20krát vpřed/zpět a mezi dvěma písněmi.
2. Při promítání odpojte kabel projektoru, počkejte 10 sekund. Zaznamenejte
   chování aplikace a zbývajícího výstupu. Hlavní okno musí zůstat dostupné,
   bez pádu, zamrznutí a opakovaných chyb. Ověřte Stop a následný start na
   dostupném monitoru; nepovažujte zmizení odpojeného obrazu za chybu.
3. Připojte kabel, počkejte 10 sekund, zkontrolujte seznam monitorů a přiřazení
   profilu; podle potřeby znovu vyberte monitor. Spusťte projekci a ověřte
   správný obsah i fullscreen na zamýšleném výstupu. Neočekávejte automatické
   obnovení projekce, pokud jej aplikace nenabízí.
4. Celý cyklus opakujte pětkrát, potom pětkrát s legacy sálovým stylem.
   Zkuste také odpojení při zastavené projekci a připojení před dalším startem.
5. Upravte a uložte kopii písně při projekci. Běžící snímek musí zůstat stabilní;
   po stop/start ověřte uloženou změnu. Zavřete aplikaci při promítání:
   všechny výstupy musí zmizet a proces skončit. Spusťte ji znovu.

## Čtyřhodinový provoz — ČEKÁ

1. Na cílové sestavě spusťte projekci s běžným playlistem, alespoň dvěma
   písněmi s diakritikou, obrázkem/QR a obvyklou kombinací sál/stream.
   Zaznamenejte výchozí paměť po pěti minutách zahřátí.
2. Každých 15 minut přepněte 20krát vpřed/zpět, změňte píseň, otevřete a
   zavřete editor projekce a řazení. Každých 30 minut proveďte stop/start.
   Po první a třetí hodině upravte a uložte testovací píseň. Dvě hodiny
   používejte stacionární styly a dvě hodiny legacy styly; pro srovnání paměti
   vždy zapište aktuální styly a stav spuštěno/zastaveno.
3. V témže PowerShellu každých 15 minut uložte vzorek:

```powershell
$testProcess.Refresh()
[pscustomobject]@{
    Time = (Get-Date).ToString('o')
    PID = $testProcess.Id
    WorkingSetMiB = [math]::Round($testProcess.WorkingSet64 / 1MB, 2)
    PrivateMiB = [math]::Round($testProcess.PrivateMemorySize64 / 1MB, 2)
    Handles = $testProcess.HandleCount
    Responding = $testProcess.Responding
} | Export-Csv (Join-Path $testRoot 'runtime.csv') -Append -NoTypeInformation
```

4. Zapisujte také odezvu tlačítek a případné zpoždění obrazu. Každou hodinu
   zkopírujte logy z `test-appdata\SuperPresenter\logs` do označené složky;
   zejména `standalone-console.log` se při dalším startu přepisuje.
5. Po čtyřech hodinách zastavte projekci, vyčkejte minutu, pořiďte poslední
   vzorek a aplikaci normálně zavřete. Ověřte ukončení procesu i všech výstupů.
   Projde pouze bez nečekaných výjimek, Tcl/Tk chyb, pádu či ztráty ovládání.
   Soustavný růst private memory/handles při srovnatelném stavu po zahřátí
   označte k vyšetření; krátkodobé kolísání samo o sobě nedokazuje únik.

## Další kontroly se součinností — ČEKÁ

- Čistý druhý Windows PC bez Pythonu: rozbalit tentýž ZIP, spustit
  `& $testExe --smoke-test (Join-Path $testRoot 'target-smoke.json')`, ověřit
  `ok: true` a potom běžné spuštění a zavření.
- Skutečné připnutí na hlavní panel: připnout testovací EXE a ověřit opětovný
  start, cestu a ikonu. Start z připnutí nedědí izolované APPDATA; provést
  v samostatném testovacím Windows účtu.
- Bitfocus/Stream Deck: v testovacím účtu a kopii konfigurace zadat úplnou
  cestu testovacího EXE, bez argumentů; stisknout skutečné tlačítko a ověřit
  jediný zamýšlený start. Zaznamenat cestu a výsledek, nepřepínat ostrou akci.
- Antivirus na cílovém PC: prověřit konkrétní ZIP a rozbalenou složku,
  zapsat produkt, verzi, datum a výsledek. Nevypínat ochranu.

Po provedení doplňte skutečné výsledky, CSV a logy do předání etapy 5.
Finální ověření zůstává otevřené do dokončení požadovaných reálných kontrol.
