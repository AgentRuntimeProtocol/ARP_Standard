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
    if pointer in ("", "/", "#", "#/"):
        return document
    if pointer.startswith("#"):
        pointer = pointer[1:]
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


_SCHEMA_KEYS = {
    "$ref",
    "additionalProperties",
    "allOf",
    "anyOf",
    "const",
    "default",
    "enum",
    "exclusiveMaximum",
    "exclusiveMinimum",
    "format",
    "items",
    "maximum",
    "maxItems",
    "maxLength",
    "minimum",
    "minItems",
    "minLength",
    "nullable",
    "oneOf",
    "pattern",
    "properties",
    "required",
    "type",
}


def _is_schema_object(value: dict[str, Any]) -> bool:
    if "$ref" in value:
        return True
    return any(key in value for key in _SCHEMA_KEYS)


def _collect_titled_schemas(value: Any, *, collected: dict[str, dict[str, Any]]) -> None:
    if isinstance(value, list):
        for item in value:
            _collect_titled_schemas(item, collected=collected)
        return

    if not isinstance(value, dict):
        return

    title = value.get("title")
    if isinstance(title, str) and _is_schema_object(value):
        existing = collected.get(title)
        if existing is None:
            collected[title] = value
        elif existing != value:
            raise ValueError(f"Schema title collision for {title}")

    for item in value.values():
        _collect_titled_schemas(item, collected=collected)


def _replace_inline_schemas(
    value: Any,
    *,
    schemas: dict[str, Any],
    title_to_key: dict[str, str],
) -> None:
    if isinstance(value, list):
        for idx, item in enumerate(value):
            if isinstance(item, dict):
                title = item.get("title")
                if isinstance(title, str) and title in title_to_key and _is_schema_object(item):
                    value[idx] = {"$ref": f"#/components/schemas/{title_to_key[title]}"}
                    continue
            _replace_inline_schemas(item, schemas=schemas, title_to_key=title_to_key)
        return

    if not isinstance(value, dict):
        return

    for key, item in list(value.items()):
        if value is schemas:
            if isinstance(item, dict):
                _replace_inline_schemas(item, schemas=schemas, title_to_key=title_to_key)
            continue
        if isinstance(item, dict):
            title = item.get("title")
            if isinstance(title, str) and title in title_to_key and _is_schema_object(item):
                value[key] = {"$ref": f"#/components/schemas/{title_to_key[title]}"}
                continue
            _replace_inline_schemas(item, schemas=schemas, title_to_key=title_to_key)
        elif isinstance(item, list):
            _replace_inline_schemas(item, schemas=schemas, title_to_key=title_to_key)


def _canonicalize_inline_schemas(openapi: dict[str, Any]) -> dict[str, Any]:
    components = openapi.setdefault("components", {})
    schemas = components.setdefault("schemas", {})

    titled: dict[str, dict[str, Any]] = {}
    _collect_titled_schemas(openapi, collected=titled)

    title_to_key: dict[str, str] = {}
    for key, schema in schemas.items():
        if not isinstance(schema, dict):
            continue
        title = schema.get("title")
        if not isinstance(title, str):
            continue
        existing = title_to_key.get(title)
        if existing and existing != key:
            raise ValueError(f"Schema title collision for {title}: {existing} vs {key}")
        title_to_key[title] = key

    for title, schema in titled.items():
        key = title_to_key.get(title)
        if key:
            if schemas[key] != schema:
                raise ValueError(f"Schema title mismatch for {title}")
            continue
        schemas[title] = schema
        title_to_key[title] = title

    _replace_inline_schemas(openapi, schemas=schemas, title_to_key=title_to_key)
    return openapi


def bundle_openapi(source_path: Path) -> dict[str, Any]:
    openapi = _load_yaml(source_path)
    openapi = _resolve_external_refs(openapi, source_path.parent, cache={})
    openapi = _sanitize_for_openapi_3_0(openapi)
    openapi = _canonicalize_inline_schemas(openapi)
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


def _service_prefix(service_name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in service_name.split("_") if part)


