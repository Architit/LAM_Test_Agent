[Unit]
Description=LAM Control Plane Model Worker
After=network-online.target lam-boot-integrity.service lam-security-telemetry.service lam-power-fabric.service lam-hmac-rotation.service
Wants=network-online.target lam-boot-integrity.service lam-security-telemetry.service lam-power-fabric.service lam-hmac-rotation.service

[Service]
Type=simple
User={{RUN_USER}}
WorkingDirectory={{REPO_ROOT}}
EnvironmentFile=-/etc/default/lam-control-plane
Environment=PYTHONUNBUFFERED=1
ExecStart=/bin/bash -lc 'cd "{{REPO_ROOT}}" && exec scripts/lam_control_plane_service.sh'
ExecStop=/bin/bash -lc 'cd "{{REPO_ROOT}}" && scripts/lam_bridge_stack.sh stop'
ExecReload=/bin/bash -lc 'cd "{{REPO_ROOT}}" && scripts/lam_bridge_stack.sh restart'
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
