#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def iter_json_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*.json") if path.is_file()]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    spec_root = repo_root / "spec"
    if not spec_root.exists():
        print(f"spec/ not found at {spec_root}", file=sys.stderr)
        return 2

    json_files = iter_json_files(spec_root)
    failures: list[tuple[Path, Exception]] = []

    for path in sorted(json_files):
        try:
            with path.open("r", encoding="utf-8") as file:
                json.load(file)
        except Exception as exc:  # noqa: BLE001 - show parse failures
            failures.append((path, exc))

    if failures:
        print("Invalid JSON:", file=sys.stderr)
        for path, exc in failures:
            print(f"- {path.relative_to(repo_root)}: {exc}", file=sys.stderr)
        return 1

    print(f"OK: parsed {len(json_files)} JSON files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

