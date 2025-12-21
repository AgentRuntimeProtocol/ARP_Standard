import importlib
import sys
import unittest
from pathlib import Path


class TestModelExports(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.model_src = self.repo_root / "models" / "python" / "src"
        self.generated_path = self.model_src / "arp_standard_model" / "_generated.py"
        self.backup_path = self.generated_path.with_suffix(".py.testbak")
        self.requests_path = self.model_src / "arp_standard_model" / "_requests.py"
        self.requests_backup_path = self.requests_path.with_suffix(".py.testbak")

        sys.path.insert(0, str(self.model_src))

        if self.generated_path.exists():
            if self.backup_path.exists():
                self.backup_path.unlink()
            self.generated_path.replace(self.backup_path)

        self.generated_path.write_text(
            "class Foo:\n"
            "    pass\n"
            "\n"
            "__all__ = [\"Foo\"]\n",
            encoding="utf-8",
        )
        if self.requests_path.exists():
            if self.requests_backup_path.exists():
                self.requests_backup_path.unlink()
            self.requests_path.replace(self.requests_backup_path)
        self.requests_path.write_text(
            "class Bar:\n"
            "    pass\n"
            "\n"
            "__all__ = [\"Bar\"]\n",
            encoding="utf-8",
        )

        importlib.invalidate_caches()
        sys.modules.pop("arp_standard_model", None)
        sys.modules.pop("arp_standard_model._generated", None)
        sys.modules.pop("arp_standard_model._requests", None)

    def tearDown(self) -> None:
        sys.modules.pop("arp_standard_model", None)
        sys.modules.pop("arp_standard_model._generated", None)
        sys.modules.pop("arp_standard_model._requests", None)
        if self.generated_path.exists():
            self.generated_path.unlink()
        if self.backup_path.exists():
            self.backup_path.replace(self.generated_path)
        if self.requests_path.exists():
            self.requests_path.unlink()
        if self.requests_backup_path.exists():
            self.requests_backup_path.replace(self.requests_path)
        try:
            sys.path.remove(str(self.model_src))
        except ValueError:
            pass

    def test_exports_match_generated_all(self) -> None:
        module = importlib.import_module("arp_standard_model")
        self.assertIn("Foo", module.__all__)
        self.assertIn("Bar", module.__all__)
        self.assertTrue(hasattr(module, "Foo"))
        self.assertTrue(hasattr(module, "Bar"))


if __name__ == "__main__":
    unittest.main()
