import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


CODEGEN_ROOT = Path(__file__).resolve().parents[1] / "tools" / "codegen" / "python" / "client"
sys.path.insert(0, str(CODEGEN_ROOT))

from patch_client_to_pydantic import _patch_text, _patch_tree, main  # noqa: E402


class TestPatchClientToPydantic(unittest.TestCase):
    def test_patch_text_rewrites_imports_and_model_helpers(self) -> None:
        original = (
            "from ..models.foo import Bar\n"
            "from ..models import Baz\n"
            "payload = req.to_dict()\n"
            "obj = Foo.from_dict(data)\n"
            "payload2 = req.model_dump(by_alias=True, exclude_none=True)\n"
            "payload3 = req.model_dump(by_alias=True)\n"
        )
        updated = _patch_text(original)
        self.assertIn("from arp_standard_model import Bar", updated)
        self.assertIn("from arp_standard_model import Baz", updated)
        self.assertIn(".model_dump(exclude_none=True)", updated)
        self.assertIn(".model_validate(", updated)
        self.assertNotIn("by_alias=True", updated)

    def test_patch_tree_skips_init_and_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service_root = root / "run_gateway"
            service_root.mkdir(parents=True)

            target = service_root / "api.py"
            target.write_text("from ..models.foo import Bar\npayload = req.to_dict()\n", encoding="utf-8")

            init_file = service_root / "__init__.py"
            init_file.write_text("from ..models.foo import Bar\n", encoding="utf-8")

            models_dir = service_root / "models"
            models_dir.mkdir()
            models_file = models_dir / "skip.py"
            models_file.write_text("from ..models.foo import Bar\n", encoding="utf-8")

            _patch_tree(service_root)

            self.assertIn("from arp_standard_model import Bar", target.read_text(encoding="utf-8"))
            self.assertIn("model_dump(exclude_none=True)", target.read_text(encoding="utf-8"))
            self.assertIn("from ..models.foo import Bar", init_file.read_text(encoding="utf-8"))
            self.assertIn("from ..models.foo import Bar", models_file.read_text(encoding="utf-8"))

    def test_main_missing_root_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = Path(tmp) / "missing"
            with patch.object(sys, "argv", ["patch_client_to_pydantic.py", "--root", str(missing_root)]):
                with self.assertRaises(FileNotFoundError):
                    main()

    def test_main_invokes_patch_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for service in ("run_gateway", "node_registry", "selection"):
                (root / service).mkdir(parents=True)

            calls: list[Path] = []

            def record_call(path: Path) -> None:
                calls.append(path)

            with (
                patch("patch_client_to_pydantic._patch_tree", side_effect=record_call),
                patch.object(sys, "argv", ["patch_client_to_pydantic.py", "--root", str(root)]),
            ):
                result = main()

            self.assertEqual(result, 0)
            self.assertEqual([path.name for path in calls], sorted(["run_gateway", "node_registry", "selection"]))


if __name__ == "__main__":
    unittest.main()
