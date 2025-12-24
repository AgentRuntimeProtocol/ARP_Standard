#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import keyword
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _load_bundle(openapi_path: Path) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[4]
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


def _merge_schemas(target: dict[str, Any], source: dict[str, Any], *, label: str, collisions: dict[str, str]) -> None:
    for name, schema in source.items():
        if name in target:
            if target[name] != schema:
                prev = collisions.get(name, "unknown")
                raise SystemExit(f"Schema collision for {name}: {prev} vs {label}")
            continue
        target[name] = schema
        collisions[name] = label


def _snake_to_pascal(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in value.split("_") if part)


def _safe_ident(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        value = "value"
    if value[0].isdigit():
        value = f"_{value}"
    if keyword.iskeyword(value):
        value += "_"
    return value


def _schema_to_pytype(schema: Any) -> tuple[str, set[str]]:
    if not isinstance(schema, dict):
        return "Any", set()

    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        name = ref.rsplit("/", 1)[-1]
        return name, {name}

    schema_type = schema.get("type")
    if schema_type == "string":
        return "str", set()
    if schema_type == "integer":
        return "int", set()
    if schema_type == "number":
        return "float", set()
    if schema_type == "boolean":
        return "bool", set()
    if schema_type == "array":
        item_type, item_models = _schema_to_pytype(schema.get("items", {}))
        return f"list[{item_type}]", item_models
    if schema_type == "object":
        return "dict[str, Any]", set()

    return "Any", set()


def _service_prefix(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in value.split("_") if part)


def _render(lines: list[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"


_HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}
_FIELD_DEFAULT_RE = re.compile(r"Field\((\s*)None(\s*[,)])")
_NUMBERED_CLASS_RE = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*\d+)\b", re.MULTILINE)
_ALLOWED_NUMBERED_CLASSES = {"ToolInvocationRequest1", "ToolInvocationRequest2"}
_ENUM_CLASS_RE = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\(Enum\):", re.MULTILINE)


def _rewrite_optional_field_defaults(path: Path) -> None:
    """Ensure optional Field(None, ...) uses explicit default for type checkers."""
    text = path.read_text(encoding="utf-8")
    updated = _FIELD_DEFAULT_RE.sub(r"Field(\1default=None\2", text)
    if updated != text:
        path.write_text(updated, encoding="utf-8")


def _guard_numbered_model_names(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    names = sorted({match.group(1) for match in _NUMBERED_CLASS_RE.finditer(text)})
    unexpected = [name for name in names if name not in _ALLOWED_NUMBERED_CLASSES]
    if unexpected:
        raise SystemExit(
            "Generated models include unexpected numbered classes: "
            + ", ".join(unexpected)
        )


def _guard_enum_classes(path: Path, *, component_names: set[str]) -> None:
    text = path.read_text(encoding="utf-8")
    enum_names = sorted({match.group(1) for match in _ENUM_CLASS_RE.finditer(text)})
    unexpected = [name for name in enum_names if name not in component_names]
    if unexpected:
        raise SystemExit(
            "Generated enum classes are not declared in components: "
            + ", ".join(unexpected)
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1", help="Spec version directory (default: v1)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[4]
    spec_root = repo_root / "spec" / args.version
    openapi_root = spec_root / "openapi"

    services = {
        "runtime": openapi_root / "runtime.openapi.yaml",
        "tool_registry": openapi_root / "tool-registry.openapi.yaml",
        "daemon": openapi_root / "daemon.openapi.yaml",
    }
    for name, path in services.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing OpenAPI spec for {name}: {path}")

    merged_schemas: dict[str, Any] = {}
    collisions: dict[str, str] = {}

    for name, path in services.items():
        bundled = _load_bundle(path)
        schemas = (bundled.get("components") or {}).get("schemas") or {}
        if not isinstance(schemas, dict):
            raise SystemExit(f"Invalid schemas section in {path}")
        _merge_schemas(merged_schemas, schemas, label=name, collisions=collisions)

    component_names = set(merged_schemas.keys())

    combined = {
        "openapi": "3.0.3",
        "info": {"title": "ARP Standard Models", "version": args.version},
        "paths": {},
        "components": {"schemas": merged_schemas},
    }

    output_path = repo_root / "models" / "python" / "src" / "arp_standard_model" / "_generated.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="arp-models-") as tmp:
        bundled_path = Path(tmp) / "openapi.models.json"
        bundled_path.write_text(json.dumps(combined, indent=2, sort_keys=True), encoding="utf-8")

        cmd = [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input",
            str(bundled_path),
            "--input-file-type",
            "openapi",
            "--output",
            str(output_path),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.11",
            "--use-union-operator",
            "--reuse-model",
            "--strict-types",
            "str",
            "bytes",
            "int",
            "float",
            "bool",
        ]
        subprocess.run(cmd, check=True)

    _rewrite_optional_field_defaults(output_path)
    _guard_numbered_model_names(output_path)
    _guard_enum_classes(output_path, component_names=component_names)

    request_models: list[tuple[str, str | None, str | None, bool]] = []
    params_models: list[tuple[str, list[tuple[str, str, bool]]]] = []
    body_aliases: dict[str, str] = {}
    used_names: set[str] = set()

    for service, path in services.items():
        bundled = _load_bundle(path)
        paths = bundled.get("paths") or {}
        if not isinstance(paths, dict):
            raise SystemExit(f"Invalid paths section in {path}")

        for path_item in paths.values():
            if not isinstance(path_item, dict):
                continue
            inherited_params = path_item.get("parameters")
            inherited_params = inherited_params if isinstance(inherited_params, list) else []

            for method, op in path_item.items():
                if method.lower() not in _HTTP_METHODS:
                    continue
                if not isinstance(op, dict):
                    continue
                operation_id = op.get("operationId")
                if not isinstance(operation_id, str) or not operation_id.strip():
                    raise SystemExit(f"Missing operationId in {path}")

                params: list[Any] = []
                params.extend(inherited_params)
                if isinstance(op.get("parameters"), list):
                    params.extend(op["parameters"])

                param_fields: list[tuple[str, str, bool]] = []
                for raw in params:
                    if not isinstance(raw, dict):
                        continue
                    if raw.get("in") not in {"path", "query"}:
                        continue
                    name = _safe_ident(str(raw.get("name", "")))
                    schema = raw.get("schema", {})
                    pytype, _ = _schema_to_pytype(schema)
                    required = bool(raw.get("required")) or raw.get("in") == "path"
                    param_fields.append((name, pytype, required))

                params_name: str | None = None
                if param_fields:
                    params_name = f"{_service_prefix(service)}{_snake_to_pascal(operation_id)}Params"
                    if params_name in used_names:
                        raise SystemExit(f"Duplicate params model name: {params_name}")
                    used_names.add(params_name)
                    params_models.append((params_name, param_fields))

                body_schema: Any | None = None
                body_required = False
                request_body = op.get("requestBody")
                if isinstance(request_body, dict):
                    body_required = bool(request_body.get("required"))
                    content = request_body.get("content")
                    if isinstance(content, dict) and content:
                        media = content.get("application/json") or next(iter(content.values()))
                        if isinstance(media, dict):
                            body_schema = media.get("schema")

                body_type: str | None = None
                if body_schema is not None:
                    body_type, _ = _schema_to_pytype(body_schema)
                    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", body_type):
                        if body_type.endswith("Request"):
                            alias = f"{body_type}Body"
                        else:
                            alias = f"{body_type}RequestBody"
                        existing = body_aliases.get(alias)
                        if existing and existing != body_type:
                            raise SystemExit(f"Request body alias collision for {alias}: {existing} vs {body_type}")
                        body_aliases[alias] = body_type
                        body_type = alias

                request_name = f"{_service_prefix(service)}{_snake_to_pascal(operation_id)}Request"
                if request_name in used_names:
                    raise SystemExit(f"Duplicate request model name: {request_name}")
                used_names.add(request_name)
                request_models.append((request_name, params_name, body_type, body_required))

    requests_path = repo_root / "models" / "python" / "src" / "arp_standard_model" / "_requests.py"
    requests_path.parent.mkdir(parents=True, exist_ok=True)

    request_lines: list[str] = []
    request_lines.append("from __future__ import annotations")
    request_lines.append("")
    request_lines.append("from typing import Any")
    request_lines.append("")
    request_lines.append("from pydantic import BaseModel")
    if body_aliases:
        request_lines.append("")
        request_lines.append("from ._generated import (")
        for alias_target in sorted(set(body_aliases.values())):
            request_lines.append(f"    {alias_target},")
        request_lines.append(")")
    request_lines.append("")

    for alias_name, target in sorted(body_aliases.items()):
        request_lines.append(f"{alias_name} = {target}")
    if body_aliases:
        request_lines.append("")

    for name, fields in params_models:
        request_lines.append(f"class {name}(BaseModel):")
        if not fields:
            request_lines.append("    pass")
        else:
            for field_name, field_type, required in fields:
                if required:
                    request_lines.append(f"    {field_name}: {field_type}")
                else:
                    request_lines.append(f"    {field_name}: {field_type} | None = None")
        request_lines.append("")

    for name, params_name, body_type, body_required in request_models:
        request_lines.append(f"class {name}(BaseModel):")
        if not params_name and not body_type:
            request_lines.append("    pass")
            request_lines.append("")
            continue
        if params_name:
            request_lines.append(f"    params: {params_name}")
        if body_type:
            if body_required:
                request_lines.append(f"    body: {body_type}")
            else:
                request_lines.append(f"    body: {body_type} | None = None")
        request_lines.append("")

    all_names = [
        *sorted(body_aliases.keys()),
        *[name for name, _ in params_models],
        *[name for name, _, _, _ in request_models],
    ]
    request_lines.append("__all__ = [")
    for name in all_names:
        request_lines.append(f"    {name!r},")
    request_lines.append("]")
    request_lines.append("")

    requests_path.write_text(_render(request_lines), encoding="utf-8")

    print(f"[codegen] models -> {output_path.relative_to(repo_root)}")
    print(f"[codegen] requests -> {requests_path.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
