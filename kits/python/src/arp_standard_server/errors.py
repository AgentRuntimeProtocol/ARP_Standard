from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from arp_standard_model import Error as ErrorDetail
from arp_standard_model import ErrorEnvelope


class ArpServerError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.retryable = retryable

    def to_envelope(self) -> ErrorEnvelope:
        error = ErrorDetail(
            code=self.code,
            cause=None,
            message=self.message,
            details=self.details,
            extensions=None,
            retryable=self.retryable,
        )
        return ErrorEnvelope(error=error, extensions=None)


def _envelope_response(envelope: ErrorEnvelope, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json", exclude_none=True),
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ArpServerError)
    async def _handle_arp_error(request: Request, exc: ArpServerError) -> JSONResponse:
        return _envelope_response(exc.to_envelope(), exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        error = ArpServerError(
            code="invalid_request",
            message="Request validation failed",
            status_code=400,
            details={"errors": exc.errors()},
        )
        return _envelope_response(error.to_envelope(), error.status_code)

    @app.exception_handler(HTTPException)
    async def _handle_http_exception(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        error = ArpServerError(
            code="http_error",
            message=str(exc.detail),
            status_code=exc.status_code,
        )
        return _envelope_response(error.to_envelope(), error.status_code)

    @app.exception_handler(Exception)
    async def _handle_unexpected_exception(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        error = ArpServerError(
            code="internal_error",
            message="Internal server error",
            status_code=500,
        )
        return _envelope_response(error.to_envelope(), error.status_code)
