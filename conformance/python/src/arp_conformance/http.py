from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status_code: int
    headers: dict[str, str]
    text: str

    def content_type(self) -> str | None:
        raw = self.headers.get("content-type") or self.headers.get("Content-Type")
        if raw is None:
            return None
        return raw.split(";", 1)[0].strip().lower()


class HttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout_s: float = 10.0,
        retries: int = 0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._retries = max(0, retries)
        self._client = httpx.Client(base_url=self._base_url, headers=headers or {}, timeout=timeout_s)

    def close(self) -> None:
        self._client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                resp = self._client.request(method, path, json=json_body, headers=headers)
                return HttpResponse(
                    url=str(resp.url),
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    text=resp.text,
                )
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt >= self._retries:
                    raise
        raise last_exc or RuntimeError("request failed")

    def stream_sample(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        max_bytes: int = 4096,
    ) -> HttpResponse:
        """
        Fetch a partial response body sample without buffering the full stream.
        """

        with self._client.stream(method, path, headers=headers) as resp:
            buf = bytearray()
            for chunk in resp.iter_bytes():
                buf.extend(chunk)
                if len(buf) >= max_bytes:
                    break
            text = bytes(buf).decode("utf-8", errors="replace")
            return HttpResponse(
                url=str(resp.url),
                status_code=resp.status_code,
                headers=dict(resp.headers),
                text=text,
            )
