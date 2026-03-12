param(
  [string]$RepoPath = "",
  [ValidateSet("quick", "standard", "full")]
  [string]$Mode = "standard",
  [switch]$OpenTabs = $true
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
$cmd = "cd '$repo' && scripts/test_phase_cascade.sh $modeArg"

Write-Host "[test-cascade] repo: $repo"
Write-Host "[test-cascade] mode: $Mode"

& wsl.exe bash -lc $cmd
if ($LASTEXITCODE -ne 0) {
  throw "phase cascade failed"
}

if ($OpenTabs -and (Get-Command wt.exe -ErrorAction SilentlyContinue)) {
  $tailCmd = "cd '$repo' && latest=`$(ls -1dt .gateway/test_runs/* | head -n1) && echo summary=`$latest/summary.json && cat `$latest/summary.json"
  Start-Process wt.exe "new-tab --title TEST_SUMMARY wsl.exe bash -lc `"$tailCmd`"" | Out-Null
}

Write-Host "[test-cascade] completed"
