param(
  [string]$RepoPath = "",
  [string]$WslDistro = "",
  [ValidateSet("discovery", "guest-gateway", "install", "revoke")]
  [string]$Mode = "guest-gateway",
  [switch]$RequireSecureBoot = $false,
  [switch]$Silent = $false
)

$ErrorActionPreference = "Stop"

function Info([string]$msg) {
  Write-Host "[preinstall-gate] $msg"
}

function Fail([string]$msg) {
  Write-Error "[preinstall-gate] $msg"
  exit 1
}

function Resolve-RepoPath([string]$inputPath) {
  if (-not [string]::IsNullOrWhiteSpace($inputPath)) {
    return (Resolve-Path -LiteralPath $inputPath).Path
  }
  $root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
  return (Resolve-Path -LiteralPath $root).Path
}

function Ensure-WSL([string]$distro) {
  if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Fail "wsl.exe not found."
  }
  if ($distro) {
    & wsl.exe -d $distro bash -lc "echo wsl-ok" | Out-Null
  } else {
    & wsl.exe bash -lc "echo wsl-ok" | Out-Null
  }
  if ($LASTEXITCODE -ne 0) {
    Fail "WSL check failed."
  }
}

function Ensure-RepoScripts([string]$repo) {
  $required = @(
    "scripts/lam_bridge_stack.sh",
    "scripts/lam_gateway.sh",
    "scripts/test_entrypoint.sh",
    "scripts/windows/portable_activate.ps1"
  )
  foreach ($item in $required) {
    $path = Join-Path $repo $item
    if (-not (Test-Path -LiteralPath $path)) {
      Fail "missing required script: $item"
    }
  }
}

function Ensure-MinDisk([string]$repo) {
  $root = [System.IO.Path]::GetPathRoot($repo)
  $drive = Get-PSDrive -Name $root.Substring(0, 1) -ErrorAction SilentlyContinue
  if (-not $drive) {
    Fail "unable to read drive status for '$root'"
  }
  $freeGB = [math]::Round($drive.Free / 1GB, 2)
  $minGB = if ($Mode -eq "install") { 3 } else { 1 }
  Info "disk_free_gb=$freeGB required_gb=$minGB drive=$($drive.Name):"
  if ($freeGB -lt $minGB) {
    Fail "insufficient disk space: ${freeGB}GB < ${minGB}GB."
  }
}

function Test-SecureBoot {
  try {
    $sb = Confirm-SecureBootUEFI -ErrorAction Stop
    return [bool]$sb
  } catch {
    return $false
  }
}

function Ensure-SecureBootIfRequired {
  $envRequired = $env:RADR_REQUIRE_SECURE_BOOT -eq "1"
  if (-not ($RequireSecureBoot -or $envRequired)) {
    return
  }
  if (-not (Test-SecureBoot)) {
    Fail "secure boot requirement not satisfied."
  }
  Info "secure_boot=enabled"
}

function Ensure-AdminIfInstall {
  if ($Mode -ne "install") {
    return
  }
  $current = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  if (-not $current.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Fail "install mode requires elevated PowerShell session."
  }
}

$repo = Resolve-RepoPath $RepoPath
Info "mode=$Mode repo=$repo silent=$Silent"

Ensure-WSL $WslDistro
Ensure-RepoScripts $repo
Ensure-MinDisk $repo
Ensure-SecureBootIfRequired
Ensure-AdminIfInstall

Info "gate=pass"
exit 0
