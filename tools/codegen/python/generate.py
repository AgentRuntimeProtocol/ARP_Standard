#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import keyword
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ruamel.yaml import YAML


def _to_builtin(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _to_builtin(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_to_builtin(v) for v in value]
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as file:
        data = yaml.load(file)
    return _to_builtin(data)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _json_pointer_get(document: Any, pointer: str) -> Any:
    if pointer in ("", "/"):
        return document
    if pointer.startswith("/"):
        pointer = pointer[1:]
    parts = pointer.split("/") if pointer else []
    current: Any = document
    for raw in parts:
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(key)]
        else:
            current = current[key]
    return current


def _resolve_external_refs(value: Any, base_dir: Path, cache: dict[Path, Any]) -> Any:
    if isinstance(value, list):
        return [_resolve_external_refs(v, base_dir, cache) for v in value]

    if not isinstance(value, dict):
        return value

    if set(value.keys()) == {"$ref"} and isinstance(value["$ref"], str):
        ref = value["$ref"]
        if ref.startswith("#"):
            return value

        path_part, _, frag = ref.partition("#")
        if "://" in path_part:
            raise ValueError(f"Remote $ref not supported in codegen bundler: {ref}")

        target_path = (base_dir / path_part).resolve()
        if target_path not in cache:
            if target_path.suffix.lower() in {".yaml", ".yml"}:
                cache[target_path] = _load_yaml(target_path)
            else:
                cache[target_path] = _load_json(target_path)

        resolved = cache[target_path]
        if frag:
            resolved = _json_pointer_get(resolved, frag)

        resolved = _resolve_external_refs(resolved, target_path.parent, cache)
        return resolved

    return {k: _resolve_external_refs(v, base_dir, cache) for k, v in value.items()}


def _sanitize_for_openapi_3_0(value: Any) -> Any:
    if isinstance(value, list):
        return [_sanitize_for_openapi_3_0(v) for v in value]

    if not isinstance(value, dict):
        return value

    # OpenAPI 3.0 Schema Object does not support patternProperties. For codegen purposes we
    # relax these into a free-form object map.
    if "patternProperties" in value:
        value = dict(value)
        value.pop("patternProperties", None)
        if value.get("additionalProperties") is False:
            value["additionalProperties"] = True

    return {k: _sanitize_for_openapi_3_0(v) for k, v in value.items()}


def _rewrite_content_types_for_codegen(value: Any) -> Any:
    if isinstance(value, list):
        return [_rewrite_content_types_for_codegen(v) for v in value]

    if not isinstance(value, dict):
        return value

    if "content" in value and isinstance(value["content"], dict):
        content = dict(value["content"])
        if "application/x-ndjson" in content and "text/plain" not in content:
            content["text/plain"] = content.pop("application/x-ndjson")
        value = dict(value)
        value["content"] = content

    return {k: _rewrite_content_types_for_codegen(v) for k, v in value.items()}


def bundle_openapi(source_path: Path) -> dict[str, Any]:
    openapi = _load_yaml(source_path)
    openapi = _resolve_external_refs(openapi, source_path.parent, cache={})
    openapi = _sanitize_for_openapi_3_0(openapi)
    openapi = _rewrite_content_types_for_codegen(openapi)
    return openapi


def _generator_exe() -> Path:
    exe = Path(sys.executable).parent / "openapi-python-client"
    if exe.exists():
        return exe
    return Path("openapi-python-client")


def _clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)

_HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


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


def _sanitize_tag(value: str) -> str:
    value = value.strip()
    if not value:
        return "default"
    value = re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_").lower()
    if not value:
        return "default"
    if value[0].isdigit():
        return f"tag_{value}"
    return value


