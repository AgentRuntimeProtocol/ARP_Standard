#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _tracked_files(repo_root: Path) -> list[str]:
    output = subprocess.check_output(["git", "ls-files"], cwd=repo_root)
    return output.decode("utf-8").splitlines()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    tracked = _tracked_files(repo_root)

    tracked_set = set(tracked)
    tracked_prefixes = [
        "clients/python/src/arp_standard_client/daemon/",
        "clients/python/src/arp_standard_client/runtime/",
        "clients/python/src/arp_standard_client/tool_registry/",
        "kits/python/src/arp_standard_server/daemon/",
        "kits/python/src/arp_standard_server/runtime/",
        "kits/python/src/arp_standard_server/tool_registry/",
    ]
    tracked_files = [
        "models/python/src/arp_standard_model/_generated.py",
        "models/python/src/arp_standard_model/_requests.py",
    ]

    violations: list[str] = []
    for path in tracked:
        if any(path.startswith(prefix) for prefix in tracked_prefixes):
            violations.append(path)
            continue
        if path in tracked_set and path in tracked_files:
            violations.append(path)

    if violations:
        print("Generated artifacts must not be checked in:", file=sys.stderr)
        for path in sorted(violations):
            print(f"- {path}", file=sys.stderr)
        return 1

    print("OK: no generated artifacts tracked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
