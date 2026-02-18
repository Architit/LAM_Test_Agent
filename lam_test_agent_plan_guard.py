from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable


EXEC_LOG_LINE_RE = re.compile(
    r"^\s*(?:-\s+)?\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}\s+UTC)?\s*(?::|—|-)\s+(.*\S)\s*$"
)


def extract_execution_events(plan_text: str) -> list[str]:
    events: list[str] = []
    for line in plan_text.splitlines():
        m = EXEC_LOG_LINE_RE.match(line)
        if m:
            events.append(m.group(1))
    return events


def detect_adjacent_duplicates(events: list[str]) -> list[str]:
    errors: list[str] = []
    for i in range(1, len(events)):
        if events[i] == events[i - 1]:
            errors.append(f"adjacent duplicate execution event at positions {i - 1} and {i}")
    return errors


def _repeat_count(events: list[str], start: int, window: int) -> int:
    pattern = events[start : start + window]
    count = 1
    pos = start + window
    while pos + window <= len(events) and events[pos : pos + window] == pattern:
        count += 1
        pos += window
    return count


def detect_repeating_cycles(
    events: list[str],
    max_window: int = 4,
    min_repeats: int = 3,
    *,
    tail_only: bool,
) -> list[str]:
    if max_window <= 0 or min_repeats < 2:
        raise ValueError("max_window must be >0 and min_repeats must be >=2")

    errors: list[str] = []
    seen: set[tuple[int, int, tuple[str, ...]]] = set()

    for window in range(1, max_window + 1):
        needed = window * min_repeats
        if len(events) < needed:
            continue

        starts: Iterable[int]
        if tail_only:
            starts = [len(events) - needed]
        else:
            starts = range(0, len(events) - needed + 1)

        for start in starts:
            repeats = _repeat_count(events, start, window)
            if repeats < min_repeats:
                continue
            if tail_only and (start + repeats * window != len(events)):
                continue

            pattern = tuple(events[start : start + window])
            key = (start, window, pattern)
            if key in seen:
                continue
            seen.add(key)
            mode = "tail" if tail_only else "global"
            errors.append(
                f"{mode} cycle detected at {start}, window={window}, repeats={repeats}: "
                + " -> ".join(pattern)
            )

    return errors


def validate_plan_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    events = extract_execution_events(text)
    errors = detect_adjacent_duplicates(events)
    errors.extend(detect_repeating_cycles(events, max_window=5, min_repeats=3, tail_only=False))
    errors.extend(detect_repeating_cycles(events, max_window=5, min_repeats=3, tail_only=True))
    return errors


def ecosystem_markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    files.extend(sorted(root.glob("memory/**/*.md")))
    files.extend(sorted(root.glob("*.md")))
    deduped: list[Path] = []
    seen: set[Path] = set()
    for p in files:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            deduped.append(p)
    return deduped


def validate_many(paths: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        file_errors = validate_plan_file(path)
        for e in file_errors:
            errors.append(f"{path}: {e}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) not in {2, 3}:
        print(f"Usage: {argv[0]} <plan.md|dir> | --ecosystem <root_dir>")
        return 2

    if argv[1] == "--ecosystem":
        root = Path(argv[2] if len(argv) == 3 else ".")
        if not root.exists():
            print(f"root dir not found: {root}")
            return 2
        files = ecosystem_markdown_files(root)
    else:
        path = Path(argv[1])
        if not path.exists():
            print(f"plan file not found: {path}")
            return 2
        if path.is_dir():
            files = sorted(path.glob("**/*.md"))
        else:
            files = [path]

    errors = validate_many(files)
    if errors:
        for e in errors:
            print(f"PLAN_GUARD_FAIL: {e}")
        return 1

    print(f"PLAN_GUARD_OK scanned_files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
