from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class Endpoint:
    method: str
    path_template: str


@dataclass(frozen=True)
class RequiredEndpoints:
    common: list[Endpoint]
    run_gateway: list[Endpoint]
    run_coordinator: list[Endpoint]
    atomic_executor: list[Endpoint]
    composite_executor: list[Endpoint]
    node_registry: list[Endpoint]
    selection: list[Endpoint]
    pdp: list[Endpoint]
    optional: list[Endpoint]


def _parse_endpoint(line: str) -> Endpoint | None:
    match = re.search(r"`([A-Z]+)\s+([^`]+)`", line)
    if not match:
        return None
    return Endpoint(method=match.group(1), path_template=match.group(2))


def _read_text_from_package(rel_path: str) -> str:
    base = resources.files("arp_conformance").joinpath("_spec").joinpath(rel_path)
    return base.read_text(encoding="utf-8")


def _walk_files(root: object, *, suffix: str) -> Iterator[tuple[str, object]]:
    """
    Yield file-like Traversables/Paths under `root` matching `suffix`.

    This avoids relying on `rglob`, which is not guaranteed for all `Traversable` implementations.
    """

    # `Traversable` interface (importlib.resources) and `Path` share `iterdir`, `is_dir`, and `is_file` on
    # concrete implementations, but not in typing.
    stack: list[tuple[str, object]] = [("", root)]
    while stack:
        prefix, node = stack.pop()
        for child in node.iterdir():  # type: ignore[attr-defined]
            name = getattr(child, "name", None)
            if not isinstance(name, str) or not name:
                continue
            rel = f"{prefix}{name}" if not prefix else f"{prefix}/{name}"
            if child.is_dir():  # type: ignore[attr-defined]
                stack.append((rel, child))
            elif child.is_file():  # type: ignore[attr-defined]
                if name.endswith(suffix):
                    yield rel, child


def load_required_endpoints(*, spec_path: Path | None = None, version: str = "v1") -> RequiredEndpoints:
    """
    Load required endpoints from the spec's conformance rules.

    The source of truth is `spec/<version>/conformance/rules/required.md`.
    """

    if spec_path is None:
        text = _read_text_from_package(f"{version}/conformance/rules/required.md")
    else:
        spec_root = normalize_spec_root(spec_path, version=version)
        text = (spec_root / version / "conformance" / "rules" / "required.md").read_text(encoding="utf-8")

    section: str | None = None
    common: list[Endpoint] = []
    run_gateway: list[Endpoint] = []
    run_coordinator: list[Endpoint] = []
    atomic_executor: list[Endpoint] = []
    composite_executor: list[Endpoint] = []
    node_registry: list[Endpoint] = []
    selection: list[Endpoint] = []
    pdp: list[Endpoint] = []
    optional: list[Endpoint] = []

    def target() -> list[Endpoint] | None:
        return {
            "common": common,
            "run_gateway": run_gateway,
            "run_coordinator": run_coordinator,
            "atomic_executor": atomic_executor,
            "composite_executor": composite_executor,
            "node_registry": node_registry,
            "selection": selection,
            "pdp": pdp,
            "optional": optional,
        }.get(section or "")

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("All services MUST implement"):
            section = "common"
            continue
        if line.startswith("Run Gateway MUST implement"):
            section = "run_gateway"
            continue
        if line.startswith("Run Coordinator MUST implement"):
            section = "run_coordinator"
            continue
        if line.startswith("Atomic Executor MUST implement"):
            section = "atomic_executor"
            continue
        if line.startswith("Composite Executor MUST implement"):
            section = "composite_executor"
            continue
        if line.startswith("Node Registry MUST implement"):
            section = "node_registry"
            continue
        if line.startswith("Selection MUST implement"):
            section = "selection"
            continue
        if line.startswith("PDP MUST implement"):
            section = "pdp"
            continue
        if line.startswith("Optional"):
            section = "optional"
            continue

        if not line.startswith("-"):
            continue
        parsed = _parse_endpoint(line)
        bucket = target()
        if parsed is not None and bucket is not None:
            bucket.append(parsed)

    return RequiredEndpoints(
        common=common,
        run_gateway=run_gateway,
        run_coordinator=run_coordinator,
        atomic_executor=atomic_executor,
        composite_executor=composite_executor,
        node_registry=node_registry,
        selection=selection,
        pdp=pdp,
        optional=optional,
    )


def normalize_spec_root(spec_path: Path, *, version: str) -> Path:
    """
    Accept either:
    - a `spec/` directory (containing `<version>/`), or
    - a repo root directory (containing `spec/<version>/`).
    """

    direct = spec_path / version / "schemas"
    if direct.exists():
        return spec_path
    nested = spec_path / "spec" / version / "schemas"
    if nested.exists():
        return spec_path / "spec"
    raise FileNotFoundError(
        f"Could not find {version}/schemas under {spec_path} (expected {direct} or {nested})"
    )


def iter_spec_schema_files(*, spec_path: Path | None = None, version: str = "v1") -> Iterable[tuple[str, str]]:
    """
    Yield `(relative_path, content)` for all JSON schema files under `schemas/`.

    `relative_path` is rooted at `schemas/` (e.g., `schemas/common/health.schema.json`).
    """

    if spec_path is None:
        root = resources.files("arp_conformance").joinpath("_spec").joinpath(version).joinpath("schemas")
        for rel_path, path in _walk_files(root, suffix=".json"):
            yield f"schemas/{rel_path}", path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
        return

    spec_root = normalize_spec_root(spec_path, version=version)
    schemas_root = spec_root / version / "schemas"
    for path in schemas_root.rglob("*.json"):
        rel = f"schemas/{path.relative_to(schemas_root).as_posix()}"
        yield rel, path.read_text(encoding="utf-8")


def iter_spec_openapi_files(*, spec_path: Path | None = None, version: str = "v1") -> Iterable[tuple[str, str]]:
    """
    Yield `(relative_path, content)` for OpenAPI YAML files under `openapi/`.
    """

    if spec_path is None:
        root = resources.files("arp_conformance").joinpath("_spec").joinpath(version).joinpath("openapi")
        for rel_path, path in _walk_files(root, suffix=".yaml"):
            yield f"openapi/{rel_path}", path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
        return

    spec_root = normalize_spec_root(spec_path, version=version)
    openapi_root = spec_root / version / "openapi"
    for path in openapi_root.rglob("*.yaml"):
        rel = f"openapi/{path.relative_to(openapi_root).as_posix()}"
        yield rel, path.read_text(encoding="utf-8")
