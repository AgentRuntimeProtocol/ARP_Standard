#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


_MODEL_IMPORT_RE = re.compile(r"^from\s+\.+models\.[a-zA-Z0-9_]+\s+import\s+(.+)$", re.MULTILINE)
_MODEL_PACKAGE_IMPORT_RE = re.compile(r"^from\s+\.+models\s+import\s+(.+)$", re.MULTILINE)


def _patch_text(text: str) -> str:
    text = _MODEL_IMPORT_RE.sub(r"from arp_standard_model import \1", text)
    text = _MODEL_PACKAGE_IMPORT_RE.sub(r"from arp_standard_model import \1", text)
    text = text.replace(".to_dict()", ".model_dump(exclude_none=True)")
    text = text.replace(".from_dict(", ".model_validate(")
    text = re.sub(r"model_dump\(\s*by_alias=True,\s*", "model_dump(", text)
    text = re.sub(r"model_dump\(\s*by_alias=True\s*\)", "model_dump()", text)
    return text


def _patch_tree(service_root: Path) -> None:
    for path in service_root.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        if "models" in path.parts:
            continue
        original = path.read_text(encoding="utf-8")
        updated = _patch_text(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Path to arp_standard_client package root")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise FileNotFoundError(f"Missing client package root: {root}")

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name.startswith("__"):
            continue
        _patch_tree(child)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
