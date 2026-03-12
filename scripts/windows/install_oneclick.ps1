param(
    [string]$RepoPath = "/home/architit/work/LAM_Test_Agent"
)

$ErrorActionPreference = "Stop"

Write-Host "[install-oneclick] Windows mode: launching WSL bridge stack..."
wsl bash -lc "cd '$RepoPath' && scripts/lam_bridge_stack.sh start"

Write-Host "[install-oneclick] Opening Windows Terminal tabs..."
$cmd1 = "wsl.exe bash -lc `"cd '$RepoPath' && scripts/lam_console.sh`""
$cmd2 = "wsl.exe bash -lc `"cd '$RepoPath' && tail -f .gateway/hub/logs/model_worker.log`""
$cmd3 = "wsl.exe bash -lc `"cd '$RepoPath' && tail -f .gateway/hub/logs/portal_gateway.log`""
wt new-tab --title "LAM Captain Bridge" $cmd1 ; `
   new-tab --title "LAM Worker Log" $cmd2 ; `
   new-tab --title "LAM Gateway Log" $cmd3

Write-Host "[install-oneclick] Done"

