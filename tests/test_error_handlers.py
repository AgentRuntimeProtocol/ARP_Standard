from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel


class _ServerTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        generated = repo_root / "models" / "python" / "src" / "arp_standard_model" / "_generated.py"
        requests = repo_root / "models" / "python" / "src" / "arp_standard_model" / "_requests.py"
        if not generated.exists() or not requests.exists():
            raise unittest.SkipTest("Generated models missing; run codegen before tests.")

        cls.repo_root = repo_root
        cls.paths = [
            repo_root / "kits" / "python" / "src",
            repo_root / "models" / "python" / "src",
        ]
        for path in cls.paths:
            sys.path.insert(0, str(path))

        import arp_standard_server.errors as errors  # noqa: E402

        cls.errors = errors

    @classmethod
    def tearDownClass(cls) -> None:
        for path in cls.paths:
            try:
                sys.path.remove(str(path))
            except ValueError:
                pass

    def setUp(self) -> None:
        self.errors = self.__class__.errors


class TestErrorHandlers(_ServerTestBase):
    def setUp(self) -> None:
        super().setUp()
        app = FastAPI()
        self.errors.register_exception_handlers(app)

        class Payload(BaseModel):
            name: str

        @app.get("/arp-error")
        def arp_error():
            raise self.errors.ArpServerError(
                code="conflict",
                message="bad input",
                status_code=409,
                details={"field": "run_id"},
                retryable=True,
            )

        @app.get("/http-error")
        def http_error():
            raise HTTPException(status_code=403, detail="nope")

        @app.get("/unexpected")
        def unexpected():
            raise ValueError("boom")

        @app.post("/validate")
        def validate(payload: Payload):
            return {"ok": True}

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_arp_server_error_envelope(self) -> None:
        response = self.client.get("/arp-error")
        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "conflict")
        self.assertEqual(payload["error"]["message"], "bad input")
        self.assertEqual(payload["error"]["details"], {"field": "run_id"})
        self.assertTrue(payload["error"]["retryable"])

    def test_http_exception_envelope(self) -> None:
        response = self.client.get("/http-error")
        self.assertEqual(response.status_code, 403)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "http_error")
        self.assertEqual(payload["error"]["message"], "nope")

    def test_unexpected_exception_envelope(self) -> None:
        response = self.client.get("/unexpected")
        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "internal_error")
        self.assertEqual(payload["error"]["message"], "Internal server error")

    def test_validation_error_envelope(self) -> None:
        response = self.client.post("/validate", json={})
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "invalid_request")
        self.assertIn("errors", payload["error"]["details"])
        self.assertTrue(payload["error"]["details"]["errors"])


if __name__ == "__main__":
    unittest.main()
