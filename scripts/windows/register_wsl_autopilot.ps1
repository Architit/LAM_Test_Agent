param(
  [string]$RepoPath = "",
  [string]$TaskName = "LAM_WSL_Autopilot"
)

$ErrorActionPreference = "Stop"

function Resolve-RepoPath {
  param([string]$InputPath)
  if (-not [string]::IsNullOrWhiteSpace($InputPath)) {
    return (Resolve-Path -LiteralPath $InputPath).Path
  }

  $cwd = (Get-Location).Path
  if ($cwd -match "^\\\\wsl\\") {
    return $cwd
  }

  throw "RepoPath is required when not running from a WSL UNC path."
}

$repo = Resolve-RepoPath -InputPath $RepoPath

$cmd = "cd '$repo' && scripts/lam_bridge_stack.sh start"
$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "bash -lc \"$cmd\""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

Register-ScheduledTask \
  -TaskName $TaskName \
  -Action $action \
  -Trigger $trigger \
  -Settings $settings \
  -Description "LAM bridge stack autopilot for WSL" \
  -Force | Out-Null

Write-Host "[wsl-autopilot] task registered: $TaskName"
Write-Host "[wsl-autopilot] repo: $repo"
Write-Host "[wsl-autopilot] trigger: AtLogOn"
Write-Host "[wsl-autopilot] check: schtasks /Query /TN $TaskName /V /FO LIST"
