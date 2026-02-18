from __future__ import annotations

from pathlib import Path

import pytest

import lam_test_agent_lam_forensics as lam_forensics


@pytest.mark.unit
def test_collect_lam_forensics_tracks_exit_codes_per_stage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lam_root = tmp_path / "LAM"
    lam_root.mkdir()

    monkeypatch.setattr(lam_forensics, "sibling_repo", lambda _: tmp_path / "repo")

    responses = iter(
        [
            (0, "main"),
            (0, " M tracked.py\n?? untracked.txt"),
            (0, " 1234567 module"),
            (0, "1:Phase 4.3"),
            (0, "1:deadloop_guard"),
            (7, '{"preflight":{"decision":"HOLD","reason":"gov_only"}}'),
            (0, '{"preflight":{"decision":"PASS"},"resume":{"decision":"PASS"}}'),
            (3, '{"summary":{"repo_count":2}}'),
            (5, "deadloop tests failed"),
        ]
    )

    def fake_run(_: list[str], __: Path) -> tuple[int, str]:
        return next(responses)

    monkeypatch.setattr(lam_forensics, "_run", fake_run)

    snapshot = lam_forensics.collect_lam_forensics(lam_root)

    assert snapshot["guard_probe_hold"]["exit_code"] == 7
    assert snapshot["guard_probe_pass"]["exit_code"] == 0
    assert snapshot["ecosystem_scan"]["exit_code"] == 3
    assert snapshot["deadloop_test_suite"]["exit_code"] == 5
    assert snapshot["ecosystem_scan"]["result"]["summary"]["repo_count"] == 2


@pytest.mark.unit
def test_collect_lam_forensics_uses_repo_venv_python_when_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lam_root = tmp_path / "LAM"
    (lam_root / ".venv" / "bin").mkdir(parents=True)
    (lam_root / ".venv" / "bin" / "python").write_text("", encoding="utf-8")

    monkeypatch.setattr(lam_forensics, "sibling_repo", lambda _: tmp_path / "repo")

    captured: list[list[str]] = []
    responses = iter([(0, "")] * 9)

    def fake_run(cmd: list[str], _: Path) -> tuple[int, str]:
        captured.append(cmd)
        return next(responses)

    monkeypatch.setattr(lam_forensics, "_run", fake_run)

    lam_forensics.collect_lam_forensics(lam_root)

    expected_python = str(lam_root / ".venv" / "bin" / "python")
    assert captured[5][0] == expected_python
    assert captured[6][0] == expected_python
    assert captured[7][0] == expected_python
    assert captured[8][0] == expected_python
