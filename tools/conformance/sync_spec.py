#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync spec/<version>/ into the arp-conformance embedded snapshot.")
    parser.add_argument("--version", default="v1", help="Spec version directory name (default: v1)")
    parser.add_argument("--clean", action="store_true", help="Delete the destination before copying")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    spec_root = repo_root / "spec" / args.version
    if not spec_root.exists():
        raise SystemExit(f"Missing spec directory: {spec_root}")

    dest_root = repo_root / "conformance" / "python" / "src" / "arp_conformance" / "_spec" / args.version
    if args.clean and dest_root.exists():
        shutil.rmtree(dest_root)

    dest_root.parent.mkdir(parents=True, exist_ok=True)
    if dest_root.exists():
        shutil.rmtree(dest_root)

    shutil.copytree(spec_root, dest_root)
    print(f"Synced {spec_root} -> {dest_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

