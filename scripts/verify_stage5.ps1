param([Parameter(Mandatory=$true)][string]$ReleaseDirectory)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$release = (Resolve-Path -LiteralPath $ReleaseDirectory).Path
$checks = Join-Path $project 'release-checks/stage5-20261009'
New-Item -ItemType Directory -Path $checks -Force | Out-Null
$app = Join-Path $release 'SuperPresenter-v3'
$zip = Join-Path $release 'SuperPresenter-3.0.0-win64.zip'
$manifest = Get-Content -LiteralPath (Join-Path $app 'release.json') -Raw | ConvertFrom-Json
$verified = 0
foreach ($entry in $manifest.sha256.PSObject.Properties) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $app $entry.Name) -Algorithm SHA256).Hash
    if ($actual -ne $entry.Value) { throw "Manifest mismatch: $($entry.Name)" }
    $verified++
}
function Invoke-Smoke([string]$Exe, [string]$Report) {
    $proc = Start-Process -FilePath $Exe -ArgumentList @('--smoke-test', ('"' + $Report + '"')) -WorkingDirectory $env:TEMP -WindowStyle Hidden -PassThru
    if (-not $proc.WaitForExit(60000)) { throw 'Smoke test exceeded 60 seconds' }
    if ($proc.ExitCode -ne 0) { throw "Smoke failed ($($proc.ExitCode)): $Report" }
    $result = Get-Content -LiteralPath $Report -Raw | ConvertFrom-Json
    if (-not $result.ok) { throw "Smoke report failed: $Report" }
}
Invoke-Smoke (Join-Path $app 'SuperPresenter.exe') (Join-Path $checks 'packaged.json')
$portable = Join-Path $checks 'Přenos s mezerami a diakritikou'
if (Test-Path -LiteralPath $portable) { throw 'Portable test directory already exists; preserve previous evidence.' }
Expand-Archive -LiteralPath $zip -DestinationPath $portable
$portableApp = Join-Path $portable 'SuperPresenter-v3'
$originalPath = $env:PATH
$originalAppdata = $env:APPDATA
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:APPDATA = Join-Path $checks 'isolated-appdata'
    Invoke-Smoke (Join-Path $portableApp 'SuperPresenter.exe') (Join-Path $checks 'portable.json')
    $proc = Start-Process -FilePath (Join-Path $portableApp 'SuperPresenter.exe') -WorkingDirectory $env:TEMP -WindowStyle Hidden -PassThru
    $title = ''
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 250
        $proc.Refresh()
        if ($proc.HasExited) { throw 'Normal launch exited before opening window' }
        if ($proc.MainWindowTitle -eq 'SuperPresenter 3.0.0') { $title = $proc.MainWindowTitle; break }
    }
    if (-not $title) { throw 'Expected main window did not open' }
    if (-not $proc.CloseMainWindow()) { throw 'WM_CLOSE request failed' }
    if (-not $proc.WaitForExit(15000)) { throw 'Normal close exceeded 15 seconds' }
    if ($proc.ExitCode -ne 0) { throw "Normal close failed: $($proc.ExitCode)" }
    $console = Join-Path $env:APPDATA 'SuperPresenter/logs/standalone-console.log'
    if ((Test-Path -LiteralPath $console) -and (Get-Content -LiteralPath $console -Raw)) { throw 'Normal launch wrote unexpected console diagnostics' }
    [ordered]@{
        ok = $true; release = $release; manifest_files_verified = $verified
        zip_bytes = (Get-Item -LiteralPath $zip).Length
        zip_sha256 = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
        exe_sha256 = (Get-FileHash -LiteralPath (Join-Path $app 'SuperPresenter.exe') -Algorithm SHA256).Hash
        portable_app = $portableApp; launch_working_directory = $env:TEMP
        launch_path = $env:PATH; main_window_title = $title; normal_close_exit = $proc.ExitCode
        isolated_appdata = $env:APPDATA; git_commit = $manifest.git_commit; git_dirty = $manifest.git_dirty
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $checks 'verification.json') -Encoding UTF8
} finally {
    $env:PATH = $originalPath
    $env:APPDATA = $originalAppdata
}
