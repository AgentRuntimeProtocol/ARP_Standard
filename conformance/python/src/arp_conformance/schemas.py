from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver

from arp_conformance.spec_loader import iter_spec_schema_files


def _to_uri(spec_version: str, rel_path: str) -> str:
    return f"arp://spec/{spec_version}/{rel_path}"


@dataclass(frozen=True)
class SchemaRegistry:
    spec_version: str
    store: dict[str, dict[str, Any]]

    @classmethod
    def load(cls, *, spec_path: Path | None = None, version: str = "v1") -> "SchemaRegistry":
        store: dict[str, dict[str, Any]] = {}
        for rel_path, content in iter_spec_schema_files(
            spec_path=spec_path,
            version=version,
        ):
            uri = _to_uri(version, rel_path)
            store[uri] = json.loads(content)
        return cls(spec_version=version, store=store)

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
        resolver = RefResolver(base_uri=self.schema_uri(schema_path), referrer=schema, store=self.store)
        validator = Draft202012Validator(schema, resolver=resolver)
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
