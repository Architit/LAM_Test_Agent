from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_test_entrypoint_modes_declared():
    text = (REPO_ROOT / "scripts" / "test_entrypoint.sh").read_text(encoding="utf-8")
    assert "--unit-only" in text
    assert "--integration" in text
    assert "--ci" in text
