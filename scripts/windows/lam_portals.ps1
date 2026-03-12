param(
    [string]$RepoPath = "/home/architit/work/LAM_Test_Agent",
    [int]$PortalPort = 8765
)

$ErrorActionPreference = "Stop"

function Start-BridgeStack {
    wsl bash -lc "cd '$RepoPath' && LAM_PORTAL_MODE=http scripts/lam_bridge_stack.sh start"
}

function Open-PortalBrowser {
    $url = "http://127.0.0.1:$PortalPort"
    Start-Process $url
}

function Open-WT {
    $cmd1 = "wsl.exe bash -lc `"cd '$RepoPath' && scripts/lam_console.sh`""
    $cmd2 = "wsl.exe bash -lc `"cd '$RepoPath' && tail -f .gateway/hub/logs/model_worker.log`""
    $cmd3 = "wsl.exe bash -lc `"cd '$RepoPath' && tail -f .gateway/hub/logs/portal_gateway.log`""
    wt new-tab --title "LAM Captain Bridge" $cmd1 ; `
       new-tab --title "LAM Worker Log" $cmd2 ; `
       new-tab --title "LAM Gateway Log" $cmd3
}

Write-Host "[lam-portals] starting bridge stack in WSL..."
Start-BridgeStack
Write-Host "[lam-portals] opening Windows Terminal tabs..."
Open-WT
Write-Host "[lam-portals] opening portal browser..."
Open-PortalBrowser
Write-Host "[lam-portals] done"
