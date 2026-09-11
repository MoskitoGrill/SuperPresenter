$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) {
    $compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework/v4.0.30319/csc.exe'
}
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Chybi kompilator .NET Framework 4.x.' }
$icon = Join-Path $projectRoot 'images/ikona.ico'
if (-not (Test-Path -LiteralPath $icon)) {
    $icon = Join-Path $projectRoot 'images/launcher-default.ico'
    if (-not (Test-Path -LiteralPath $icon)) {
        Add-Type -AssemblyName System.Drawing
        $stream = [System.IO.File]::Create($icon)
        try { [System.Drawing.SystemIcons]::Application.Save($stream) } finally { $stream.Dispose() }
    }
}
& $compiler /nologo /target:winexe /optimize+ /reference:System.Windows.Forms.dll "/win32icon:$icon" "/out:$(Join-Path $projectRoot 'spustit_super_presenter.exe')" (Join-Path $PSScriptRoot 'WindowsLauncher.cs')
if ($LASTEXITCODE -ne 0) { throw 'Sestaveni EXE selhalo.' }
Write-Host 'EXE bylo sestaveno.'

