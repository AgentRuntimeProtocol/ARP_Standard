from __future__ import annotations

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from jwt import ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError, InvalidTokenError
from jwt.exceptions import PyJWKClientError


class _AuthTestBase(unittest.TestCase):
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

        import arp_standard_server.auth as auth  # noqa: E402

        cls.auth = auth

    @classmethod
    def tearDownClass(cls) -> None:
        for path in cls.paths:
            try:
                sys.path.remove(str(path))
            except ValueError:
                pass

    def setUp(self) -> None:
        self.auth = self.__class__.auth

    def _build_app(self, settings):  # type: ignore[no-untyped-def]
        auth = self.auth
        app = FastAPI()

        @app.get("/v1/health")
        def health():
            return {"principal": auth.get_principal()}

        @app.get("/v1/protected")
        def protected(request: Request):
            return {
                "principal": request.state.arp_principal,
                "context": auth.get_principal(),
            }

        auth.register_auth_middleware(app, settings=settings)
        return app


class TestAuthMiddleware(_AuthTestBase):
    def test_required_missing_header_returns_401(self) -> None:
        class StubAuthenticator:
            def __init__(self, settings) -> None:
                self.settings = settings

            def decode(self, token: str):
                return {"sub": "user"}

        settings = self.auth.AuthSettings(mode="required")
        with patch.object(self.auth, "JwtBearerAuthenticator", StubAuthenticator):
            client = TestClient(self._build_app(settings))
            response = client.get("/v1/protected")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.headers.get("WWW-Authenticate"),
            'Bearer error="invalid_request", error_description="Missing Authorization header"',
        )
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "unauthorized")
        self.assertEqual(payload["error"]["message"], "Missing Authorization header")

    def test_required_invalid_header_returns_401(self) -> None:
        class StubAuthenticator:
            def __init__(self, settings) -> None:
                self.settings = settings

            def decode(self, token: str):
                return {"sub": "user"}

        settings = self.auth.AuthSettings(mode="required")
        with patch.object(self.auth, "JwtBearerAuthenticator", StubAuthenticator):
            client = TestClient(self._build_app(settings))
            response = client.get("/v1/protected", headers={"Authorization": "Basic abc"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.headers.get("WWW-Authenticate"),
            'Bearer error="invalid_request", error_description="Invalid Authorization header"',
        )

    def test_optional_mode_allows_missing_auth(self) -> None:
        class StubAuthenticator:
            def __init__(self, settings) -> None:
                self.settings = settings

            def decode(self, token: str):
                return {"sub": "user"}

        settings = self.auth.AuthSettings(mode="optional", anonymous_subject="anon")
        with patch.object(self.auth, "JwtBearerAuthenticator", StubAuthenticator):
            client = TestClient(self._build_app(settings))
            response = client.get("/v1/protected")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["principal"]["sub"], "anon")
        self.assertEqual(payload["context"]["sub"], "anon")

    def test_disabled_mode_sets_dev_subject(self) -> None:
        settings = self.auth.AuthSettings(mode="disabled", dev_subject="dev-user")
        client = TestClient(self._build_app(settings))
        response = client.get("/v1/protected")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["principal"]["sub"], "dev-user")
        self.assertEqual(payload["context"]["sub"], "dev-user")

    def test_exempt_path_skips_auth(self) -> None:
        class StubAuthenticator:
            def __init__(self, settings) -> None:
                self.settings = settings

            def decode(self, token: str):
                return {"sub": "user"}

        settings = self.auth.AuthSettings(mode="required")
        with patch.object(self.auth, "JwtBearerAuthenticator", StubAuthenticator):
            client = TestClient(self._build_app(settings))
            response = client.get("/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["principal"])

    def test_valid_token_sets_principal(self) -> None:
        class StubAuthenticator:
            def __init__(self, settings) -> None:
                self.settings = settings

            def decode(self, token: str):
                return {"sub": "user", "scope": "read"}

        settings = self.auth.AuthSettings(mode="required")
        with patch.object(self.auth, "JwtBearerAuthenticator", StubAuthenticator):
            client = TestClient(self._build_app(settings))
            response = client.get("/v1/protected", headers={"Authorization": "Bearer token"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["principal"]["sub"], "user")
        self.assertEqual(payload["context"]["scope"], "read")

    def test_invalid_tokens_map_to_unauthorized(self) -> None:
        settings = self.auth.AuthSettings(mode="required")
        cases = [
            (ExpiredSignatureError(), "Token expired"),
            (InvalidAudienceError("bad"), "Invalid token audience"),
            (InvalidIssuerError("bad"), "Invalid token issuer"),
            (PyJWKClientError("fail"), "Unable to fetch JWKS"),
            (urllib.error.URLError("fail"), "Unable to fetch JWKS"),
            (InvalidTokenError("bad"), "Invalid token"),
        ]

        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                class StubAuthenticator:
                    def __init__(self, settings) -> None:
                        self.settings = settings

                    def decode(self, token: str):
                        raise error

                with patch.object(self.auth, "JwtBearerAuthenticator", StubAuthenticator):
                    client = TestClient(self._build_app(settings))
                    response = client.get("/v1/protected", headers={"Authorization": "Bearer token"})

                self.assertEqual(response.status_code, 401)
                self.assertIn('Bearer error="invalid_token"', response.headers.get("WWW-Authenticate", ""))
                self.assertEqual(response.json()["error"]["message"], expected)


class TestAuthSettings(_AuthTestBase):
    def test_from_env_defaults(self) -> None:
        settings = self.auth.AuthSettings.from_env({})
        self.assertEqual(settings.mode, "required")
        self.assertEqual(settings.algorithms, ("RS256",))
        self.assertEqual(settings.clock_skew_seconds, 60)
        self.assertEqual(settings.exempt_paths, ("/v1/health", "/v1/version"))

    def test_from_env_dev_insecure_profile_sets_disabled(self) -> None:
        settings = self.auth.AuthSettings.from_env({"ARP_AUTH_PROFILE": "dev-insecure"})
        self.assertEqual(settings.mode, "disabled")

    def test_from_env_dev_secure_keycloak_profile_sets_defaults(self) -> None:
        settings = self.auth.AuthSettings.from_env(
            {"ARP_AUTH_PROFILE": "dev-secure-keycloak", "ARP_AUTH_SERVICE_ID": "arp-run-gateway"}
        )
        self.assertEqual(settings.mode, "required")
        self.assertEqual(settings.issuer, "http://localhost:8080/realms/arp-dev")
        self.assertEqual(settings.audience, "arp-run-gateway")

    def test_from_env_dev_secure_keycloak_profile_requires_audience(self) -> None:
        with self.assertRaises(ValueError):
            self.auth.AuthSettings.from_env({"ARP_AUTH_PROFILE": "dev-secure-keycloak"})

    def test_from_env_invalid_profile_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.auth.AuthSettings.from_env({"ARP_AUTH_PROFILE": "nope"})

    def test_from_env_invalid_mode(self) -> None:
        with self.assertRaises(ValueError):
            self.auth.AuthSettings.from_env({"ARP_AUTH_MODE": "invalid"})

    def test_from_env_invalid_clock_skew(self) -> None:
        with self.assertRaises(ValueError):
            self.auth.AuthSettings.from_env({"ARP_AUTH_CLOCK_SKEW_SECONDS": "bad"})

    def test_from_env_requires_algorithms(self) -> None:
        with self.assertRaises(ValueError):
            self.auth.AuthSettings.from_env({"ARP_AUTH_ALGORITHMS": " , "})

    def test_from_env_custom_exempt_paths(self) -> None:
        settings = self.auth.AuthSettings.from_env(
            {"ARP_AUTH_EXEMPT_PATHS": "/v1/health, /v1/ping"}
        )
        self.assertEqual(settings.exempt_paths, ("/v1/health", "/v1/ping"))

    def test_resolve_jwks_uri_prefers_direct(self) -> None:
        settings = self.auth.AuthSettings(jwks_uri="https://jwks.example.com")
        self.assertEqual(self.auth._resolve_jwks_uri(settings), "https://jwks.example.com")

    def test_resolve_jwks_uri_from_discovery(self) -> None:
        settings = self.auth.AuthSettings(issuer="https://issuer.example.com")
        with patch.object(self.auth, "_fetch_json", return_value={"jwks_uri": "https://jwks"}):
            self.assertEqual(self.auth._resolve_jwks_uri(settings), "https://jwks")

    def test_resolve_jwks_uri_requires_discovery(self) -> None:
        settings = self.auth.AuthSettings(issuer=None, jwks_uri=None, oidc_discovery_url=None)
        with self.assertRaises(ValueError):
            self.auth._resolve_jwks_uri(settings)

    def test_resolve_jwks_uri_requires_jwks_uri(self) -> None:
        settings = self.auth.AuthSettings(issuer="https://issuer.example.com")
        with patch.object(self.auth, "_fetch_json", return_value={}):
            with self.assertRaises(ValueError):
                self.auth._resolve_jwks_uri(settings)

    def test_fetch_json_reads_object(self) -> None:
        class DummyResponse:
            def __init__(self, payload: bytes) -> None:
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        payload = b'{"jwks_uri": "https://jwks.example.com"}'
        with patch.object(
            self.auth.urllib.request,
            "urlopen",
            return_value=DummyResponse(payload),
        ):
            result = self.auth._fetch_json("https://example.com/.well-known/openid-configuration")
        self.assertEqual(result["jwks_uri"], "https://jwks.example.com")

    def test_fetch_json_rejects_non_object(self) -> None:
        class DummyResponse:
            def __init__(self, payload: bytes) -> None:
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        payload = b'["not-an-object"]'
        with patch.object(
            self.auth.urllib.request,
            "urlopen",
            return_value=DummyResponse(payload),
        ):
            with self.assertRaises(ValueError):
                self.auth._fetch_json("https://example.com/.well-known/openid-configuration")

    def test_bearer_challenge_escapes_quotes(self) -> None:
        header = self.auth._bearer_challenge(
            error="invalid_token",
            description='token "expired"',
        )
        self.assertIn('\\"', header)


if __name__ == "__main__":
    unittest.main()
