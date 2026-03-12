param(
  [string]$RepoPath = "",
  [string]$WslDistro = ""
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function New-Label([string]$text, [int]$x, [int]$y, [int]$w, [int]$h) {
  $l = New-Object System.Windows.Forms.Label
  $l.Text = $text
  $l.Left = $x
  $l.Top = $y
  $l.Width = $w
  $l.Height = $h
  return $l
}

function Resolve-RepoPath([string]$inputPath) {
  if (-not [string]::IsNullOrWhiteSpace($inputPath)) {
    return (Resolve-Path -LiteralPath $inputPath).Path
  }
  $root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
  return (Resolve-Path -LiteralPath $root).Path
}

function Run-Activation(
  [System.Windows.Forms.TextBox]$logBox,
  [string]$mode,
  [bool]$enableAutopilot,
  [bool]$silentMode,
  [string]$repoPath,
  [string]$wslDistro
) {
  $script = Join-Path $PSScriptRoot "portable_activate.ps1"
  if (-not (Test-Path -LiteralPath $script)) {
    $logBox.AppendText("[wizard] missing script: $script`r`n")
    return 2
  }

  $args = @("-ExecutionPolicy", "Bypass", "-File", $script, "-Mode", $mode, "-RepoPath", $repoPath)
  if (-not [string]::IsNullOrWhiteSpace($wslDistro)) {
    $args += @("-WslDistro", $wslDistro)
  }
  if ($enableAutopilot) {
    $args += "-EnableAutopilot"
  }
  if ($silentMode) {
    $args += @("-Silent", "-AssumeConsent")
  }

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = "powershell.exe"
  $psi.Arguments = [string]::Join(" ", ($args | ForEach-Object {
    if ($_ -match "^[A-Za-z0-9_\-.:\\/]+$") { $_ } else { '"' + ($_ -replace '"', '\"') + '"' }
  }))
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()
  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  $p.WaitForExit()

  if ($stdout) { $logBox.AppendText($stdout + "`r`n") }
  if ($stderr) { $logBox.AppendText($stderr + "`r`n") }
  $logBox.AppendText("[wizard] exit_code=$($p.ExitCode)`r`n")
  return $p.ExitCode
}

function Run-SubScript(
  [System.Windows.Forms.TextBox]$logBox,
  [string]$scriptFile,
  [string[]]$arguments
) {
  $script = Join-Path $PSScriptRoot $scriptFile
  if (-not (Test-Path -LiteralPath $script)) {
    $logBox.AppendText("[wizard] missing script: $script`r`n")
    return 2
  }
  $args = @("-ExecutionPolicy", "Bypass", "-File", $script) + $arguments
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = "powershell.exe"
  $psi.Arguments = [string]::Join(" ", ($args | ForEach-Object {
    if ($_ -match "^[A-Za-z0-9_\-.:\\/]+$") { $_ } else { '"' + ($_ -replace '"', '\"') + '"' }
  }))
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()
  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  $p.WaitForExit()

  if ($stdout) { $logBox.AppendText($stdout + "`r`n") }
  if ($stderr) { $logBox.AppendText($stderr + "`r`n") }
  $logBox.AppendText("[wizard] $scriptFile exit_code=$($p.ExitCode)`r`n")
  return $p.ExitCode
}

$repo = Resolve-RepoPath $RepoPath

$form = New-Object System.Windows.Forms.Form
$form.Text = "RADRILONIUMA OS Installer"
$form.StartPosition = "CenterScreen"
$form.Width = 860
$form.Height = 640
$form.BackColor = [System.Drawing.Color]::FromArgb(18, 22, 28)
$form.ForeColor = [System.Drawing.Color]::FromArgb(230, 236, 245)

$title = New-Label "RADRILONIUMA OS" 20 16 420 34
$title.Font = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($title)

$subtitle = New-Label "Portable Gateway & Installer Wizard" 22 50 420 22
$subtitle.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Regular)
$form.Controls.Add($subtitle)

$stepLabel = New-Label "Step 1: Select mode" 22 88 220 24
$stepLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($stepLabel)

