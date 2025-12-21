#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable


class DependencyMissing(RuntimeError):
    pass


def _require_ruamel() -> Any:
    try:
        from ruamel.yaml import YAML  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise DependencyMissing(
            "Missing dependency: ruamel.yaml. Install with: python -m pip install -r tools/validate/requirements.txt"
        ) from exc
    return YAML


def _load_bundle(openapi_path: Path) -> tuple[dict[str, Any], Any]:
    repo_root = Path(__file__).resolve().parents[2]
    codegen_root = repo_root / "tools" / "codegen" / "python" / "client"
    sys.path.insert(0, str(codegen_root))
    try:
        from generate import bundle_openapi, _json_pointer_get  # type: ignore
    finally:
        try:
            sys.path.remove(str(codegen_root))
        except ValueError:
            pass

    return bundle_openapi(openapi_path), _json_pointer_get


def _iter_refs(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        if "$ref" in value and isinstance(value["$ref"], str):
            yield path or "<root>", value["$ref"]
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            yield from _iter_refs(child, child_path)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}/{idx}" if path else f"/{idx}"
            yield from _iter_refs(child, child_path)


def _find_unsupported(value: Any, path: str = "") -> list[str]:
    unsupported_keys = {"oneOf", "discriminator", "callbacks"}
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else f"/{key}"
            if key in unsupported_keys:
                hits.append(child_path)
            hits.extend(_find_unsupported(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}/{idx}" if path else f"/{idx}"
            hits.extend(_find_unsupported(child, child_path))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1", help="Spec version directory (default: v1)")
    args = parser.parse_args()

    try:
        _require_ruamel()
    except DependencyMissing as exc:
        print(str(exc), file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parents[2]
    spec_root = repo_root / "spec" / args.version
    openapi_root = spec_root / "openapi"

    if not openapi_root.exists():
        print(f"OpenAPI directory not found: {openapi_root}", file=sys.stderr)
        return 2

    failures: list[str] = []
    for openapi_path in sorted(openapi_root.glob("*.yaml")):
        try:
            bundled, json_pointer_get = _load_bundle(openapi_path)
        except Exception as exc:  # noqa: BLE001 - surface bundler issues
            failures.append(f"{openapi_path.relative_to(repo_root)}: bundle failed: {exc}")
            continue

        unsupported = _find_unsupported(bundled)
        for location in unsupported:
            failures.append(
                f"{openapi_path.relative_to(repo_root)}: unsupported feature at {location}"
            )

        for location, ref in _iter_refs(bundled):
            if not ref.startswith("#"):
                continue
            try:
                json_pointer_get(bundled, ref)
            except Exception as exc:  # noqa: BLE001 - surface ref issues
                failures.append(
                    f"{openapi_path.relative_to(repo_root)}: invalid $ref {ref} at {location}: {exc}"
                )

    if failures:
        print("OpenAPI validation failed:", file=sys.stderr)
        for line in failures:
            print(f"- {line}", file=sys.stderr)
        return 1

    print("OK: OpenAPI specs bundled and validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
