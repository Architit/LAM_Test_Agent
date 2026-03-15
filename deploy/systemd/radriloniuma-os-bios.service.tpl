[Unit]
Description=RADRILONIUMA OS BIOS Boot Manager
After=network-online.target local-fs.target
Wants=network-online.target

[Service]
Type=oneshot
User={{RUN_USER}}
Group={{RUN_USER}}
WorkingDirectory={{REPO_ROOT}}
ExecStart={{REPO_ROOT}}/scripts/radriloniuma_os_bios_boot.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
