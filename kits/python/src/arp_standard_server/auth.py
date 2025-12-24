from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Literal

import anyio
import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError, PyJWTError

from arp_standard_model import Error as ErrorDetail
from arp_standard_model import ErrorEnvelope

AuthMode = Literal["required", "optional", "disabled"]
Principal = dict[str, Any]

principal_var: ContextVar[Principal | None] = ContextVar("arp_principal", default=None)


@dataclass(frozen=True, slots=True)
class AuthSettings:
    mode: AuthMode = "required"
    issuer: str | None = None
    audience: str | None = None
    jwks_uri: str | None = None
    oidc_discovery_url: str | None = None
    algorithms: tuple[str, ...] = ("RS256",)
    clock_skew_seconds: int = 60
    exempt_paths: tuple[str, ...] = ("/v1/health", "/v1/version")
    dev_subject: str = "dev"
    anonymous_subject: str = "anonymous"

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "AuthSettings":
        environ = os.environ if environ is None else environ
        mode = (environ.get("ARP_AUTH_MODE") or "required").strip().lower()
        if mode not in {"required", "optional", "disabled"}:
            raise ValueError(f"Invalid ARP_AUTH_MODE: {mode!r}")

        clock_skew_raw = (environ.get("ARP_AUTH_CLOCK_SKEW_SECONDS") or "60").strip()
        try:
            clock_skew_seconds = int(clock_skew_raw)
        except ValueError as exc:
            raise ValueError(f"Invalid ARP_AUTH_CLOCK_SKEW_SECONDS: {clock_skew_raw!r}") from exc

        algorithms_raw = (environ.get("ARP_AUTH_ALGORITHMS") or "RS256").strip()
        algorithms = tuple(part.strip() for part in algorithms_raw.split(",") if part.strip())
        if not algorithms:
            raise ValueError("ARP_AUTH_ALGORITHMS must include at least one algorithm (for example: RS256)")

        exempt_raw = (environ.get("ARP_AUTH_EXEMPT_PATHS") or "/v1/health,/v1/version").strip()
        exempt_paths = tuple(part.strip() for part in exempt_raw.split(",") if part.strip())
        if not exempt_paths:
            exempt_paths = ("/v1/health", "/v1/version")

        return cls(
            mode=mode,  # type: ignore[arg-type]
            issuer=(environ.get("ARP_AUTH_ISSUER") or None),
            audience=(environ.get("ARP_AUTH_AUDIENCE") or None),
            jwks_uri=(environ.get("ARP_AUTH_JWKS_URI") or None),
            oidc_discovery_url=(environ.get("ARP_AUTH_OIDC_DISCOVERY_URL") or None),
            algorithms=algorithms,
            clock_skew_seconds=clock_skew_seconds,
            exempt_paths=exempt_paths,
            dev_subject=(environ.get("ARP_AUTH_DEV_SUBJECT") or "dev"),
            anonymous_subject=(environ.get("ARP_AUTH_ANONYMOUS_SUBJECT") or "anonymous"),
        )


def _error_envelope(*, code: str, message: str, details: dict[str, Any] | None = None) -> ErrorEnvelope:
    error = ErrorDetail(
        code=code,
        cause=None,
        message=message,
        details=details,
        extensions=None,
        retryable=None,
    )
    return ErrorEnvelope(error=error, extensions=None)


def _bearer_challenge(*, error: str, description: str) -> str:
    escaped = description.replace('"', '\\"')
    return f'Bearer error="{error}", error_description="{escaped}"'


def _unauthorized(*, error: str, message: str, details: dict[str, Any] | None = None) -> JSONResponse:
    envelope = _error_envelope(code="unauthorized", message=message, details=details)
    return JSONResponse(
        status_code=401,
        content=envelope.model_dump(exclude_none=True),
        headers={"WWW-Authenticate": _bearer_challenge(error=error, description=message)},
    )


