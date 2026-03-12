param(
  [Parameter(Mandatory = $true)]
  [string]$TargetDrive,
  [string]$RepoPath = "",
  [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

function Info([string]$msg) {
  Write-Host "[portable-core] $msg"
}

function Resolve-RepoPath([string]$inputPath) {
  if (-not [string]::IsNullOrWhiteSpace($inputPath)) {
    return (Resolve-Path -LiteralPath $inputPath).Path
  }
  $root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
  return (Resolve-Path -LiteralPath $root).Path
}

function Normalize-DriveRoot([string]$drive) {
  $trimmed = $drive.Trim()
  if ($trimmed -match '^[A-Za-z]$') {
    return ($trimmed.ToUpper() + ":\")
  }
  if ($trimmed -match '^[A-Za-z]:$') {
    return ($trimmed.ToUpper() + "\")
  }
  if ($trimmed -match '^[A-Za-z]:\\$') {
    return $trimmed.ToUpper()
  }
  throw "invalid TargetDrive format '$drive'. Use D, D:, or D:\"
}

function Copy-PortableSet([string]$repo, [string]$targetRoot) {
  $portableRoot = Join-Path $targetRoot "RADRILONIUMA_OS"
  if ((Test-Path -LiteralPath $portableRoot) -and -not $Force) {
    throw "target already exists: $portableRoot (use -Force to overwrite files)"
  }

  New-Item -ItemType Directory -Path $portableRoot -Force | Out-Null

  $items = @(
    "apps",
    "deploy",
    "infra",
    "scripts",
    "README.md"
  )

  foreach ($item in $items) {
    $src = Join-Path $repo $item
    if (-not (Test-Path -LiteralPath $src)) {
      continue
    }
    $dst = Join-Path $portableRoot $item
    if (Test-Path -LiteralPath $src -PathType Container) {
      robocopy $src $dst /MIR /R:1 /W:1 /NFL /NDL /NP /NJH /NJS /XF "*.pyc" /XD "__pycache__" ".pytest_cache" | Out-Null
      if ($LASTEXITCODE -ge 8) {
        throw "robocopy failed for $item with code $LASTEXITCODE"
      }
    } else {
      Copy-Item -LiteralPath $src -Destination $dst -Force
    }
  }

  $launcher = Join-Path $portableRoot "Start_RADRILONIUMA_OS.cmd"
  @"
@echo off
setlocal
set ROOT=%~dp0
powershell.exe -ExecutionPolicy Bypass -File "%ROOT%scripts\windows\installer_wizard.ps1" -RepoPath "%ROOT%"
endlocal
"@ | Set-Content -LiteralPath $launcher -Encoding ASCII -NoNewline

  $manifest = Join-Path $portableRoot "portable_manifest.txt"
  @(
    "RADRILONIUMA OS portable core"
    "built_utc=$(Get-Date -AsUTC -Format s)Z"
    "source_repo=$repo"
    "target_root=$portableRoot"
    "launcher=Start_RADRILONIUMA_OS.cmd"
  ) | Set-Content -LiteralPath $manifest -Encoding ASCII

  return $portableRoot
}

$repo = Resolve-RepoPath $RepoPath
$driveRoot = Normalize-DriveRoot $TargetDrive

if (-not (Test-Path -LiteralPath $driveRoot)) {
  throw "drive not found: $driveRoot"
}

$resultRoot = Copy-PortableSet -repo $repo -targetRoot $driveRoot
Info "portable_core_ready=$resultRoot"
exit 0
