from __future__ import annotations

import json
from pathlib import Path

from apps.lam_console.feedback_gateway import FeedbackGateway


def _write_mesh(path: Path, ready_names: list[str]) -> None:
    providers = []
    for name in ["openai", "claude_sonnet", "grok_xai", "shinkai", "github", "google", "microsoft"]:
        providers.append({"name": name, "ready": name in ready_names, "signals": {}})
    path.write_text(
        json.dumps(
            {
                "ts_utc": "2026-03-07T00:00:00Z",
                "providers_total": len(providers),
                "providers_ready": len(ready_names),
                "providers_not_ready": len(providers) - len(ready_names),
                "providers": providers,
                "signals": {"status": "ok"},
            },
            ensure_ascii=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_feedback_gateway_dispatches_to_ready_channels(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    repo_root = Path(__file__).resolve().parents[2]
    svc = FeedbackGateway(repo_root)

    _write_mesh(svc.external_mesh_state, ["openai", "github"])
    svc.requests_file.parent.mkdir(parents=True, exist_ok=True)
    svc.requests_file.write_text(
        json.dumps(
            {
                "source": "test",
                "severity": "warning",
                "message": "manual recommendation",
                "targets": ["openai", "github"],
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = svc.run_once()
    assert payload["sent_count"] >= 2
    assert payload["spooled_count"] == 0
    openai_out = svc.channels_dir / "openai.jsonl"
    github_out = svc.channels_dir / "github.jsonl"
    assert openai_out.exists()
    assert github_out.exists()


def test_feedback_gateway_spools_when_no_ready_targets(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    repo_root = Path(__file__).resolve().parents[2]
    svc = FeedbackGateway(repo_root)

    _write_mesh(svc.external_mesh_state, [])
    svc.requests_file.write_text(
        json.dumps(
            {
                "source": "test",
                "severity": "critical",
                "message": "no channels",
                "targets": ["openai"],
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = svc.run_once()
    assert payload["spooled_count"] >= 1
    assert svc.spool_file.exists()


def test_feedback_gateway_blocks_noncritical_during_lockdown(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    repo_root = Path(__file__).resolve().parents[2]
    svc = FeedbackGateway(repo_root)

    _write_mesh(svc.external_mesh_state, ["openai", "github"])
    (svc.hub_root / "security_lockdown.flag").write_text("1\n", encoding="utf-8")
    svc.requests_file.write_text(
        json.dumps(
            {
                "source": "test",
                "severity": "warning",
                "message": "must block",
                "targets": ["openai", "github"],
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    payload = svc.run_once()
    assert payload["spooled_count"] >= 1
    assert payload["sent_count"] == 0


def test_feedback_gateway_allows_critical_during_lockdown_by_allowlist(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_FEEDBACK_CRITICAL_ALLOWED", "github")
    repo_root = Path(__file__).resolve().parents[2]
    svc = FeedbackGateway(repo_root)

    _write_mesh(svc.external_mesh_state, ["openai", "github"])
    (svc.hub_root / "failsafe_active.flag").write_text("1\n", encoding="utf-8")
    svc.requests_file.write_text(
        json.dumps(
            {
                "source": "test",
                "severity": "critical",
                "message": "critical path",
                "targets": ["openai", "github"],
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    payload = svc.run_once()
    assert payload["sent_count"] == 1
    assert payload["spooled_count"] == 0
