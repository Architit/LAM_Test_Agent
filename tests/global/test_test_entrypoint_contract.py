from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_test_entrypoint_modes_declared():
    text = (REPO_ROOT / "scripts" / "local" / "test_entrypoint.sh").read_text(encoding="utf-8")
    assert "--unit" in text
    assert "--integration" in text
    assert "--route-matrix" in text
    assert "--memory" in text
    assert "--transport" in text
    assert "--p0-safety" in text
    assert "--flow-control" in text
    assert "--research-gate" in text
