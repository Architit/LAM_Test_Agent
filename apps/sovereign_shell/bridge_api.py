#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime

PORT = 8080
WORK_DIR = Path("/home/architit/work")
BRIDGE_DIR = WORK_DIR / "RADRILONIUMA"
STATIC_DIR = Path(__file__).parent

ORGANS = [
    "LAM_Test_Agent", "RADRILONIUMA", "LAM_Comunication_Agent", 
    "Archivator_Agent", "Aristos", "Ayaearias-Triania", "CORE", 
    "Croambeth", "Fomanor", "Glokha", "J.A.R.V.I.S", "Jouna", 
    "Kitora", "LAM-Codex_Agent", "LAM", "LAM_DATA_Src", "Luvia", 
    "Melia", "Operator_Agent", "Oxin", "Pralia", "RADRILONIUMA-PROJECT", 
    "Roaudter-agent", "Sataris", "System-", "TRIANIUMA_DATA_BASE", 
    "Taspit", "Trianiuma", "Trianiuma_MEM_CORE", "Vilami", "Vionori", 
    "Vrela", "Zudory"
]

class SovereignHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api/organs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            data = []
            for organ in ORGANS:
                path = WORK_DIR / organ
                exists = path.exists()
                status = "active" if exists else "offline"
                data.append({"name": organ, "status": status, "path": str(path)})
            self.wfile.write(json.dumps(data).encode())
        elif self.path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            log_path = BRIDGE_DIR / "DEV_LOGS.md"
            lines = []
            if log_path.exists():
                with open(log_path, "r") as f:
                    lines = f.readlines()[-50:]
            self.wfile.write(json.dumps({"logs": lines}).encode())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/trigger":
            # Manual pulse trigger
            subprocess.Popen([str(BRIDGE_DIR / "scripts" / "trigger_pulse.sh"), "--all"])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{\"status\": \"pulsing\"}")

if __name__ == "__main__":
    os.chdir(STATIC_DIR)
    with socketserver.TCPServer(("", PORT), SovereignHandler) as httpd:
        print(f"Sovereign Bridge API active at http://localhost:{PORT}")
        httpd.serve_forever()
