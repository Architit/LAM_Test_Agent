param(
  [string]$RepoPath = "",
  [ValidateSet("quick", "standard", "full")]
  [string]$Mode = "standard",
  [int]$MaxTicks = 0,
  [int]$TickTimeoutSec = 120
)

$ErrorActionPreference = "Stop"

function Resolve-RepoPath {
  param([string]$InputPath)
  if (-not [string]::IsNullOrWhiteSpace($InputPath)) {
    return (Resolve-Path -LiteralPath $InputPath).Path
  }
  $cwd = (Get-Location).Path
  if ($cwd -match "^\\\\wsl\\") { return $cwd }
  throw "RepoPath is required when not running from WSL UNC path."
}

$repo = Resolve-RepoPath -InputPath $RepoPath
$modeArg = "--$Mode"
$cmd = "cd '$repo' && LAM_TEST_MAX_TICKS=$MaxTicks LAM_TEST_TICK_TIMEOUT_SEC=$TickTimeoutSec scripts/test_microtick_orchestrator.sh $modeArg"

Write-Host "[microtick] repo: $repo"
Write-Host "[microtick] mode: $Mode max_ticks=$MaxTicks timeout=$TickTimeoutSec"

& wsl.exe bash -lc $cmd
if ($LASTEXITCODE -ne 0) {
  throw "microtick cascade failed"
}

Write-Host "[microtick] completed"
