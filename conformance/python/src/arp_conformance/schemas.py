from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing import jsonschema as referencing_jsonschema

from arp_conformance.spec_loader import iter_spec_schema_files


def _to_uri(spec_version: str, rel_path: str) -> str:
    return f"arp://spec/{spec_version}/{rel_path}"


@dataclass(frozen=True)
class SchemaRegistry:
    spec_version: str
    store: dict[str, dict[str, Any]]
    registry: Registry

    @classmethod
    def load(cls, *, spec_path: Path | None = None, version: str = "v1") -> "SchemaRegistry":
        store: dict[str, dict[str, Any]] = {}
        for rel_path, content in iter_spec_schema_files(
            spec_path=spec_path,
            version=version,
        ):
            uri = _to_uri(version, rel_path)
            schema = json.loads(content)
            schema.setdefault("$id", uri)
            store[uri] = schema
        registry = Registry().with_resources(
            (uri, Resource.from_contents(schema, default_specification=referencing_jsonschema.DRAFT202012))
            for uri, schema in store.items()
        )
        return cls(spec_version=version, store=store, registry=registry)

    def schema_uri(self, rel_path: str) -> str:
        if not rel_path.startswith("schemas/"):
            raise ValueError(f"Expected schema path rooted at 'schemas/': {rel_path}")
        return _to_uri(self.spec_version, rel_path)

    def load_schema(self, rel_path: str) -> dict[str, Any]:
        uri = self.schema_uri(rel_path)
        schema = self.store.get(uri)
        if schema is None:
            raise KeyError(f"Schema not found: {rel_path}")
        return schema

    def validate(self, instance: Any, *, schema_path: str) -> list[str]:
        schema = self.load_schema(schema_path)
        validator = Draft202012Validator(schema, registry=self.registry)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(getattr(e, "absolute_path", [])))

        def _json_path(err: object) -> str:
            path = getattr(err, "absolute_path", None)
            if not path:
                return "$"
            out = "$"
            for part in path:
                if isinstance(part, int):
                    out += f"[{part}]"
                else:
                    out += f".{part}"
            return out

        return [f"{_json_path(e)}: {e.message}" for e in errors]
