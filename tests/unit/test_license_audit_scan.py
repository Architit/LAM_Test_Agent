from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "local" / "license_audit_scan.py"
    spec = importlib.util.spec_from_file_location("license_audit_scan", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_github_slug_supports_https_and_ssh() -> None:
    m = load_module()
    assert m.parse_github_slug("https://github.com/openai/openai-python.git") == "openai/openai-python"
    assert m.parse_github_slug("git@github.com:org/repo.git") == "org/repo"


def test_detect_license_type_mit() -> None:
    m = load_module()
    text = "MIT License\nPermission is hereby granted, free of charge, to any person obtaining a copy..."
    assert m.detect_license_type(text) == "MIT"


def test_find_license_file_case_insensitive(tmp_path: Path) -> None:
    m = load_module()
    p = tmp_path / "license.txt"
    p.write_text("MIT License\n", encoding="utf-8")
    found = m.find_license_file(tmp_path)
    assert found is not None
    assert found.name == "license.txt"
