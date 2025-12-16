from __future__ import annotations

import json
from urllib.parse import quote

from .base import BaseClient
from ..models.common import Health, VersionInfo
from ..models.node_agent import InstanceCreateRequest, InstanceCreateResponse, RuntimeInstance
from ..models.runtime import RunRequest, RunResult, RunStatus
from ..models.trace import TraceEvent


class NodeAgentClient(BaseClient):
    def health(self) -> Health:
        payload = self._request_json("GET", "/v1alpha1/health")
        return Health.from_dict(payload)

    def version(self) -> VersionInfo:
        payload = self._request_json("GET", "/v1alpha1/version")
        return VersionInfo.from_dict(payload)

    def list_instances(self) -> list[RuntimeInstance]:
        payload = self._request_json("GET", "/v1alpha1/instances")
        return [RuntimeInstance.from_dict(x) for x in payload]

    def create_instances(self, request: InstanceCreateRequest) -> InstanceCreateResponse:
        payload = self._request_json("POST", "/v1alpha1/instances", body=request.to_dict())
        return InstanceCreateResponse.from_dict(payload)

    def delete_instance(self, instance_id: str) -> None:
        self._request_json("DELETE", f"/v1alpha1/instances/{quote(instance_id, safe='')}")
        return None

    def create_run(self, request: RunRequest) -> RunStatus:
        payload = self._request_json("POST", "/v1alpha1/runs", body=request.to_dict())
        return RunStatus.from_dict(payload)

    def get_run(self, run_id: str) -> RunStatus:
        payload = self._request_json("GET", f"/v1alpha1/runs/{quote(run_id, safe='')}")
        return RunStatus.from_dict(payload)

    def get_run_result(self, run_id: str) -> RunResult:
        payload = self._request_json("GET", f"/v1alpha1/runs/{quote(run_id, safe='')}/result")
        return RunResult.from_dict(payload)

    def get_trace_events(self, run_id: str) -> list[TraceEvent]:
        text = self._request_json("GET", f"/v1alpha1/runs/{quote(run_id, safe='')}/trace")
        if not isinstance(text, str):
            raise TypeError("Expected NDJSON text response")
        events: list[TraceEvent] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            events.append(TraceEvent.from_dict(json.loads(line)))
        return events

