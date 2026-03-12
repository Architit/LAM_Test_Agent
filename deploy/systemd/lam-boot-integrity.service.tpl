[Unit]
Description=LAM Boot Integrity Gate
DefaultDependencies=no
After=local-fs.target
Before=multi-user.target

[Service]
Type=oneshot
User={{RUN_USER}}
WorkingDirectory={{REPO_ROOT}}
EnvironmentFile=-/etc/default/lam-control-plane
ExecStart=/bin/bash -lc 'cd "{{REPO_ROOT}}" && exec scripts/boot_integrity_check.sh'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
