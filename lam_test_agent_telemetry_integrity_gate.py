from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(paths: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in paths:
        out[str(p)] = sha256_file(p)
    return out


def verify_manifest(manifest: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for raw_path, expected in manifest.items():
        p = Path(raw_path)
        if not p.exists():
            errors.append(f"missing file: {p}")
            continue
        actual = sha256_file(p)
        if actual != expected:
            errors.append(f"hash mismatch: {p}")
    return errors


def parse_manifest(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be JSON object")
    files = data.get("files")
    if not isinstance(files, dict):
        raise ValueError("manifest.files must be object")
    out: dict[str, str] = {}
    for k, v in files.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ValueError("manifest entries must be string->string")
        out[k] = v
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create/verify telemetry integrity manifest.")
    parser.add_argument("--mode", choices=["create", "verify"], required=True)
    parser.add_argument("--manifest", default="memory/FRONT/TELEMETRY_INTEGRITY_MANIFEST.json")
    parser.add_argument("--file", action="append", default=[])
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest).resolve()

    if args.mode == "create":
        if not args.file:
            print("TELEMETRY_INTEGRITY_GATE_FAIL no --file provided for create")
            return 2
        paths = [Path(f).resolve() for f in args.file]
        missing = [p for p in paths if not p.exists()]
        if missing:
            for p in missing:
                print(f"TELEMETRY_INTEGRITY_GATE_FAIL missing_file={p}")
            return 2
        manifest_doc = {"files": build_manifest(paths)}
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest_doc, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        print(f"TELEMETRY_INTEGRITY_GATE_OK mode=create manifest={manifest_path} files={len(paths)}")
        return 0

    if not manifest_path.exists():
        print(f"TELEMETRY_INTEGRITY_GATE_FAIL missing_manifest={manifest_path}")
        return 2

    try:
        manifest_files = parse_manifest(manifest_path)
    except Exception as exc:  # pragma: no cover
        print(f"TELEMETRY_INTEGRITY_GATE_FAIL error={exc}")
        return 2

    errors = verify_manifest(manifest_files)
    if errors:
        for err in errors:
            print(f"TELEMETRY_INTEGRITY_GATE_FAIL {err}")
        return 1

    print(f"TELEMETRY_INTEGRITY_GATE_OK mode=verify manifest={manifest_path} files={len(manifest_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
