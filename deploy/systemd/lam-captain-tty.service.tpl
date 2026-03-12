[Unit]
Description=LAM Captain Bridge Console on tty1
After=lam-control-plane.service
Conflicts=getty@tty1.service

[Service]
Type=simple
User={{RUN_USER}}
WorkingDirectory={{REPO_ROOT}}
EnvironmentFile=-/etc/default/lam-control-plane
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
TTYVTDisallocate=yes
StandardInput=tty
StandardOutput=tty
StandardError=journal
ExecStart=/bin/bash -lc 'cd "{{REPO_ROOT}}" && exec scripts/lam_console.sh'
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
