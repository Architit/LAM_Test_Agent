from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "apps" / "lam_console" / "io_spectral_daemon.py"
    spec = importlib.util.spec_from_file_location("io_spectral_daemon", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_compute_freq_bands_maps_expected_ranges() -> None:
    m = load_module()
    bands = m.compute_freq_bands([0.2, 0.8, 3.5, 10.0, 64.0])
    assert bands["ultra_low_0_0_5hz"] == 1
    assert bands["low_0_5_2hz"] == 1
    assert bands["mid_2_8hz"] == 1
    assert bands["high_8_32hz"] == 1
    assert bands["ultra_high_32hz_plus"] == 1


def test_compute_io_vector_normalizes() -> None:
    m = load_module()
    vec = m.compute_io_vector({"ultra_low_0_0_5hz": 1, "low_0_5_2hz": 1, "mid_2_8hz": 2, "high_8_32hz": 0, "ultra_high_32hz_plus": 0})
    assert vec["mid_2_8hz"] == 0.5
    assert vec["low_0_5_2hz"] == 0.25


def test_classify_domain_keyboard() -> None:
    m = load_module()
    event = {"event": "keypress", "source": "keyboard"}
    assert m.classify_domain(event) == "keyboard"
