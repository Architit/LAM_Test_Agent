from __future__ import annotations

from pathlib import Path

from apps.lam_console.external_provider_mesh import ExternalProviderMesh


def test_external_provider_mesh_emits_expected_registry(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("SHINKAI_API_URL", "http://127.0.0.1:8080")

    repo_root = Path(__file__).resolve().parents[2]
    svc = ExternalProviderMesh(repo_root)
    payload = svc.run_once()

    names = [p.get("name") for p in payload.get("providers", [])]
    assert "github" in names
    assert "google" in names
    assert "microsoft" in names
    assert "openai" in names
    assert "claude_sonnet" in names
    assert "grok_xai" in names
    assert "shinkai" in names
    assert "ollama" in names
    assert "nvidia" in names
    assert "intel" in names
    assert "amd" in names
    assert "razer" in names
    assert "samsung_android" in names
    assert "android" in names
    assert "ubuntu" in names
    assert payload.get("providers_total") == 15