def _fetch_json(url: str, *, timeout_seconds: float = 5.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
    parsed = json.loads(payload.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a JSON object from {url}")
    return parsed


def _resolve_jwks_uri(settings: AuthSettings) -> str:
    if settings.jwks_uri:
        return settings.jwks_uri

    discovery_url = settings.oidc_discovery_url
    if not discovery_url and settings.issuer:
        discovery_url = settings.issuer.rstrip("/") + "/.well-known/openid-configuration"

    if not discovery_url:
        raise ValueError(
            "JWT auth requires ARP_AUTH_JWKS_URI or ARP_AUTH_ISSUER/ARP_AUTH_OIDC_DISCOVERY_URL "
            "when ARP_AUTH_MODE is not 'disabled'"
        )

    config = _fetch_json(discovery_url)
    jwks_uri = config.get("jwks_uri")
    if not isinstance(jwks_uri, str) or not jwks_uri.strip():
        raise ValueError(f"OIDC discovery document missing jwks_uri: {discovery_url}")
    return jwks_uri


@dataclass(frozen=True, slots=True)
class JwtBearerAuthenticator:
    settings: AuthSettings
    jwks_uri: str = field(init=False)
    jwk_client: PyJWKClient = field(init=False)

    def __post_init__(self) -> None:
        jwks_uri = _resolve_jwks_uri(self.settings)
        object.__setattr__(self, "jwks_uri", jwks_uri)
        object.__setattr__(self, "jwk_client", PyJWKClient(jwks_uri))

    def decode(self, token: str) -> Principal:
        signing_key = self.jwk_client.get_signing_key_from_jwt(token).key
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_aud": bool(self.settings.audience),
            "verify_iss": bool(self.settings.issuer),
        }
        decoded = jwt.decode(
            token,
            signing_key,
            algorithms=list(self.settings.algorithms),
            audience=self.settings.audience,
            issuer=self.settings.issuer,
            options=options,
            leeway=self.settings.clock_skew_seconds,
        )
        if not isinstance(decoded, dict):
            raise jwt.InvalidTokenError("Invalid JWT payload")
        return decoded


def register_auth_middleware(app: FastAPI, *, settings: AuthSettings) -> None:
    exempt_paths = set(settings.exempt_paths)
    authenticator: JwtBearerAuthenticator | None = None

    if settings.mode != "disabled":
        authenticator = JwtBearerAuthenticator(settings)

    @app.middleware("http")
    async def _auth(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.url.path in exempt_paths:
            return await call_next(request)

        if settings.mode == "disabled":
            principal: Principal = {"sub": settings.dev_subject}
            token = principal_var.set(principal)
            request.state.arp_principal = principal
            try:
                return await call_next(request)
            finally:
                principal_var.reset(token)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            if settings.mode == "optional":
                principal = {"sub": settings.anonymous_subject}
                token = principal_var.set(principal)
                request.state.arp_principal = principal
                try:
                    return await call_next(request)
                finally:
                    principal_var.reset(token)
            return _unauthorized(error="invalid_request", message="Missing Authorization header")

        parts = auth_header.strip().split()
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
            return _unauthorized(error="invalid_request", message="Invalid Authorization header")

        bearer_token = parts[1].strip()
        assert authenticator is not None
        try:
            principal = await anyio.to_thread.run_sync(authenticator.decode, bearer_token)
        except jwt.ExpiredSignatureError:
            return _unauthorized(error="invalid_token", message="Token expired")
        except jwt.InvalidAudienceError:
            return _unauthorized(error="invalid_token", message="Invalid token audience")
        except jwt.InvalidIssuerError:
            return _unauthorized(error="invalid_token", message="Invalid token issuer")
        except (PyJWKClientError, urllib.error.URLError):
            return _unauthorized(error="invalid_token", message="Unable to fetch JWKS")
        except PyJWTError:
            return _unauthorized(error="invalid_token", message="Invalid token")

        token = principal_var.set(principal)
        request.state.arp_principal = principal
        try:
            return await call_next(request)
        finally:
            principal_var.reset(token)


def get_principal() -> Principal | None:
    return principal_var.get()

