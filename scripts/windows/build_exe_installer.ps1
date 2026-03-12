param(
  [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Join-Path $PSScriptRoot "dist"
}

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$launcherCs = Join-Path $PSScriptRoot "RADRILONIUMA_Installer_Launcher.cs"
$exePath = Join-Path $OutDir "RADRILONIUMA_Installer.exe"
$activatePs1 = Join-Path $PSScriptRoot "portable_activate.ps1"
$wizardPs1 = Join-Path $PSScriptRoot "installer_wizard.ps1"
$autopilotPs1 = Join-Path $PSScriptRoot "register_wsl_autopilot.ps1"
$preflightPs1 = Join-Path $PSScriptRoot "preinstall_security_gate.ps1"
$preparePortablePs1 = Join-Path $PSScriptRoot "prepare_portable_core.ps1"

if (-not (Test-Path -LiteralPath $launcherCs)) { throw "missing: $launcherCs" }
if (-not (Test-Path -LiteralPath $activatePs1)) { throw "missing: $activatePs1" }
if (-not (Test-Path -LiteralPath $wizardPs1)) { throw "missing: $wizardPs1" }
if (-not (Test-Path -LiteralPath $autopilotPs1)) { throw "missing: $autopilotPs1" }
if (-not (Test-Path -LiteralPath $preflightPs1)) { throw "missing: $preflightPs1" }
if (-not (Test-Path -LiteralPath $preparePortablePs1)) { throw "missing: $preparePortablePs1" }

$csc = Get-Command csc.exe -ErrorAction SilentlyContinue
if (-not $csc) {
  throw "csc.exe not found. Install .NET build tools / Visual Studio Build Tools."
}

& $csc.Source /target:winexe /nologo /out:$exePath /reference:System.Windows.Forms.dll /reference:System.Drawing.dll $launcherCs
if ($LASTEXITCODE -ne 0) { throw "csc.exe failed" }

Copy-Item -LiteralPath $activatePs1 -Destination (Join-Path $OutDir "portable_activate.ps1") -Force
Copy-Item -LiteralPath $wizardPs1 -Destination (Join-Path $OutDir "installer_wizard.ps1") -Force
Copy-Item -LiteralPath $autopilotPs1 -Destination (Join-Path $OutDir "register_wsl_autopilot.ps1") -Force
Copy-Item -LiteralPath $preflightPs1 -Destination (Join-Path $OutDir "preinstall_security_gate.ps1") -Force
Copy-Item -LiteralPath $preparePortablePs1 -Destination (Join-Path $OutDir "prepare_portable_core.ps1") -Force

Write-Host "[build-exe] created: $exePath"
Write-Host "[build-exe] bundle files:"
Get-ChildItem -Path $OutDir | ForEach-Object { Write-Host " - $($_.Name)" }
