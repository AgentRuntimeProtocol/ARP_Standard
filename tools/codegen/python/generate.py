#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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


def generate_service(*, openapi_path: Path, output_dir: Path, config_path: Path) -> None:
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
        generate_service(openapi_path=openapi_path, output_dir=output_dir, config_path=config_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
