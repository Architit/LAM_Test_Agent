[Unit]
Description=LAM HMAC Rotation Daemon (Early Boot Security)
After=lam-boot-integrity.service
Wants=lam-boot-integrity.service

[Service]
Type=simple
User={{RUN_USER}}
WorkingDirectory={{REPO_ROOT}}
EnvironmentFile=-/etc/default/lam-control-plane
ExecStart=/bin/bash -lc 'cd "{{REPO_ROOT}}" && exec scripts/lam_hmac_rotation_daemon.sh --daemon --interval-sec "${LAM_CIRCULATION_HMAC_ROTATE_INTERVAL_SEC:-86400}"'
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target

