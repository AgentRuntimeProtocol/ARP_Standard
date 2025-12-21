import sys
import unittest
from pathlib import Path


class TestServerErrors(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.paths = [
            self.repo_root / "kits" / "python" / "src",
            self.repo_root / "models" / "python" / "src",
        ]
        for path in self.paths:
            sys.path.insert(0, str(path))
        self.generated_model = (
            self.repo_root
            / "models"
            / "python"
            / "src"
            / "arp_standard_model"
            / "_generated.py"
        )
        self.request_model = (
            self.repo_root
            / "models"
            / "python"
            / "src"
            / "arp_standard_model"
            / "_requests.py"
        )

    def tearDown(self) -> None:
        for path in self.paths:
            try:
                sys.path.remove(str(path))
            except ValueError:
                pass

    def test_error_envelope(self) -> None:
        if not self.generated_model.exists() or not self.request_model.exists():
            self.skipTest("Generated models missing; run codegen before tests.")
        from arp_standard_server.errors import ArpServerError
        from arp_standard_model import ErrorEnvelope

        error = ArpServerError(
            code="invalid_request",
            message="bad input",
            status_code=400,
            details={"field": "run_id"},
        )
        envelope = error.to_envelope()
        self.assertIsInstance(envelope, ErrorEnvelope)
        self.assertEqual(envelope.error.code, "invalid_request")
        self.assertEqual(envelope.error.message, "bad input")
        self.assertEqual(envelope.error.details, {"field": "run_id"})


if __name__ == "__main__":
    unittest.main()
