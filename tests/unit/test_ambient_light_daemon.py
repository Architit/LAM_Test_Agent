from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_ambient_module():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "apps" / "lam_console" / "ambient_light_daemon.py"
    spec = importlib.util.spec_from_file_location("ambient_light_daemon", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dispatches_vector_to_ambient_scoped_device(tmp_path, monkeypatch) -> None:
    module = load_ambient_module()
    repo_root = Path(__file__).resolve().parents[2]
    bridge_root = tmp_path / ".gateway" / "bridge" / "captain"
    hub_root = tmp_path / ".gateway" / "hub"
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(bridge_root))
    monkeypatch.setenv("LAM_HUB_ROOT", str(hub_root))

    bridge_root.mkdir(parents=True, exist_ok=True)
    (bridge_root / "devices.json").write_text(
        json.dumps(
            {
                "devices": [
                    {
                        "device_id": "aura_hub",
                        "consent": {"approved": True},
                        "scopes": ["ambient_light", "device_status"],
                        "trust_level": "limited",
                    }
                ]
            },
            ensure_ascii=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (bridge_root / "ambient_light_vector.json").write_text(
        json.dumps(
            {
                "profile": "aura_ambient_mirror",
                "mode": "inversion",
                "pane": "ACTIVITY",
                "mirror_pane": "LOG",
                "vector": {"rgb": [40, 180, 255], "brightness_pct": 78, "wave_hz": 2.1, "phase": "anti"},
            },
            ensure_ascii=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    svc = module.AmbientLightBridge(repo_root)
    result = svc.run_once()
    assert result["dispatched"] == 1

    outbox = bridge_root / "device_outbox" / "aura_hub.jsonl"
    assert outbox.exists()
    msg = json.loads(outbox.read_text(encoding="utf-8").splitlines()[-1])
    assert msg["op"] == "ambient_light_apply"
    assert msg["vector"]["phase"] == "anti"
