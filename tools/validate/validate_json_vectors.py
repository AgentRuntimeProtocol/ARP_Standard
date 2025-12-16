#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any


class DependencyMissing(RuntimeError):
    pass


def require_jsonschema() -> Any:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise DependencyMissing(
            "Missing dependency: jsonschema. Install with: python -m pip install -r tools/validate/requirements.txt"
        ) from exc
    return jsonschema


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_one(schema_path: Path, instance_path: Path, *, jsonschema: Any) -> list[str]:
    schema = load_json(schema_path)
    instance = load_json(instance_path)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        resolver = jsonschema.RefResolver(base_uri=schema_path.as_uri(), referrer=schema)
    validator = jsonschema.Draft7Validator(schema, resolver=resolver)

    errors = sorted(validator.iter_errors(instance), key=lambda exc: list(exc.path))
    rendered: list[str] = []
    for err in errors:
        location = "/".join(str(p) for p in err.path) or "<root>"
        rendered.append(f"{location}: {err.message}")
    return rendered


def validate_tree(payload_root: Path, schemas_root: Path, repo_root: Path, *, jsonschema: Any) -> list[str]:
    failures: list[str] = []
    for instance_path in sorted(payload_root.rglob("*.json")):
        rel = instance_path.relative_to(payload_root)
        schema_path = schemas_root / rel.parent / f"{instance_path.stem}.schema.json"
        if not schema_path.exists():
            failures.append(
                f"{instance_path.relative_to(repo_root)}: missing schema {schema_path.relative_to(repo_root)}"
            )
            continue

        try:
            errors = validate_one(schema_path, instance_path, jsonschema=jsonschema)
        except json.JSONDecodeError as exc:
            failures.append(f"{instance_path.relative_to(repo_root)}: invalid JSON: {exc}")
            continue
        except Exception as exc:  # noqa: BLE001 - surface validator issues
            failures.append(f"{instance_path.relative_to(repo_root)}: validation error: {exc}")
            continue

        for message in errors:
            failures.append(f"{instance_path.relative_to(repo_root)}: {message}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1alpha1", help="Spec version directory (default: v1alpha1)")
    parser.add_argument("--include-examples", action="store_true", help="Also validate spec/<ver>/examples")
    args = parser.parse_args()

    try:
        jsonschema = require_jsonschema()
    except DependencyMissing as exc:
        print(str(exc), file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parents[2]
    spec_root = repo_root / "spec" / args.version
    schemas_root = spec_root / "schemas"
    vectors_root = spec_root / "conformance" / "json_vectors"

    if not schemas_root.exists():
        print(f"Schemas not found: {schemas_root}", file=sys.stderr)
        return 2
    if not vectors_root.exists():
        print(f"Conformance vectors not found: {vectors_root}", file=sys.stderr)
        return 2

    failures = validate_tree(vectors_root, schemas_root, repo_root, jsonschema=jsonschema)
    if args.include_examples:
        examples_root = spec_root / "examples"
        if not examples_root.exists():
            print(f"Examples not found: {examples_root}", file=sys.stderr)
            return 2
        failures.extend(validate_tree(examples_root, schemas_root, repo_root, jsonschema=jsonschema))

    if failures:
        print("Validation failed:", file=sys.stderr)
        for line in failures:
            print(f"- {line}", file=sys.stderr)
        return 1

    print("OK: all JSON vectors validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