$modeCombo = New-Object System.Windows.Forms.ComboBox
$modeCombo.Left = 22
$modeCombo.Top = 116
$modeCombo.Width = 250
$modeCombo.DropDownStyle = "DropDownList"
[void]$modeCombo.Items.Add("discovery")
[void]$modeCombo.Items.Add("guest-gateway")
[void]$modeCombo.Items.Add("install")
[void]$modeCombo.Items.Add("revoke")
$modeCombo.SelectedItem = "guest-gateway"
$form.Controls.Add($modeCombo)

$autopilotCheck = New-Object System.Windows.Forms.CheckBox
$autopilotCheck.Left = 290
$autopilotCheck.Top = 118
$autopilotCheck.Width = 250
$autopilotCheck.Text = "Enable Windows logon autopilot"
$autopilotCheck.Checked = $true
$form.Controls.Add($autopilotCheck)

$silentCheck = New-Object System.Windows.Forms.CheckBox
$silentCheck.Left = 550
$silentCheck.Top = 118
$silentCheck.Width = 220
$silentCheck.Text = "Silent (/S semantics)"
$silentCheck.Checked = $false
$form.Controls.Add($silentCheck)

$repoLabel = New-Label "Repo path:" 22 152 120 20
$form.Controls.Add($repoLabel)

$repoBox = New-Object System.Windows.Forms.TextBox
$repoBox.Left = 22
$repoBox.Top = 174
$repoBox.Width = 810
$repoBox.Text = $repo
$form.Controls.Add($repoBox)

$wslLabel = New-Label "WSL distro (optional):" 22 204 180 20
$form.Controls.Add($wslLabel)

$wslBox = New-Object System.Windows.Forms.TextBox
$wslBox.Left = 22
$wslBox.Top = 226
$wslBox.Width = 320
$wslBox.Text = $WslDistro
$form.Controls.Add($wslBox)

$portableLabel = New-Label "Portable target drive (D:/E:/F:):" 370 204 260 20
$form.Controls.Add($portableLabel)

$portableBox = New-Object System.Windows.Forms.TextBox
$portableBox.Left = 370
$portableBox.Top = 226
$portableBox.Width = 120
$portableBox.Text = "D:"
$form.Controls.Add($portableBox)

$step2 = New-Label "Step 2: Execute and monitor" 22 262 240 24
$step2.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($step2)

$runBtn = New-Object System.Windows.Forms.Button
$runBtn.Left = 22
$runBtn.Top = 292
$runBtn.Width = 170
$runBtn.Height = 34
$runBtn.Text = "Run Selected Mode"
$runBtn.BackColor = [System.Drawing.Color]::FromArgb(33, 112, 201)
$runBtn.ForeColor = [System.Drawing.Color]::White
$form.Controls.Add($runBtn)

$rollbackBtn = New-Object System.Windows.Forms.Button
$rollbackBtn.Left = 206
$rollbackBtn.Top = 292
$rollbackBtn.Width = 170
$rollbackBtn.Height = 34
$rollbackBtn.Text = "Rollback (Revoke)"
$rollbackBtn.BackColor = [System.Drawing.Color]::FromArgb(166, 63, 63)
$rollbackBtn.ForeColor = [System.Drawing.Color]::White
$form.Controls.Add($rollbackBtn)

$openLogsBtn = New-Object System.Windows.Forms.Button
$openLogsBtn.Left = 390
$openLogsBtn.Top = 292
$openLogsBtn.Width = 170
$openLogsBtn.Height = 34
$openLogsBtn.Text = "Open Logs Folder"
$form.Controls.Add($openLogsBtn)

$preflightBtn = New-Object System.Windows.Forms.Button
$preflightBtn.Left = 574
$preflightBtn.Top = 292
$preflightBtn.Width = 120
$preflightBtn.Height = 34
$preflightBtn.Text = "Preflight"
$form.Controls.Add($preflightBtn)

$portableBtn = New-Object System.Windows.Forms.Button
$portableBtn.Left = 708
$portableBtn.Top = 292
$portableBtn.Width = 124
$portableBtn.Height = 34
$portableBtn.Text = "Prepare SSD"
$form.Controls.Add($portableBtn)

