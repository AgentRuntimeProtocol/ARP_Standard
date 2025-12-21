from __future__ import annotations

from typing import Callable

from fastapi import Depends
from fastapi.security.api_key import APIKeyHeader

from .errors import ArpServerError


def api_key_dependency(api_key: str, *, header_name: str = "X-API-Key") -> Callable[..., None]:
    header = APIKeyHeader(name=header_name, auto_error=False)

    async def _require_key(key: str | None = Depends(header)) -> None:
        if key != api_key:
            raise ArpServerError(
                code="unauthorized",
                message="Invalid API key",
                status_code=401,
            )

    return _require_key
