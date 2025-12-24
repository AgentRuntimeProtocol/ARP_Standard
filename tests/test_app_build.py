from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import APIRouter
from fastapi.testclient import TestClient


class TestBuildApp(unittest.TestCase):
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

        import arp_standard_server.app as app_module  # noqa: E402

        cls.app_module = app_module

    @classmethod
    def tearDownClass(cls) -> None:
        for path in cls.paths:
            try:
                sys.path.remove(str(path))
            except ValueError:
                pass

    def setUp(self) -> None:
        self.app_module = self.__class__.app_module

    def test_build_app_uses_env_settings(self) -> None:
        router = APIRouter()

        @router.get("/ping")
        def ping():
            return {"ok": True}

        sentinel = self.app_module.AuthSettings(mode="disabled")
        with (
            patch.object(self.app_module.AuthSettings, "from_env", return_value=sentinel) as from_env,
            patch.object(self.app_module, "register_auth_middleware") as register_auth,
            patch.object(self.app_module, "register_exception_handlers") as register_errors,
        ):
            app = self.app_module.build_app(router=router, title="Test")

        from_env.assert_called_once()
        register_auth.assert_called_once()
        register_errors.assert_called_once()
        self.assertIs(register_auth.call_args.kwargs["settings"], sentinel)

        client = TestClient(app)
        self.assertEqual(client.get("/ping").json(), {"ok": True})

    def test_build_app_uses_provided_settings(self) -> None:
        router = APIRouter()

        @router.get("/ping")
        def ping():
            return {"ok": True}

        sentinel = self.app_module.AuthSettings(mode="disabled")
        with (
            patch.object(self.app_module.AuthSettings, "from_env") as from_env,
            patch.object(self.app_module, "register_auth_middleware") as register_auth,
            patch.object(self.app_module, "register_exception_handlers"),
        ):
            app = self.app_module.build_app(router=router, title="Test", auth_settings=sentinel)

        from_env.assert_not_called()
        self.assertIs(register_auth.call_args.kwargs["settings"], sentinel)

        client = TestClient(app)
        self.assertEqual(client.get("/ping").json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
