from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import Extensions, Metadata, ResourceRef, Error, _omit_none


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    tool_id: str
    name: str
    input_schema: dict[str, Any]
    source: str
    description: str | None = None
    output_schema: dict[str, Any] | None = None
    metadata: Metadata | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "tool_id": self.tool_id,
                "name": self.name,
                "description": self.description,
                "input_schema": self.input_schema,
                "output_schema": self.output_schema,
                "source": self.source,
                "metadata": self.metadata.to_dict() if self.metadata is not None else None,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ToolDefinition":
        metadata = data.get("metadata")
        return ToolDefinition(
            tool_id=data["tool_id"],
            name=data["name"],
            description=data.get("description"),
            input_schema=dict(data["input_schema"]),
            output_schema=data.get("output_schema"),
            source=data["source"],
            metadata=Metadata.from_dict(metadata) if isinstance(metadata, dict) else None,
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class ToolInvocationRequest:
    invocation_id: str
    args: dict[str, Any]
    tool_id: str | None = None
    tool_name: str | None = None
    context: dict[str, Any] | None = None
    caller: ResourceRef | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "invocation_id": self.invocation_id,
                "tool_id": self.tool_id,
                "tool_name": self.tool_name,
                "args": self.args,
                "context": self.context,
                "caller": self.caller.to_dict() if self.caller is not None else None,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ToolInvocationRequest":
        caller = data.get("caller")
        return ToolInvocationRequest(
            invocation_id=data["invocation_id"],
            tool_id=data.get("tool_id"),
            tool_name=data.get("tool_name"),
            args=dict(data["args"]),
            context=data.get("context"),
            caller=ResourceRef.from_dict(caller) if isinstance(caller, dict) else None,
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class ToolInvocationResult:
    invocation_id: str
    ok: bool
    result: dict[str, Any] | None = None
    error: Error | None = None
    duration_ms: int | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "invocation_id": self.invocation_id,
                "ok": self.ok,
                "result": self.result,
                "error": self.error.to_dict() if self.error is not None else None,
                "duration_ms": self.duration_ms,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ToolInvocationResult":
        error = data.get("error")
        return ToolInvocationResult(
            invocation_id=data["invocation_id"],
            ok=bool(data["ok"]),
            result=data.get("result"),
            error=Error.from_dict(error) if isinstance(error, dict) else None,
            duration_ms=data.get("duration_ms"),
            extensions=data.get("extensions"),
        )

