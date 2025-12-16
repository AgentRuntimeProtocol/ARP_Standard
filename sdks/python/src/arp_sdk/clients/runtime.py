from __future__ import annotations

from urllib.parse import quote

from .base import BaseClient
from ..models.common import Health, VersionInfo
from ..models.runtime import RunRequest, RunResult, RunStatus


class RuntimeClient(BaseClient):
    def health(self) -> Health:
        payload = self._request_json("GET", "/v1alpha1/health")
        return Health.from_dict(payload)

    def version(self) -> VersionInfo:
        payload = self._request_json("GET", "/v1alpha1/version")
        return VersionInfo.from_dict(payload)

    def create_run(self, request: RunRequest) -> RunStatus:
        payload = self._request_json("POST", "/v1alpha1/runs", body=request.to_dict())
        return RunStatus.from_dict(payload)

    def get_run(self, run_id: str) -> RunStatus:
        payload = self._request_json("GET", f"/v1alpha1/runs/{quote(run_id, safe='')}")
        return RunStatus.from_dict(payload)

    def get_run_result(self, run_id: str) -> RunResult:
        payload = self._request_json("GET", f"/v1alpha1/runs/{quote(run_id, safe='')}/result")
        return RunResult.from_dict(payload)

    def cancel_run(self, run_id: str) -> RunStatus:
        payload = self._request_json("POST", f"/v1alpha1/runs/{quote(run_id, safe='')}:cancel")
        return RunStatus.from_dict(payload)

