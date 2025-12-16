from __future__ import annotations

from typing import Any

from .models.common import ErrorEnvelope


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        *,
        message: str | None = None,
        error: ErrorEnvelope | None = None,
        response_body: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.error = error
        self.response_body = response_body

        super().__init__(str(self))

    def __str__(self) -> str:
        if self.error is not None:
            return f"API error {self.status_code}: {self.error.error.code}: {self.error.error.message}"
        if self.message:
            return f"API error {self.status_code}: {self.message}"
        return f"API error {self.status_code}"

