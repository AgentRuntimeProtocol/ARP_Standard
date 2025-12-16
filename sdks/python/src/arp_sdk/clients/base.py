from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ..errors import ApiError
from ..models.common import ErrorEnvelope


def _looks_like_json(content_type: str) -> bool:
    if not content_type:
        return False
    mime = content_type.split(";", 1)[0].strip().lower()
    return mime == "application/json" or mime.endswith("+json") or mime == "text/json"


class BaseClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 30.0,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url if base_url.endswith("/") else base_url + "/"
        self._timeout = timeout
        self._default_headers = dict(default_headers or {})

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        url = urllib.parse.urljoin(self._base_url, path.lstrip("/"))

        req_headers = {"Accept": "application/json", **self._default_headers}
        if headers:
            req_headers.update(headers)

        data: bytes | None = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")

        request = urllib.request.Request(url=url, data=data, method=method.upper())
        for key, value in req_headers.items():
            request.add_header(key, value)

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                status = response.getcode()
                resp_headers = dict(response.headers.items())
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            resp_headers = dict(exc.headers.items())
            raw = exc.read()
        except urllib.error.URLError as exc:
            raise ApiError(0, message=str(exc)) from exc

        if status == 204:
            return None

        content_type = resp_headers.get("Content-Type", "")
        if not _looks_like_json(content_type):
            text = raw.decode("utf-8", errors="replace")
            if status >= 400:
                raise ApiError(status, message=text, response_body=text)
            return text

        try:
            payload = json.loads(raw.decode("utf-8")) if raw else None
        except json.JSONDecodeError as exc:
            if status >= 400:
                raise ApiError(status, message=f"Invalid JSON error response: {exc}") from exc
            raise ApiError(status, message=f"Invalid JSON response: {exc}") from exc

        if status >= 400:
            error = None
            if isinstance(payload, dict) and "error" in payload:
                try:
                    error = ErrorEnvelope.from_dict(payload)
                except Exception:
                    error = None
            raise ApiError(status, error=error, response_body=payload)

        return payload

