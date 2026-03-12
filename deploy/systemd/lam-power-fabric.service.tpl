[Unit]
Description=LAM Power Fabric Guard
After=lam-boot-integrity.service network-online.target
Wants=lam-boot-integrity.service network-online.target

[Service]
Type=simple
User={{RUN_USER}}
WorkingDirectory={{REPO_ROOT}}
EnvironmentFile=-/etc/default/lam-control-plane
ExecStart=/bin/bash -lc 'cd "{{REPO_ROOT}}" && exec scripts/lam_power_fabric_guard.sh --interval-sec 12'
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
