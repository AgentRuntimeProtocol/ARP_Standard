from __future__ import annotations

from typing import Any


class ArpApiError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Any | None = None,
        status_code: int | None = None,
        raw: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code
        self.raw = raw

    def __str__(self) -> str:
        if self.status_code is None:
            return f"{self.code}: {self.message}"
        return f"[{self.status_code}] {self.code}: {self.message}"


__all__ = ["ArpApiError"]
