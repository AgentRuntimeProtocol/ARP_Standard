import json
import unittest
import warnings
from pathlib import Path
from typing import Any

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover - optional in local envs
    jsonschema = None

from pydantic import ValidationError

import arp_standard_model as models


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _schema_for(instance_path: Path, root: Path, schemas_root: Path) -> Path:
    rel = instance_path.relative_to(root)
    return schemas_root / root.name / rel.parent / f"{instance_path.stem}.schema.json"


def _validate_jsonschema(schema_path: Path, instance: Any) -> list[str]:
    schema = _load_json(schema_path)
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


class TestModelEquivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if jsonschema is None:
            raise unittest.SkipTest("jsonschema not installed")

        repo_root = Path(__file__).resolve().parents[1]
        spec_root = repo_root / "spec" / "v1"
        cls.schemas_root = spec_root / "schemas"
        services = [
            "run_gateway",
            "run_coordinator",
            "atomic_executor",
            "composite_executor",
            "node_registry",
            "selection",
            "pdp",
        ]
        cls.valid_roots = [
            spec_root / "conformance" / "json_vectors" / service for service in services
        ]
        cls.invalid_roots = [
            spec_root / "conformance" / "json_vectors_invalid" / service for service in services
        ]
        cls.valid_roots = [root for root in cls.valid_roots if root.exists()]
        cls.invalid_roots = [root for root in cls.invalid_roots if root.exists()]
        if not cls.valid_roots and not cls.invalid_roots:
            raise unittest.SkipTest("No conformance vectors found for v1 spec")

    def _assert_valid(self, instance_path: Path, root: Path) -> None:
        schema_path = _schema_for(instance_path, root, self.schemas_root)
        self.assertTrue(schema_path.exists(), f"Missing schema for {instance_path}")

        instance = _load_json(instance_path)
        errors = _validate_jsonschema(schema_path, instance)
        self.assertFalse(errors, f"jsonschema failed for {instance_path}: {errors}")

        schema = _load_json(schema_path)
        title = schema.get("title")
        self.assertTrue(title, f"Schema missing title: {schema_path}")
        model = getattr(models, title, None)
        self.assertIsNotNone(model, f"Model not found for schema title {title}")

        try:
            model.model_validate(instance)
        except ValidationError as exc:
            self.fail(f"Pydantic rejected valid {instance_path}: {exc}")

    def _assert_invalid(self, instance_path: Path, root: Path) -> None:
        schema_path = _schema_for(instance_path, root, self.schemas_root)
        self.assertTrue(schema_path.exists(), f"Missing schema for {instance_path}")

        instance = _load_json(instance_path)
        errors = _validate_jsonschema(schema_path, instance)
        self.assertTrue(errors, f"jsonschema accepted invalid {instance_path}")

        schema = _load_json(schema_path)
        title = schema.get("title")
        self.assertTrue(title, f"Schema missing title: {schema_path}")
        model = getattr(models, title, None)
        self.assertIsNotNone(model, f"Model not found for schema title {title}")

        with self.assertRaises(ValidationError):
            model.model_validate(instance)

    def test_valid_vectors_match_pydantic(self) -> None:
        for root in self.valid_roots:
            for instance_path in sorted(root.rglob("*.json")):
                self._assert_valid(instance_path, root)

    def test_invalid_vectors_rejected_by_pydantic(self) -> None:
        for root in self.invalid_roots:
            for instance_path in sorted(root.rglob("*.json")):
                self._assert_invalid(instance_path, root)
