from __future__ import annotations

from urllib.parse import quote

from .base import BaseClient
from ..models.common import Health, VersionInfo
from ..models.tool_registry import ToolDefinition, ToolInvocationRequest, ToolInvocationResult


class ToolRegistryClient(BaseClient):
    def health(self) -> Health:
        payload = self._request_json("GET", "/v1alpha1/health")
        return Health.from_dict(payload)

    def version(self) -> VersionInfo:
        payload = self._request_json("GET", "/v1alpha1/version")
        return VersionInfo.from_dict(payload)

    def list_tools(self) -> list[ToolDefinition]:
        payload = self._request_json("GET", "/v1alpha1/tools")
        return [ToolDefinition.from_dict(x) for x in payload]

    def get_tool(self, tool_id: str) -> ToolDefinition:
        payload = self._request_json("GET", f"/v1alpha1/tools/{quote(tool_id, safe='')}")
        return ToolDefinition.from_dict(payload)

    def invoke_tool(self, request: ToolInvocationRequest) -> ToolInvocationResult:
        payload = self._request_json("POST", "/v1alpha1/tool-invocations", body=request.to_dict())
        return ToolInvocationResult.from_dict(payload)

