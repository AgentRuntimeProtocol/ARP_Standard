import sys
import unittest
from pathlib import Path


CODEGEN_ROOT = Path(__file__).resolve().parents[1] / "tools" / "codegen" / "python" / "client"
sys.path.insert(0, str(CODEGEN_ROOT))

from patch_client_to_pydantic import _patch_text  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