$closeBtn = New-Object System.Windows.Forms.Button
$closeBtn.Left = 708
$closeBtn.Top = 252
$closeBtn.Width = 124
$closeBtn.Height = 28
$closeBtn.Text = "Close"
$form.Controls.Add($closeBtn)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Left = 22
$logBox.Top = 340
$logBox.Width = 810
$logBox.Height = 245
$logBox.Multiline = $true
$logBox.ScrollBars = "Vertical"
$logBox.ReadOnly = $true
$logBox.BackColor = [System.Drawing.Color]::FromArgb(10, 14, 20)
$logBox.ForeColor = [System.Drawing.Color]::FromArgb(205, 230, 245)
$logBox.Font = New-Object System.Drawing.Font("Consolas", 9)
$form.Controls.Add($logBox)

$runBtn.Add_Click({
  $mode = [string]$modeCombo.SelectedItem
  $repoPath = $repoBox.Text
  $distro = $wslBox.Text
  $silent = $silentCheck.Checked
  $enableAp = $autopilotCheck.Checked
  $logBox.AppendText("[wizard] run mode=$mode autopilot=$enableAp silent=$silent`r`n")
  $code = Run-Activation -logBox $logBox -mode $mode -enableAutopilot $enableAp -silentMode $silent -repoPath $repoPath -wslDistro $distro
  if ($code -eq 0) {
    [System.Windows.Forms.MessageBox]::Show("Mode '$mode' completed successfully.", "RADRILONIUMA Installer", "OK", "Information") | Out-Null
  } else {
    [System.Windows.Forms.MessageBox]::Show("Mode '$mode' failed with code $code. Check logs.", "RADRILONIUMA Installer", "OK", "Warning") | Out-Null
  }
})

$rollbackBtn.Add_Click({
  $repoPath = $repoBox.Text
  $distro = $wslBox.Text
  $logBox.AppendText("[wizard] rollback requested`r`n")
  $code = Run-Activation -logBox $logBox -mode "revoke" -enableAutopilot $false -silentMode $true -repoPath $repoPath -wslDistro $distro
  if ($code -eq 0) {
    [System.Windows.Forms.MessageBox]::Show("Rollback completed.", "RADRILONIUMA Installer", "OK", "Information") | Out-Null
  } else {
    [System.Windows.Forms.MessageBox]::Show("Rollback failed with code $code.", "RADRILONIUMA Installer", "OK", "Warning") | Out-Null
  }
})

$openLogsBtn.Add_Click({
  $logRoot = Join-Path $env:ProgramData "RADRILONIUMA\\logs"
  New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
  Start-Process explorer.exe $logRoot | Out-Null
})

$preflightBtn.Add_Click({
  $mode = [string]$modeCombo.SelectedItem
  $repoPath = $repoBox.Text
  $distro = $wslBox.Text
  $args = @("-RepoPath", $repoPath, "-Mode", $mode)
  if (-not [string]::IsNullOrWhiteSpace($distro)) {
    $args += @("-WslDistro", $distro)
  }
  if ($silentCheck.Checked) {
    $args += "-Silent"
  }
  $logBox.AppendText("[wizard] preflight mode=$mode`r`n")
  $code = Run-SubScript -logBox $logBox -scriptFile "preinstall_security_gate.ps1" -arguments $args
  if ($code -eq 0) {
    [System.Windows.Forms.MessageBox]::Show("Preflight passed.", "RADRILONIUMA Installer", "OK", "Information") | Out-Null
  } else {
    [System.Windows.Forms.MessageBox]::Show("Preflight failed with code $code.", "RADRILONIUMA Installer", "OK", "Warning") | Out-Null
  }
})

$portableBtn.Add_Click({
  $repoPath = $repoBox.Text
  $targetDrive = $portableBox.Text
  $args = @("-RepoPath", $repoPath, "-TargetDrive", $targetDrive, "-Force")
  $logBox.AppendText("[wizard] prepare portable target=$targetDrive`r`n")
  $code = Run-SubScript -logBox $logBox -scriptFile "prepare_portable_core.ps1" -arguments $args
  if ($code -eq 0) {
    [System.Windows.Forms.MessageBox]::Show("Portable SSD core prepared on $targetDrive", "RADRILONIUMA Installer", "OK", "Information") | Out-Null
  } else {
    [System.Windows.Forms.MessageBox]::Show("Portable prep failed with code $code.", "RADRILONIUMA Installer", "OK", "Warning") | Out-Null
  }
})

$closeBtn.Add_Click({ $form.Close() })

[void]$form.ShowDialog()
