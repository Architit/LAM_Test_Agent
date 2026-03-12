[Unit]
Description=LAM Security Telemetry Guard
After=lam-boot-integrity.service network-online.target
Wants=lam-boot-integrity.service network-online.target

[Service]
Type=simple
User={{RUN_USER}}
WorkingDirectory={{REPO_ROOT}}
EnvironmentFile=-/etc/default/lam-control-plane
ExecStart=/bin/bash -lc 'cd "{{REPO_ROOT}}" && exec scripts/lam_security_telemetry_guard.sh --interval-sec 10'
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
