param(
  [string]$RepoPath = "",
  [string]$WslDistro = "",
  [ValidateSet("discovery", "guest-gateway", "install", "revoke")]
  [string]$Mode = "guest-gateway",
  [switch]$EnableAutopilot = $true,
  [switch]$RunPreflight = $true,
  [switch]$Silent = $false,
  [switch]$AssumeConsent = $false
)

$ErrorActionPreference = "Stop"

function Info($msg) {
  Write-Host "[portable-activate] $msg"
}

function Ensure-LogRoot {
  $root = Join-Path $env:ProgramData "RADRILONIUMA\logs"
  New-Item -ItemType Directory -Path $root -Force | Out-Null
  return $root
}

function Resolve-RepoPath([string]$inputPath) {
  if (-not [string]::IsNullOrWhiteSpace($inputPath)) {
    return (Resolve-Path -LiteralPath $inputPath).Path
  }
  $root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
  return (Resolve-Path -LiteralPath $root).Path
}

function Convert-ToWslPath([string]$windowsPath) {
  $winEsc = $windowsPath.Replace("'", "'\\''")
  $cmd = "wslpath -a '$winEsc'"
  $output = if ($WslDistro) {
    & wsl.exe -d $WslDistro bash -lc $cmd
  } else {
    & wsl.exe bash -lc $cmd
  }
  return ($output | Select-Object -First 1).Trim()
}

function Run-WslCommand([string]$cmd, [switch]$IgnoreErrors) {
  if ($WslDistro) {
    & wsl.exe -d $WslDistro bash -lc $cmd
  } else {
    & wsl.exe bash -lc $cmd
  }
  if ($LASTEXITCODE -ne 0 -and -not $IgnoreErrors) {
    throw "WSL command failed: $cmd"
  }
}

function Register-Autopilot([string]$repoWindows) {
  $autopilotScript = Join-Path $PSScriptRoot "register_wsl_autopilot.ps1"
  if (-not (Test-Path -LiteralPath $autopilotScript)) {
    throw "autopilot script not found: $autopilotScript"
  }
  & $autopilotScript -RepoPath $repoWindows -TaskName "LAM_WSL_Autopilot"
  if ($LASTEXITCODE -ne 0) {
    throw "autopilot registration failed"
  }
}

function Run-PreinstallGate([string]$repoWindows, [string]$currentMode) {
  $gateScript = Join-Path $PSScriptRoot "preinstall_security_gate.ps1"
  if (-not (Test-Path -LiteralPath $gateScript)) {
    throw "preinstall gate script not found: $gateScript"
  }
  $gateArgs = @("-ExecutionPolicy", "Bypass", "-File", $gateScript, "-RepoPath", $repoWindows, "-Mode", $currentMode)
  if ($Silent) {
    $gateArgs += "-Silent"
  }
  if ($WslDistro) {
    $gateArgs += @("-WslDistro", $WslDistro)
  }
  & powershell.exe @gateArgs
  if ($LASTEXITCODE -ne 0) {
    throw "preinstall gate failed with code $LASTEXITCODE"
  }
}

function Unregister-Autopilot {
  schtasks /Delete /TN "LAM_WSL_Autopilot" /F | Out-Null
}

function Ask-Consent([string]$currentMode) {
  if (($AssumeConsent -or $Silent) -and $currentMode -eq "install") {
    if ($env:RADR_ALLOW_SILENT_INSTALL -ne "1") {
      throw "silent install blocked by policy. Set RADR_ALLOW_SILENT_INSTALL=1 to allow."
    }
  }
  if ($AssumeConsent -or $Silent) {
    return $true
  }
  Add-Type -AssemblyName PresentationFramework -ErrorAction SilentlyContinue | Out-Null
  $text = @"
RADRILONIUMA portable core is requesting access level:
- mode: $currentMode
- action: open communication gateways to host + external services via WSL
- optional: register autopilot at Windows logon

Continue?
"@
  if ("System.Windows.MessageBox" -as [type]) {
    $result = [System.Windows.MessageBox]::Show($text, "RADRILONIUMA Installer", "YesNo", "Question")
    return $result -eq "Yes"
  }
  $raw = Read-Host "Approve activation? (yes/no)"
  return $raw -match "^(y|yes)$"
}

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
  throw "wsl.exe not found. Install WSL first."
}

$logRoot = Ensure-LogRoot
$logFile = Join-Path $logRoot ("portable_activate_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
Start-Transcript -Path $logFile -Force | Out-Null

try {
  $repoWindows = Resolve-RepoPath $RepoPath
  $repoWsl = Convert-ToWslPath $repoWindows
  Info "repo(windows): $repoWindows"
  Info "repo(wsl): $repoWsl"
  Info "mode=$Mode silent=$Silent"

  if (-not (Ask-Consent $Mode)) {
    Info "user denied activation"
    exit 2
  }

  if ($RunPreflight -and $Mode -ne "revoke") {
    Run-PreinstallGate -repoWindows $repoWindows -currentMode $Mode
  }

  switch ($Mode) {
    "discovery" {
      Run-WslCommand "cd '$repoWsl' && scripts/lam_bridge_stack.sh status" -IgnoreErrors
      Info "discovery complete"
    }
    "guest-gateway" {
      # Guest mode: only communication gateways, no scheduler changes.
      Run-WslCommand "cd '$repoWsl' && LAM_ENABLE_MCP_WATCHDOG=1 LAM_ENABLE_GWS_BRIDGE=1 scripts/lam_bridge_stack.sh start"
      Run-WslCommand "cd '$repoWsl' && scripts/lam_bridge_stack.sh status"
      Info "guest gateway complete"
    }
    "install" {
      Run-WslCommand "cd '$repoWsl' && LAM_ENABLE_MCP_WATCHDOG=1 LAM_ENABLE_GWS_BRIDGE=1 scripts/lam_bridge_stack.sh start"
      Run-WslCommand "cd '$repoWsl' && scripts/lam_bridge_stack.sh status"
      if ($EnableAutopilot) {
        Register-Autopilot -repoWindows $repoWindows
      }
      Info "install complete"
    }
    "revoke" {
      Run-WslCommand "cd '$repoWsl' && scripts/lam_bridge_stack.sh stop" -IgnoreErrors
      Unregister-Autopilot
      Info "revoke complete"
    }
    default {
      throw "unknown mode: $Mode"
    }
  }

  Info "log: $logFile"
}
finally {
  Stop-Transcript | Out-Null
}