def _sanitize_path_for_endpoint(path: str) -> str:
    value = path.strip("/")
    value = value.replace("/", "_")
    value = value.replace("{", "").replace("}", "")
    value = value.replace("-", "_").replace(":", "")
    value = re.sub(r"[^0-9A-Za-z_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value.lower()


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


def _parse_all_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    exported: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                value = node.value
                if isinstance(value, (ast.List, ast.Tuple)):
                    for elt in value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            exported.add(elt.value)
    return exported


def _parse_shared_model_map(path: Path) -> tuple[set[str], dict[str, str]]:
    exported = _parse_all_names(path)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    origin: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        for alias in node.names:
            if alias.name in exported:
                origin[alias.name] = node.module
    return exported, origin


def _parse_service_model_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.level <= 0:
            continue
        for alias in node.names:
            names.add(alias.name)
    return names


def _pick_success_response(responses: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for code, resp in responses.items():
        if not isinstance(resp, dict):
            continue
        try:
            numeric = int(code)
        except Exception:
            continue
        if 200 <= numeric <= 299:
            candidates.append((numeric, code, resp))
    if not candidates:
        raise ValueError("No 2xx success response found")
    candidates.sort(key=lambda t: t[0])
    _, code, resp = candidates[0]
    return code, resp


def _service_client_class(service_name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in service_name.split("_") if part) + "Client"


def _render_lines(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def generate_facade(*, service: str, bundled_openapi: dict[str, Any], output_dir: Path, sdk_src_root: Path) -> None:
    shared_models_path = sdk_src_root / "models" / "__init__.py"
    shared_model_names, shared_model_origin = _parse_shared_model_map(shared_models_path)

    service_models_path = output_dir / "models" / "__init__.py"
    service_model_names = _parse_service_model_names(service_models_path)

    operations: list[dict[str, Any]] = []
    for path, path_item in (bundled_openapi.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        inherited_params = path_item.get("parameters") if isinstance(path_item.get("parameters"), list) else []
        for http_method, op in path_item.items():
            if http_method.lower() not in _HTTP_METHODS:
                continue
            if not isinstance(op, dict):
                continue
            operation_id = op.get("operationId")
            if not isinstance(operation_id, str) or not operation_id.strip():
                raise ValueError(f"Missing operationId for {http_method.upper()} {path}")

            tags = op.get("tags")
            tag = tags[0] if isinstance(tags, list) and tags else "default"

            params: list[Any] = []
            params.extend(inherited_params)
            if isinstance(op.get("parameters"), list):
                params.extend(op["parameters"])

            _, success_resp = _pick_success_response(op.get("responses") or {})
            success_content = success_resp.get("content")
            allow_none = success_content is None
            return_schema: Any | None = None
            if isinstance(success_content, dict) and success_content:
                media = (
                    success_content.get("application/json")
                    or success_content.get("text/plain")
                    or success_content.get("text/event-stream")
                    or next(iter(success_content.values()))
                )
                if isinstance(media, dict):
                    return_schema = media.get("schema")

            return_type, return_models = ("None", set()) if allow_none else _schema_to_pytype(return_schema)

            request_body = op.get("requestBody")
            body_schema: Any | None = None
            if isinstance(request_body, dict):
                content = request_body.get("content")
                if isinstance(content, dict) and content:
                    media = content.get("application/json") or next(iter(content.values()))
                    if isinstance(media, dict):
                        body_schema = media.get("schema")

            body_type, body_models = _schema_to_pytype(body_schema) if body_schema is not None else ("", set())

            operations.append(
                {
                    "operation_id": str(operation_id),
                    "path": str(path),
                    "http_method": http_method.lower(),
                    "tag": str(tag),
                    "params": params,
                    "return_type": return_type,
                    "return_models": return_models,
                    "allow_none": allow_none,
                    "body_schema": body_schema,
                    "body_type": body_type,
                    "body_models": body_models,
                }
            )

    operations.sort(key=lambda o: o["operation_id"])
    client_class = _service_client_class(service)

    endpoint_imports: dict[str, set[str]] = {}
    import_shared: set[str] = set()
    import_service: set[str] = {"Health", "VersionInfo"}
    body_coerce_models: set[str] = set()
    uses_unset = False

    for op in operations:
        endpoint = _safe_ident(op["operation_id"])
        tag_mod = _sanitize_tag(op["tag"])
        endpoint_imports.setdefault(tag_mod, set()).add(endpoint)

        for model in op["return_models"] | op["body_models"]:
            if model in shared_model_names:
                import_shared.add(model)
            elif model in service_model_names:
                import_service.add(model)

        body_type = op.get("body_type")
        if (
            isinstance(body_type, str)
            and body_type
            and body_type in shared_model_origin
            and body_type in service_model_names
            and shared_model_origin[body_type] != f"arp_sdk.{service}.models"
        ):
            body_coerce_models.add(body_type)

        params = op["params"]
        if any(isinstance(p, dict) and p.get("in") == "query" for p in params):
            uses_unset = True

    # sdk.py
    sdk: list[str] = []
    sdk.append("from __future__ import annotations")
    sdk.append("")
    sdk.append("from dataclasses import dataclass")
    sdk.append("from typing import Any, TypeVar, overload")
    sdk.append("")
    sdk.append("import httpx")
    sdk.append("")
    sdk.append("from arp_sdk.errors import ArpApiError")
    if import_shared:
        sdk.append("from arp_sdk.models import (")
        for name in sorted(import_shared):
            sdk.append(f"    {name},")
        sdk.append(")")
        sdk.append("")
    for tag_mod, modules in sorted(endpoint_imports.items()):
        sdk.append(f"from .api.{tag_mod} import (")
        for mod in sorted(modules):
            sdk.append(f"    {mod},")
        sdk.append(")")
        sdk.append("")
    sdk.append("from .client import Client as _LowLevelClient")
    sdk.append("from .models import ErrorEnvelope as _ErrorEnvelope")
    if import_service:
        sdk.append(f"from .models import {', '.join(sorted(import_service))}")
    if body_coerce_models:
        sdk.append("from .models import (")
        for name in sorted(body_coerce_models):
            sdk.append(f"    {name} as _{name},")
        sdk.append(")")
    sdk.append("from .types import Response as _Response")
    sdk.append("from .types import Unset as _Unset")
    if uses_unset:
        sdk.append("from .types import UNSET as _UNSET")
    sdk.append("")
    sdk.append('T = TypeVar("T")')
    sdk.append("")
    sdk.extend(
        [
            "def _coerce_model(value: Any, target: type[T]) -> T:",
            "    if isinstance(value, target):",
            "        return value",
            '    if hasattr(value, "to_dict") and hasattr(target, "from_dict"):',
            "        return target.from_dict(value.to_dict())  # type: ignore[attr-defined]",
            '    if isinstance(value, dict) and hasattr(target, "from_dict"):',
            "        return target.from_dict(value)  # type: ignore[attr-defined]",
            "    raise TypeError(f\"Cannot coerce {type(value)} to {target}\")",
            "",
            "def _raise_for_error_envelope(*, envelope: _ErrorEnvelope, status_code: int | None, raw: Any | None) -> None:",
            "    details: Any | None = None",
            "    if not isinstance(envelope.error.details, _Unset):",
            "        details = envelope.error.details.to_dict()",
            "    raise ArpApiError(",
            "        code=str(envelope.error.code),",
            "        message=str(envelope.error.message),",
            "        details=details,",
            "        status_code=status_code,",
            "        raw=raw,",
            "    )",
            "",
            "def _unwrap(response: _Response[Any], *, allow_none: bool = False) -> Any:",
            "    parsed = response.parsed",
            "    if parsed is None:",
            "        if allow_none:",
            "            return None",
            "        raise ArpApiError(",
            "            code=\"unexpected_empty_response\",",
            "            message=\"API returned an empty response\",",
            "            status_code=int(response.status_code),",
            "            raw=response.content,",
            "        )",
            "    if isinstance(parsed, _ErrorEnvelope):",
            "        _raise_for_error_envelope(envelope=parsed, status_code=int(response.status_code), raw=parsed.to_dict())",
            "    return parsed",
            "",
        ]
    )

    components = (bundled_openapi.get("components") or {}).get("schemas") or {}

    request_types: list[str] = []
    for op in operations:
        op_id = op["operation_id"]
        request_type = _snake_to_pascal(op_id) + "Request"
        request_types.append(request_type)

        params = op["params"]
        path_params: list[tuple[str, str]] = []
        query_params: list[tuple[str, str]] = []
        for raw in params:
            if not isinstance(raw, dict):
                continue
            if raw.get("in") not in {"path", "query"}:
                continue
            name = _safe_ident(str(raw.get("name", "")))
            schema = raw.get("schema", {})
            pytype, _ = _schema_to_pytype(schema)
            if raw.get("in") == "path":
                path_params.append((name, pytype))
            else:
                query_params.append((name, pytype))

        body_schema = op["body_schema"]
        body_type = op["body_type"]
        body_model_exists = bool(body_type) and body_type in service_model_names

        sdk.append("@dataclass(slots=True)")
        sdk.append(f"class {request_type}:")
        if not path_params and not query_params and body_schema is None:
            sdk.append("    pass")
            sdk.append("")
            continue

        if body_schema is not None and not path_params and not query_params and body_model_exists:
            sdk.append(f"    body: {body_type}")
            sdk.append("")
            continue

        if body_schema is not None and not path_params and not query_params and not body_model_exists:
            # Inline missing body model schema (e.g., anyOf/unsupported shapes).
            schema_name = None
            if isinstance(body_schema, dict):
                ref = body_schema.get("$ref")
                if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                    schema_name = ref.rsplit("/", 1)[-1]

            schema_def = components.get(schema_name) if schema_name else None
            required = set(schema_def.get("required") or []) if isinstance(schema_def, dict) else set()
            properties = dict(schema_def.get("properties") or {}) if isinstance(schema_def, dict) else {}
            any_of = schema_def.get("anyOf") if isinstance(schema_def, dict) else None

            required_props = [(n, s) for n, s in properties.items() if n in required]
            optional_props = [(n, s) for n, s in properties.items() if n not in required]

            for prop_name, prop_schema in [*required_props, *optional_props]:
                py_name = _safe_ident(str(prop_name))
                prop_type, _ = _schema_to_pytype(prop_schema)
                if prop_name in required:
                    sdk.append(f"    {py_name}: {prop_type}")
                else:
                    sdk.append(f"    {py_name}: {prop_type} | None = None")

            sdk.append("")
            if isinstance(any_of, list) and any_of:
                sdk.append("    def __post_init__(self) -> None:")
                sdk.append("        satisfied = False")
                for clause in any_of:
                    if not isinstance(clause, dict):
                        continue
                    req = clause.get("required")
                    if not isinstance(req, list) or not req:
                        continue
                    checks = " and ".join(f"self.{_safe_ident(str(r))} is not None" for r in req)
                    sdk.append(f"        if {checks}:")
                    sdk.append("            satisfied = True")
                sdk.append("        if not satisfied:")
                sdk.append(f"            raise ValueError(\"{request_type} does not satisfy request constraints\")")
                sdk.append("")

            sdk.append("    def to_body(self) -> dict[str, Any]:")
            sdk.append("        body: dict[str, Any] = {}")
            for prop_name in properties.keys():
                py_name = _safe_ident(str(prop_name))
                sdk.append(f"        if self.{py_name} is not None:")
                sdk.append(f"            body[{prop_name!r}] = self.{py_name}")
            sdk.append("        return body")
            sdk.append("")
            continue

        for name, typ in path_params:
            sdk.append(f"    {name}: {typ}")
        for name, typ in query_params:
            sdk.append(f"    {name}: {typ} | None = None")
        if body_schema is not None:
            sdk.append(f"    body: {body_type}")
        sdk.append("")

    # Client class
    sdk.append(f"class {client_class}:")
    sdk.append("    def __init__(")
    sdk.append("        self,")
    sdk.append("        base_url: str | None = None,")
    sdk.append("        *,")
    sdk.append("        client: _LowLevelClient | None = None,")
    sdk.append("        timeout: httpx.Timeout | None = None,")
    sdk.append("        headers: dict[str, str] | None = None,")
    sdk.append("        cookies: dict[str, str] | None = None,")
    sdk.append("        verify_ssl: Any = True,")
    sdk.append("        follow_redirects: bool = False,")
    sdk.append("        raise_on_unexpected_status: bool = False,")
    sdk.append("        httpx_args: dict[str, Any] | None = None,")
    sdk.append("    ) -> None:")
    sdk.append("        if client is None:")
    sdk.append("            if base_url is None:")
    sdk.append("                raise ValueError(\"base_url is required when client is not provided\")")
    sdk.append("            client = _LowLevelClient(")
    sdk.append("                base_url=base_url,")
    sdk.append("                timeout=timeout,")
    sdk.append("                headers={} if headers is None else dict(headers),")
    sdk.append("                cookies={} if cookies is None else dict(cookies),")
    sdk.append("                verify_ssl=verify_ssl,")
    sdk.append("                follow_redirects=follow_redirects,")
    sdk.append("                raise_on_unexpected_status=raise_on_unexpected_status,")
    sdk.append("                httpx_args={} if httpx_args is None else dict(httpx_args),")
    sdk.append("            )")
    sdk.append("        self._client = client")
    sdk.append("")
    sdk.append("    @property")
    sdk.append("    def raw_client(self) -> _LowLevelClient:")
    sdk.append("        return self._client")
    sdk.append("")

    for op in operations:
        op_id = op["operation_id"]
        method_name = _safe_ident(op_id)
        request_type = _snake_to_pascal(op_id) + "Request"
        endpoint = _safe_ident(op_id)

        params = op["params"]
        path_params: list[tuple[str, str]] = []
        query_params: list[tuple[str, str]] = []
        for raw in params:
            if not isinstance(raw, dict):
                continue
            if raw.get("in") not in {"path", "query"}:
                continue
            name = _safe_ident(str(raw.get("name", "")))
            schema = raw.get("schema", {})
            pytype, _ = _schema_to_pytype(schema)
            if raw.get("in") == "path":
                path_params.append((name, pytype))
            else:
                query_params.append((name, pytype))

        body_schema = op["body_schema"]
        body_type = op["body_type"]
        body_model_exists = bool(body_type) and body_type in service_model_names

        return_type = op["return_type"]
        allow_none = bool(op["allow_none"])

        coerce_target: str | None = None
        list_item_target: str | None = None
        if return_type.startswith("list[") and return_type.endswith("]"):
            list_item_target = return_type[len("list[") : -1]
            if list_item_target in shared_model_origin and shared_model_origin[list_item_target] != f"arp_sdk.{service}.models":
                coerce_target = list_item_target
        elif return_type in shared_model_origin and shared_model_origin[return_type] != f"arp_sdk.{service}.models":
            coerce_target = return_type

        body_coerce_target: str | None = None
        if body_type and body_type in body_coerce_models:
            body_coerce_target = body_type

        if not path_params and not query_params and body_schema is None:
            sdk.append("    @overload")
            sdk.append(f"    def {method_name}(self) -> {return_type}: ...")
            sdk.append("")
            sdk.append("    @overload")
            sdk.append(f"    def {method_name}(self, request: {request_type}) -> {return_type}: ...")
            sdk.append("")
            sdk.append(f"    def {method_name}(self, request: {request_type} | None = None) -> {return_type}:")
            sdk.append("        _ = request")
            sdk.append(f"        resp = {endpoint}.sync_detailed(client=self._client)")
            if allow_none:
                sdk.append("        _unwrap(resp, allow_none=True)")
                sdk.append("        return None")
            else:
                sdk.append("        return _unwrap(resp)")
            sdk.append("")
            continue

        if body_schema is not None and not path_params and not query_params and body_model_exists:
            sdk.append("    @overload")
            sdk.append(f"    def {method_name}(self, body: {body_type}) -> {return_type}: ...")
            sdk.append("")
            sdk.append("    @overload")
            sdk.append(f"    def {method_name}(self, body: {request_type}) -> {return_type}: ...")
            sdk.append("")
            sdk.append(f"    def {method_name}(self, body: {request_type} | {body_type}) -> {return_type}:")
            sdk.append(f"        payload = body.body if isinstance(body, {request_type}) else body")
            if body_coerce_target:
                sdk.append(f"        payload = _coerce_model(payload, _{body_coerce_target})")
            sdk.append(f"        resp = {endpoint}.sync_detailed(client=self._client, body=payload)")
            if allow_none:
                sdk.append("        _unwrap(resp, allow_none=True)")
                sdk.append("        return None")
            else:
                sdk.append("        result = _unwrap(resp)")
                if coerce_target:
                    sdk.append(f"        return _coerce_model(result, {coerce_target})")
                else:
                    sdk.append("        return result")
            sdk.append("")
            continue

        if len(path_params) == 1 and not query_params and body_schema is None:
            param_name, param_type = path_params[0]
            sdk.append("    @overload")
            sdk.append(f"    def {method_name}(self, {param_name}: {param_type}) -> {return_type}: ...")
            sdk.append("")
            sdk.append("    @overload")
            sdk.append(f"    def {method_name}(self, {param_name}: {request_type}) -> {return_type}: ...")
            sdk.append("")
            sdk.append(f"    def {method_name}(self, {param_name}: {request_type} | {param_type}) -> {return_type}:")
            sdk.append(
                f"        value = {param_name}.{param_name} if isinstance({param_name}, {request_type}) else {param_name}"
            )
            sdk.append(f"        {param_name} = value")
            sdk.append(f"        resp = {endpoint}.sync_detailed(client=self._client, {param_name}={param_name})")
            if allow_none:
                sdk.append("        _unwrap(resp, allow_none=True)")
                sdk.append("        return None")
            else:
                sdk.append("        result = _unwrap(resp)")
                if coerce_target:
                    sdk.append(f"        return _coerce_model(result, {coerce_target})")
                else:
                    sdk.append("        return result")
            sdk.append("")
            continue

        if query_params and not path_params and body_schema is None:
            kw_sig = ", ".join(f"{n}: {t} | None = None" for n, t in query_params)
            sdk.append("    @overload")
            sdk.append(f"    def {method_name}(self) -> {return_type}: ...")
            sdk.append("")
            sdk.append("    @overload")
            sdk.append(f"    def {method_name}(self, request: {request_type}) -> {return_type}: ...")
            sdk.append("")
            sdk.append("    @overload")
            sdk.append(f"    def {method_name}(self, *, {kw_sig}) -> {return_type}: ...")
            sdk.append("")
            sdk.append(f"    def {method_name}(self, request: {request_type} | None = None, *, {kw_sig}) -> {return_type}:")
            sdk.append("        if request is not None:")
            for n, _ in query_params:
                sdk.append(f"            {n} = request.{n}")
            call_args = ", ".join(f"{n}=_UNSET if {n} is None else {n}" for n, _ in query_params)
            sdk.append(f"        resp = {endpoint}.sync_detailed(client=self._client, {call_args})")
            if allow_none:
                sdk.append("        _unwrap(resp, allow_none=True)")
                sdk.append("        return None")
            else:
                sdk.append("        return _unwrap(resp)")
            sdk.append("")
            continue

        if body_schema is not None and not path_params and not query_params and not body_model_exists:
            sdk.append(f"    def {method_name}(self, request: {request_type}) -> {return_type}:")
            sdk.append("        body = request.to_body()")
            sdk.append(f"        resp = {endpoint}.sync_detailed(client=self._client, body=body)")
            if allow_none:
                sdk.append("        _unwrap(resp, allow_none=True)")
                sdk.append("        return None")
            else:
                sdk.append("        result = _unwrap(resp)")
                if coerce_target:
                    sdk.append(f"        return _coerce_model(result, {coerce_target})")
                else:
                    sdk.append("        return result")
            sdk.append("")
            continue

        sdk.append(f"    def {method_name}(self, request: {request_type}) -> {return_type}:")
        call_parts: list[str] = []
        for n, _ in path_params:
            call_parts.append(f"{n}=request.{n}")
        for n, _ in query_params:
            call_parts.append(f"{n}=_UNSET if request.{n} is None else request.{n}")
        if body_schema is not None:
            call_parts.append("body=request.body")
        joined = ", ".join(call_parts)
        sdk.append(f"        resp = {endpoint}.sync_detailed(client=self._client, {joined})")
        if allow_none:
            sdk.append("        _unwrap(resp, allow_none=True)")
            sdk.append("        return None")
        else:
            sdk.append("        result = _unwrap(resp)")
            if coerce_target:
                sdk.append(f"        return _coerce_model(result, {coerce_target})")
            else:
                sdk.append("        return result")
        sdk.append("")

    sdk.append("__all__ = [")
    sdk.append(f"    {client_class!r},")
    for name in sorted(set(request_types)):
        sdk.append(f"    {name!r},")
    sdk.append("]")

    (output_dir / "sdk.py").write_text(_render_lines(sdk), encoding="utf-8")

    # __init__.py (lazy exports to avoid import cycles with arp_sdk.models)
    export_map: dict[str, str] = {}
    for name in [client_class, *sorted(set(request_types))]:
        export_map[name] = ".sdk"

    model_candidates = set(import_service) | set(import_shared)
    for name in sorted(model_candidates):
        origin = shared_model_origin.get(name)
        if origin is None:
            export_map[name] = ".models"
            continue
        if origin == f"arp_sdk.{service}.models":
            export_map[name] = ".models"
            continue
        export_map[name] = origin

    exported_names = ["ArpApiError", *sorted(export_map.keys())]

    init: list[str] = []
    title = service.replace("_", " ").title()
    init.append(f'"""ARP {title} API facade (preferred) + low-level client package."""')
    init.append("")
    init.append("from __future__ import annotations")
    init.append("")
    init.append("from importlib import import_module")
    init.append("from typing import TYPE_CHECKING, Any")
    init.append("")
    init.append("__all__ = [")
    for name in exported_names:
        init.append(f"    {name!r},")
    init.append("]")
    init.append("")
    init.append("_EXPORT_MAP: dict[str, str] = {")
    for name, module in sorted(export_map.items()):
        init.append(f"    {name!r}: {module!r},")
    init.append("}")
    init.append("")

    sdk_exports = sorted(name for name, module in export_map.items() if module == ".sdk")
    local_model_exports = sorted(name for name, module in export_map.items() if module == ".models")
    foreign_exports: dict[str, list[str]] = {}
    for name, module in export_map.items():
        if not module.startswith("arp_sdk."):
            continue
        foreign_exports.setdefault(module, []).append(name)

    init.append("if TYPE_CHECKING:")
    init.append("    from arp_sdk.errors import ArpApiError")
    if sdk_exports:
        init.append(f"    from .sdk import {', '.join(sdk_exports)}")
    if local_model_exports:
        init.append(f"    from .models import {', '.join(local_model_exports)}")
    for module, names in sorted(foreign_exports.items()):
        init.append(f"    from {module} import {', '.join(sorted(names))}")
    init.append("")

    init.extend(
        [
            "def __getattr__(name: str) -> Any:",
            "    if name == \"ArpApiError\":",
            "        from arp_sdk.errors import ArpApiError as _ArpApiError",
            "",
            "        return _ArpApiError",
            "    module = _EXPORT_MAP.get(name)",
            "    if module is None:",
            "        raise AttributeError(name)",
            "    if module.startswith(\".\"):",
            "        return getattr(import_module(module, __name__), name)",
            "    return getattr(import_module(module), name)",
            "",
        ]
    )

    (output_dir / "__init__.py").write_text(_render_lines(init), encoding="utf-8")


def generate_service(*, service: str, openapi_path: Path, output_dir: Path, config_path: Path, sdk_src_root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="arp-openapi-bundle-") as tmp:
        bundled_path = Path(tmp) / "openapi.bundled.json"
        bundled = bundle_openapi(openapi_path)
        bundled_path.write_text(json.dumps(bundled, indent=2, sort_keys=True), encoding="utf-8")

        _clean_dir(output_dir)

        cmd = [
            str(_generator_exe()),
            "generate",
            "--path",
            str(bundled_path),
            "--meta",
            "none",
            "--config",
            str(config_path),
            "--output-path",
            str(output_dir),
            "--overwrite",
        ]
        subprocess.run(cmd, check=True)
        generate_facade(service=service, bundled_openapi=bundled, output_dir=output_dir, sdk_src_root=sdk_src_root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1beta1", help="Spec version directory (default: v1beta1)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    spec_root = repo_root / "spec" / args.version
    openapi_root = spec_root / "openapi"
    config_path = Path(__file__).resolve().parent / "openapi-python-client-config.yml"

    sdk_src_root = repo_root / "sdks" / "python" / "src" / "arp_sdk"

    services: dict[str, tuple[Path, Path]] = {
        "tool_registry": (
            openapi_root / "tool-registry.openapi.yaml",
            sdk_src_root / "tool_registry",
        ),
        "runtime": (
            openapi_root / "runtime.openapi.yaml",
            sdk_src_root / "runtime",
        ),
        "daemon": (
            openapi_root / "daemon.openapi.yaml",
            sdk_src_root / "daemon",
        ),
    }

    for name, (openapi_path, output_dir) in services.items():
        if not openapi_path.exists():
            raise FileNotFoundError(f"Missing OpenAPI spec for {name}: {openapi_path}")
        print(f"[codegen] {name}: {openapi_path.relative_to(repo_root)} -> {output_dir.relative_to(repo_root)}")
        generate_service(service=name, openapi_path=openapi_path, output_dir=output_dir, config_path=config_path, sdk_src_root=sdk_src_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
