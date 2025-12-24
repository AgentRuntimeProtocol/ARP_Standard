#!/usr/bin/env python3
from __future__ import annotations

import argparse
import keyword
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


_HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}
_PRIMITIVE_TYPES = {"str", "int", "float", "bool", "Any"}
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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


def _to_builtin(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _to_builtin(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_to_builtin(v) for v in value]
    return value


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


def _snake_to_pascal(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in value.split("_") if part)


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


def _service_prefix(service_name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in service_name.split("_") if part)


def _maybe_body_alias(body_type: str) -> str:
    if not _IDENT_RE.match(body_type):
        return body_type
    if body_type in _PRIMITIVE_TYPES:
        return body_type
    if body_type.endswith("Request"):
        return f"{body_type}Body"
    return f"{body_type}RequestBody"


def _render(lines: list[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"


def _needs_any(*types: str | None) -> bool:
    return any(isinstance(value, str) and "Any" in value for value in types)


def _clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _build_router(service: str, operations: list[dict[str, Any]], output_dir: Path) -> None:
    service_prefix = _service_prefix(service)
    base_class = f"Base{service_prefix}Server"

    import_models: set[str] = set()
    uses_body = False
    uses_query = False
    uses_path = False
    needs_any = False

    for op in operations:
        import_models.add(op["request_type"])
        if op.get("params_name"):
            import_models.add(op["params_name"])
        import_models.update(op["return_models"])
        import_models.update(op["body_models"])
        if op.get("body_type"):
            uses_body = True
        if any(p["in"] == "query" for p in op["params"]):
            uses_query = True
        if any(p["in"] == "path" for p in op["params"]):
            uses_path = True
        param_types = [p["type"] for p in op["params"]]
        needs_any = needs_any or _needs_any(op["return_type"], op.get("body_type", ""), *param_types)

    lines: list[str] = []
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("from inspect import isawaitable")
    typing_imports: list[str] = ["TYPE_CHECKING"]
    if needs_any:
        typing_imports.append("Any")
    lines.append(f"from typing import {', '.join(typing_imports)}")
    lines.append("")
    if uses_body or uses_query or uses_path:
        imports = ["APIRouter"]
        if uses_body:
            imports.append("Body")
        if uses_query:
            imports.append("Query")
        if uses_path:
            imports.append("Path")
        lines.append(f"from fastapi import {', '.join(imports)}")
    else:
        lines.append("from fastapi import APIRouter")
    if import_models:
        lines.append("")
        lines.append("from arp_standard_model import (")
        for name in sorted(import_models):
            lines.append(f"    {name},")
        lines.append(")")
    lines.append("")
    lines.append("")
    lines.append("if TYPE_CHECKING:")
    lines.append(f"    from .server import {base_class}")
    lines.append("")
    lines.append(f"def create_router(server: {base_class}) -> APIRouter:")
    lines.append("    router = APIRouter()")
    lines.append("")

    for op in operations:
        op_id = op["operation_id"]
        method_name = _safe_ident(op_id)
        http_method = op["http_method"]
        path = op["path"]
        return_type = op["return_type"]
        response_model = op["response_model"]
        status_code = op["status_code"]

        decorator = f"@router.{http_method}(\"{path}\""
        if response_model:
            decorator += f", response_model={response_model}"
        decorator += f", status_code={status_code})"
        lines.append(f"    {decorator}")

        signature: list[str] = []
        params = op["params"]
        if params:
            for param in params:
                name = param["name"]
                original = param["original"]
                param_type = param["type"]
                required = param["required"]
                location = param["in"]

                if location == "path":
                    sig = f"{name}: {param_type} = Path(..., alias=\"{original}\")"
                else:
                    if required:
                        sig = f"{name}: {param_type} = Query(..., alias=\"{original}\")"
                    else:
                        sig = f"{name}: {param_type} | None = Query(None, alias=\"{original}\")"
                signature.append(sig)

        body_type = op.get("body_type")
        if body_type:
            body_required = op.get("body_required", False)
            if body_required:
                signature.append(f"body: {body_type} = Body(...)")
            else:
                signature.append(f"body: {body_type} | None = Body(None)")

        lines.append(f"    async def {method_name}(")
        if signature:
            for item in signature:
                lines.append(f"        {item},")
            lines.append(f"    ) -> {return_type}:")
        else:
            lines.append(f"    ) -> {return_type}:")

        params_name = op.get("params_name")
        if params_name:
            lines.append(f"        params = {params_name}(")
            for param in params:
                lines.append(f"            {param['name']}={param['name']},")
            lines.append("        )")

        request_type = op["request_type"]
        if params_name and body_type:
            lines.append(f"        request = {request_type}(params=params, body=body)")
        elif params_name:
            lines.append(f"        request = {request_type}(params=params)")
        elif body_type:
            lines.append(f"        request = {request_type}(body=body)")
        else:
            lines.append(f"        request = {request_type}()")

        lines.append(f"        result = server.{method_name}(request)")
        lines.append("        if isawaitable(result):")
        lines.append("            result = await result")
        if return_type == "None":
            lines.append("        return None")
        else:
            lines.append("        return result")
        lines.append("")

    lines.append("    return router")
    lines.append("")

    (output_dir / "router.py").write_text(_render(lines), encoding="utf-8")


def _build_server(service: str, operations: list[dict[str, Any]], output_dir: Path) -> None:
    service_prefix = _service_prefix(service)
    base_class = f"Base{service_prefix}Server"

    import_models: set[str] = set()
    needs_any = False

    for op in operations:
        import_models.add(op["request_type"])
        import_models.update(op["return_models"])
        needs_any = needs_any or _needs_any(op["return_type"], op.get("body_type", ""))

    lines: list[str] = []
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("import inspect")
    lines.append("from abc import ABC, abstractmethod")
    lines.append("")
    if needs_any:
        lines.append("from typing import Any")
        lines.append("")
    lines.append("from fastapi import FastAPI")
    lines.append("")
    if import_models:
        lines.append("from arp_standard_model import (")
        for name in sorted(import_models):
            lines.append(f"    {name},")
        lines.append(")")
        lines.append("")
    lines.append("from arp_standard_server.app import build_app")
    lines.append("from arp_standard_server.auth import AuthSettings")
    lines.append("from .router import create_router")
    lines.append("")
    lines.append("")
    lines.append(f"class {base_class}(ABC):")

    for op in operations:
        method_name = _safe_ident(op["operation_id"])
        request_type = op["request_type"]
        return_type = op["return_type"]
        lines.append("    @abstractmethod")
        lines.append(f"    async def {method_name}(self, request: {request_type}) -> {return_type}:")
        lines.append("        raise NotImplementedError")
        lines.append("")

    title = f"ARP {service.replace('_', ' ').title()} Server"
    lines.append("    def create_app(")
    lines.append("        self,")
    lines.append("        *,")
    lines.append("        title: str | None = None,")
    lines.append("        auth_settings: AuthSettings | None = None,")
    lines.append("    ) -> FastAPI:")
    lines.append("        if inspect.isabstract(self.__class__):")
    lines.append("            raise TypeError(")
    lines.append(f"                \"{base_class} has unimplemented abstract methods. \"")
    lines.append("                \"Implement all required endpoints before creating the app.\"")
    lines.append("            )")
    lines.append("        return build_app(")
    lines.append("            router=create_router(self),")
    lines.append(f"            title=title or \"{title}\",")
    lines.append("            auth_settings=auth_settings,")
    lines.append("        )")
    lines.append("")

    (output_dir / "server.py").write_text(_render(lines), encoding="utf-8")

    init_lines = [
        "from __future__ import annotations",
        "",
        f"from .server import {base_class}",
        "from .router import create_router",
        "",
        "__all__ = [",
        f"    {base_class!r},",
        "    \"create_router\",",
        "]",
        "",
    ]
    (output_dir / "__init__.py").write_text(_render(init_lines), encoding="utf-8")


def generate_service(service: str, bundled: dict[str, Any], output_root: Path) -> None:
    operations: list[dict[str, Any]] = []
    service_prefix = _service_prefix(service)

    for path, path_item in (bundled.get("paths") or {}).items():
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

            params: list[Any] = []
            params.extend(inherited_params)
            if isinstance(op.get("parameters"), list):
                params.extend(op["parameters"])

            param_fields: list[dict[str, Any]] = []
            for raw in params:
                if not isinstance(raw, dict):
                    continue
                location = raw.get("in")
                if location not in {"path", "query"}:
                    continue
                original = str(raw.get("name", ""))
                name = _safe_ident(original)
                schema = raw.get("schema", {})
                pytype, _ = _schema_to_pytype(schema)
                required = bool(raw.get("required")) or location == "path"
                param_fields.append(
                    {
                        "name": name,
                        "original": original,
                        "type": pytype,
                        "required": required,
                        "in": location,
                    }
                )

            params_name: str | None = None
            if param_fields:
                params_name = f"{service_prefix}{_snake_to_pascal(str(operation_id))}Params"

            success_code, success_resp = _pick_success_response(op.get("responses") or {})
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

            response_model: str | None
            if allow_none or return_type == "Any":
                response_model = None
            else:
                response_model = return_type

            body_required = False
            body_schema: Any | None = None
            request_body = op.get("requestBody")
            if isinstance(request_body, dict):
                body_required = bool(request_body.get("required"))
                content = request_body.get("content")
                if isinstance(content, dict) and content:
                    media = content.get("application/json") or next(iter(content.values()))
                    if isinstance(media, dict):
                        body_schema = media.get("schema")

            body_type: str | None = None
            body_models: set[str] = set()
            if body_schema is not None:
                body_type, body_models = _schema_to_pytype(body_schema)
                body_type = _maybe_body_alias(body_type)
                if body_type != "Any" and _IDENT_RE.match(body_type):
                    body_models = {body_type}

            request_type = f"{service_prefix}{_snake_to_pascal(str(operation_id))}Request"

            status_code = int(success_code)

            operations.append(
                {
                    "operation_id": str(operation_id),
                    "http_method": http_method.lower(),
                    "path": str(path),
                    "params": param_fields,
                    "params_name": params_name,
                    "request_type": request_type,
                    "body_type": body_type,
                    "body_models": body_models,
                    "body_required": body_required,
                    "return_type": return_type,
                    "return_models": return_models,
                    "response_model": response_model,
                    "status_code": status_code,
                }
            )

    operations.sort(key=lambda item: item["operation_id"])

    output_dir = output_root / service
    _clean_dir(output_dir)
    _build_router(service, operations, output_dir)
    _build_server(service, operations, output_dir)


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

    output_root = repo_root / "kits" / "python" / "src" / "arp_standard_server"
    output_root.mkdir(parents=True, exist_ok=True)

    for name, path in services.items():
        bundled = _load_bundle(path)
        bundled = _to_builtin(bundled)
        generate_service(name, bundled, output_root)

    print(f"[codegen] server -> {output_root.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