def _render_lines(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def generate_facade(*, service: str, bundled_openapi: dict[str, Any], output_dir: Path) -> None:
    operations: list[dict[str, Any]] = []
    service_prefix = _service_prefix(service)
    for path, path_item in (bundled_openapi.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        raw_inherited_params = path_item.get("parameters")
        inherited_params = raw_inherited_params if isinstance(raw_inherited_params, list) else []
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
                    "request_type": f"{service_prefix}{_snake_to_pascal(str(operation_id))}Request",
                }
            )

    operations.sort(key=lambda o: o["operation_id"])
    client_class = _service_client_class(service)

    endpoint_imports: dict[str, set[str]] = {}
    import_models: set[str] = set()
    uses_unset = False

    for op in operations:
        endpoint = _safe_ident(op["operation_id"])
        tag_mod = _sanitize_tag(op["tag"])
        endpoint_imports.setdefault(tag_mod, set()).add(endpoint)

        import_models.update(op["return_models"] | op["body_models"] | {op["request_type"]})

        params = op["params"]
        if any(isinstance(p, dict) and p.get("in") == "query" for p in params):
            uses_unset = True

    # facade.py
    client_lines: list[str] = []
    client_lines.append("from __future__ import annotations")
    client_lines.append("")
    client_lines.append("from typing import Any")
    client_lines.append("")
    client_lines.append("import httpx")
    client_lines.append("")
    client_lines.append("from arp_standard_client.errors import ArpApiError")
    if import_models:
        client_lines.append("from arp_standard_model import (")
        for name in sorted(import_models):
            client_lines.append(f"    {name},")
        client_lines.append(")")
        client_lines.append("")
    for tag_mod, modules in sorted(endpoint_imports.items()):
        client_lines.append(f"from .api.{tag_mod} import (")
        for mod in sorted(modules):
            client_lines.append(f"    {mod},")
        client_lines.append(")")
        client_lines.append("")
    client_lines.append("from .client import AuthenticatedClient as _AuthenticatedClient")
    client_lines.append("from .client import Client as _LowLevelClient")
    client_lines.append("from arp_standard_model import ErrorEnvelope as _ErrorEnvelope")
    client_lines.append("from .types import Response as _Response")
    client_lines.append("from .types import Unset as _Unset")
    if uses_unset:
        client_lines.append("from .types import UNSET as _UNSET")
    client_lines.append("")
    client_lines.extend(
        [
            "def _raise_for_error_envelope(*, envelope: _ErrorEnvelope, status_code: int | None, raw: Any | None) -> None:",
            "    details: Any | None = None",
            "    if not isinstance(envelope.error.details, _Unset):",
            "        details = envelope.error.details",
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
            "        _raise_for_error_envelope(",
            "            envelope=parsed,",
            "            status_code=int(response.status_code),",
            "            raw=parsed.model_dump(exclude_none=True),",
            "        )",
            "    return parsed",
            "",
        ]
    )

    # Client class
    client_lines.append(f"class {client_class}:")
    client_lines.append("    def __init__(")
    client_lines.append("        self,")
    client_lines.append("        base_url: str | None = None,")
    client_lines.append("        *,")
    client_lines.append("        client: _LowLevelClient | _AuthenticatedClient | None = None,")
    client_lines.append("        bearer_token: str | None = None,")
    client_lines.append("        timeout: httpx.Timeout | None = None,")
    client_lines.append("        headers: dict[str, str] | None = None,")
    client_lines.append("        cookies: dict[str, str] | None = None,")
    client_lines.append("        verify_ssl: Any = True,")
    client_lines.append("        follow_redirects: bool = False,")
    client_lines.append("        raise_on_unexpected_status: bool = False,")
    client_lines.append("        httpx_args: dict[str, Any] | None = None,")
    client_lines.append("    ) -> None:")
    client_lines.append("        if client is None:")
    client_lines.append("            if base_url is None:")
    client_lines.append("                raise ValueError(\"base_url is required when client is not provided\")")
    client_lines.append("            headers_dict = {} if headers is None else dict(headers)")
    client_lines.append("            cookies_dict = {} if cookies is None else dict(cookies)")
    client_lines.append("            httpx_args_dict = {} if httpx_args is None else dict(httpx_args)")
    client_lines.append("            if bearer_token is None:")
    client_lines.append("                client = _LowLevelClient(")
    client_lines.append("                    base_url=base_url,")
    client_lines.append("                    timeout=timeout,")
    client_lines.append("                    headers=headers_dict,")
    client_lines.append("                    cookies=cookies_dict,")
    client_lines.append("                    verify_ssl=verify_ssl,")
    client_lines.append("                    follow_redirects=follow_redirects,")
    client_lines.append("                    raise_on_unexpected_status=raise_on_unexpected_status,")
    client_lines.append("                    httpx_args=httpx_args_dict,")
    client_lines.append("                )")
    client_lines.append("            else:")
    client_lines.append("                client = _AuthenticatedClient(")
    client_lines.append("                    base_url=base_url,")
    client_lines.append("                    token=bearer_token,")
    client_lines.append("                    timeout=timeout,")
    client_lines.append("                    headers=headers_dict,")
    client_lines.append("                    cookies=cookies_dict,")
    client_lines.append("                    verify_ssl=verify_ssl,")
    client_lines.append("                    follow_redirects=follow_redirects,")
    client_lines.append("                    raise_on_unexpected_status=raise_on_unexpected_status,")
    client_lines.append("                    httpx_args=httpx_args_dict,")
    client_lines.append("                )")
    client_lines.append("        self._client = client")
    client_lines.append("")
    client_lines.append("    @property")
    client_lines.append("    def raw_client(self) -> _LowLevelClient | _AuthenticatedClient:")
    client_lines.append("        return self._client")
    client_lines.append("")

    for op in operations:
        op_id = op["operation_id"]
        method_name = _safe_ident(op_id)
        request_type = op["request_type"]
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
        return_type = op["return_type"]
        allow_none = bool(op["allow_none"])

        client_lines.append(f"    def {method_name}(self, request: {request_type}) -> {return_type}:")
        if not path_params and not query_params and body_schema is None:
            client_lines.append("        _ = request")
            client_lines.append(f"        resp = {endpoint}.sync_detailed(client=self._client)")
            if allow_none:
                client_lines.append("        _unwrap(resp, allow_none=True)")
                client_lines.append("        return None")
            else:
                client_lines.append("        return _unwrap(resp)")
            client_lines.append("")
            continue

        if path_params or query_params:
            client_lines.append("        params = request.params")

        call_parts: list[str] = []
        for n, _ in path_params:
            call_parts.append(f"{n}=params.{n}")
        for n, _ in query_params:
            call_parts.append(f"{n}=_UNSET if params.{n} is None else params.{n}")
        if body_schema is not None:
            call_parts.append("body=request.body")
        joined = ", ".join(call_parts)
        client_lines.append(f"        resp = {endpoint}.sync_detailed(client=self._client, {joined})")
        if allow_none:
            client_lines.append("        _unwrap(resp, allow_none=True)")
            client_lines.append("        return None")
        else:
            client_lines.append("        return _unwrap(resp)")
        client_lines.append("")

    client_lines.append("__all__ = [")
    client_lines.append(f"    {client_class!r},")
    client_lines.append("]")

    (output_dir / "facade.py").write_text(_render_lines(client_lines), encoding="utf-8")

    # __init__.py (lazy exports to avoid import cycles with arp_standard_model)
    export_map: dict[str, str] = {client_class: ".facade"}
    exported_names = ["ArpApiError", client_class]

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

    client_exports = sorted(name for name, module in export_map.items() if module == ".facade")

    init.append("if TYPE_CHECKING:")
    init.append("    from arp_standard_client.errors import ArpApiError")
    if client_exports:
        init.append(f"    from .facade import {', '.join(client_exports)}")
    init.append("")

    init.extend(
        [
            "def __getattr__(name: str) -> Any:",
            "    if name == \"ArpApiError\":",
            "        from arp_standard_client.errors import ArpApiError as _ArpApiError",
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


def generate_service(*, service: str, openapi_path: Path, output_dir: Path, config_path: Path) -> None:
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
        generate_facade(service=service, bundled_openapi=bundled, output_dir=output_dir)


def _remove_service_models(client_src_root: Path, services: Sequence[str]) -> None:
    for service in services:
        models_dir = client_src_root / service / "models"
        if models_dir.exists():
            shutil.rmtree(models_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1", help="Spec version directory (default: v1)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[4]
    spec_root = repo_root / "spec" / args.version
    openapi_root = spec_root / "openapi"
    config_path = Path(__file__).resolve().parent / "openapi-python-client-config.yml"

    client_src_root = repo_root / "clients" / "python" / "src" / "arp_standard_client"

    services: dict[str, tuple[Path, Path]] = {
        "tool_registry": (
            openapi_root / "tool-registry.openapi.yaml",
            client_src_root / "tool_registry",
        ),
        "runtime": (
            openapi_root / "runtime.openapi.yaml",
            client_src_root / "runtime",
        ),
        "daemon": (
            openapi_root / "daemon.openapi.yaml",
            client_src_root / "daemon",
        ),
    }

    for name, (openapi_path, output_dir) in services.items():
        if not openapi_path.exists():
            raise FileNotFoundError(f"Missing OpenAPI spec for {name}: {openapi_path}")
        print(f"[codegen] {name}: {openapi_path.relative_to(repo_root)} -> {output_dir.relative_to(repo_root)}")
        generate_service(service=name, openapi_path=openapi_path, output_dir=output_dir, config_path=config_path)

    patcher = Path(__file__).resolve().parent / "patch_client_to_pydantic.py"
    subprocess.run([sys.executable, str(patcher), "--root", str(client_src_root)], check=True)
    _remove_service_models(client_src_root, list(services.keys()))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
