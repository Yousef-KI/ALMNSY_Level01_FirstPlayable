param([string]$EngineRoot = '')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$ProjectFile = Join-Path $ProjectRoot 'ALMNSY_Level01.uproject'
$ProjectData = Get-Content -LiteralPath $ProjectFile -Raw | ConvertFrom-Json
if (-not $EngineRoot) {
    $Candidates = @("C:\Program Files\Epic Games\UE_$($ProjectData.EngineAssociation)", "D:\Epic Games\UE_$($ProjectData.EngineAssociation)")
    $RegPath = "HKLM:\SOFTWARE\EpicGames\Unreal Engine\$($ProjectData.EngineAssociation)"
    if (Test-Path $RegPath) { $Candidates = @((Get-ItemProperty $RegPath).InstalledDirectory) + $Candidates }
    foreach ($Candidate in $Candidates) {
        if ($Candidate -and (Test-Path (Join-Path $Candidate 'Engine\Binaries\Win64\UnrealEditor.exe'))) { $EngineRoot=$Candidate; break }
    }
}
if (-not $EngineRoot) { throw 'UE 5.8 was not found. Supply -EngineRoot "your UE_5.8 directory".' }
$Build = Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat'
$Editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
$Generator = Join-Path $PSScriptRoot 'Build_ALMNSY_v03.py'
if (-not (Test-Path $Build) -or -not (Test-Path $Editor)) { throw 'Invalid Unreal Engine directory.' }
Write-Host 'Building ALMNSY_Level01Editor. Close Unreal Editor first.'
& $Build ALMNSY_Level01Editor Win64 Development "-Project=$ProjectFile" -WaitMutex -NoHotReloadFromIDE
if ($LASTEXITCODE -ne 0) { throw "Build failed ($LASTEXITCODE). The editor was not launched." }
Write-Host 'Opening separate v03. Existing v02 assets and startup-map settings are preserved.'
& $Editor $ProjectFile "-ExecutePythonScript=$Generator" -log
