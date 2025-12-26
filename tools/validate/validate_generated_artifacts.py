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
        "clients/python/src/arp_standard_client/run_gateway/",
        "clients/python/src/arp_standard_client/run_coordinator/",
        "clients/python/src/arp_standard_client/atomic_executor/",
        "clients/python/src/arp_standard_client/composite_executor/",
        "clients/python/src/arp_standard_client/node_registry/",
        "clients/python/src/arp_standard_client/selection/",
        "clients/python/src/arp_standard_client/pdp/",
        "kits/python/src/arp_standard_server/run_gateway/",
        "kits/python/src/arp_standard_server/run_coordinator/",
        "kits/python/src/arp_standard_server/atomic_executor/",
        "kits/python/src/arp_standard_server/composite_executor/",
        "kits/python/src/arp_standard_server/node_registry/",
        "kits/python/src/arp_standard_server/selection/",
        "kits/python/src/arp_standard_server/pdp/",
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
