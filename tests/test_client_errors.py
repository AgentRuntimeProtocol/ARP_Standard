from __future__ import annotations

import sys
import unittest
from pathlib import Path


class TestClientErrors(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cls.repo_root = repo_root
        cls.paths = [repo_root / "clients" / "python" / "src"]
        for path in cls.paths:
            sys.path.insert(0, str(path))

        import arp_standard_client as client_module  # noqa: E402
        from arp_standard_client.errors import ArpApiError  # noqa: E402

        cls.client_module = client_module
        cls.ArpApiError = ArpApiError

    @classmethod
    def tearDownClass(cls) -> None:
        for path in cls.paths:
            try:
                sys.path.remove(str(path))
            except ValueError:
                pass

    def setUp(self) -> None:
        self.client_module = self.__class__.client_module
        self.ArpApiError = self.__class__.ArpApiError

    def test_arp_api_error_str_without_status(self) -> None:
        error = self.ArpApiError("invalid_request", "bad input")
        self.assertEqual(str(error), "invalid_request: bad input")

    def test_arp_api_error_str_with_status(self) -> None:
        error = self.ArpApiError("unauthorized", "missing token", status_code=401)
        self.assertEqual(str(error), "[401] unauthorized: missing token")

    def test_client_exports_error(self) -> None:
        self.assertIn("ArpApiError", self.client_module.__all__)
        self.assertIs(self.client_module.ArpApiError, self.ArpApiError)


if __name__ == "__main__":
    unittest.main()
