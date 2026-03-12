param(
  [string]$RepoPath = "",
  [ValidateSet("start", "stop", "status", "errors", "watch")]
  [string]$Action = "status",
  [ValidateSet("quick", "standard", "full")]
  [string]$Mode = "standard"
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

switch ($Action) {
  "start" { $cmd = "cd '$repo' && scripts/test_background_daemon.sh start --mode $Mode" }
  "stop" { $cmd = "cd '$repo' && scripts/test_background_daemon.sh stop" }
  "status" { $cmd = "cd '$repo' && scripts/test_background_daemon.sh status" }
  "errors" { $cmd = "cd '$repo' && scripts/test_background_daemon.sh errors" }
  "watch" { $cmd = "cd '$repo' && scripts/test_background_daemon.sh watch" }
}

& wsl.exe bash -lc $cmd
if ($LASTEXITCODE -ne 0) {
  throw "test background daemon action failed: $Action"
}
