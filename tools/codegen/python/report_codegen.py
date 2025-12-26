#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def _load_bundle(openapi_path: Path) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[3]
    codegen_root = repo_root / "tools" / "codegen" / "python" / "client"
    sys.path.insert(0, str(codegen_root))
    try:
        from generate import bundle_openapi  # type: ignore
    finally:
        try:
            sys.path.remove(str(codegen_root))
        except ValueError:
            pass

    return bundle_openapi(openapi_path)


def _count_operations(paths: dict[str, Any]) -> int:
    methods = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}
    count = 0
    for item in paths.values():
        if not isinstance(item, dict):
            continue
        for key in item.keys():
            if key.lower() in methods:
                count += 1
    return count


def _render(service: str, bundled: dict[str, Any]) -> list[str]:
    paths = bundled.get("paths") or {}
    components = bundled.get("components") or {}
    schemas = components.get("schemas") or {}

    path_count = len(paths) if isinstance(paths, dict) else 0
    op_count = _count_operations(paths if isinstance(paths, dict) else {})
    schema_count = len(schemas) if isinstance(schemas, dict) else 0

    lines = [
        f"Service: {service}",
        f"- Paths: {path_count}",
        f"- Operations: {op_count}",
        f"- Schemas: {schema_count}",
        "",
    ]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1", help="Spec version directory (default: v1)")
    parser.add_argument("--out", help="Write report to this file instead of stdout")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    spec_root = repo_root / "spec" / args.version
    openapi_root = spec_root / "openapi"

    services = {
        "run_gateway": openapi_root / "run-gateway.openapi.yaml",
        "run_coordinator": openapi_root / "run-coordinator.openapi.yaml",
        "atomic_executor": openapi_root / "atomic-executor.openapi.yaml",
        "composite_executor": openapi_root / "composite-executor.openapi.yaml",
        "node_registry": openapi_root / "node-registry.openapi.yaml",
        "selection": openapi_root / "selection.openapi.yaml",
        "pdp": openapi_root / "pdp.openapi.yaml",
    }

    lines: list[str] = [f"ARP codegen report ({args.version})", ""]
    for name, path in services.items():
        if not path.exists():
            print(f"Missing OpenAPI spec: {path}", file=sys.stderr)
            return 2
        bundled = _load_bundle(path)
        lines.extend(_render(name, bundled))

    output = "\n".join(lines).rstrip() + "\n"
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
