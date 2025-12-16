from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import Extensions, Metadata, ResourceRef, Error, _omit_none


@dataclass(frozen=True, slots=True)
class RunInput:
    goal: str
    context: dict[str, Any] | None = None
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "goal": self.goal,
                "context": self.context,
                "data": self.data,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RunInput":
        return RunInput(
            goal=data["goal"],
            context=data.get("context"),
            data=data.get("data"),
        )


@dataclass(frozen=True, slots=True)
class RuntimeSelector:
    profile: str | None = None
    instance_id: str | None = None
    runtime_type: str | None = None
    address: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "profile": self.profile,
                "instance_id": self.instance_id,
                "runtime_type": self.runtime_type,
                "address": self.address,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RuntimeSelector":
        return RuntimeSelector(
            profile=data.get("profile"),
            instance_id=data.get("instance_id"),
            runtime_type=data.get("runtime_type"),
            address=data.get("address"),
        )


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    allow_tool_ids: list[str] | None = None
    deny_tool_ids: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "allow_tool_ids": self.allow_tool_ids,
                "deny_tool_ids": self.deny_tool_ids,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ToolPolicy":
        return ToolPolicy(
            allow_tool_ids=list(data["allow_tool_ids"]) if "allow_tool_ids" in data else None,
            deny_tool_ids=list(data["deny_tool_ids"]) if "deny_tool_ids" in data else None,
        )


@dataclass(frozen=True, slots=True)
class Limits:
    timeout_ms: int | None = None
    max_steps: int | None = None
    max_tokens: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "timeout_ms": self.timeout_ms,
                "max_steps": self.max_steps,
                "max_tokens": self.max_tokens,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Limits":
        return Limits(
            timeout_ms=data.get("timeout_ms"),
            max_steps=data.get("max_steps"),
            max_tokens=data.get("max_tokens"),
        )


@dataclass(frozen=True, slots=True)
class RunRequest:
    input: RunInput
    run_id: str | None = None
    runtime_selector: RuntimeSelector | None = None
    tool_policy: ToolPolicy | None = None
    limits: Limits | None = None
    metadata: Metadata | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "run_id": self.run_id,
                "input": self.input.to_dict(),
                "runtime_selector": self.runtime_selector.to_dict()
                if self.runtime_selector is not None
                else None,
                "tool_policy": self.tool_policy.to_dict() if self.tool_policy is not None else None,
                "limits": self.limits.to_dict() if self.limits is not None else None,
                "metadata": self.metadata.to_dict() if self.metadata is not None else None,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RunRequest":
        runtime_selector = data.get("runtime_selector")
        tool_policy = data.get("tool_policy")
        limits = data.get("limits")
        metadata = data.get("metadata")

        return RunRequest(
            run_id=data.get("run_id"),
            input=RunInput.from_dict(data["input"]),
            runtime_selector=RuntimeSelector.from_dict(runtime_selector)
            if isinstance(runtime_selector, dict)
            else None,
            tool_policy=ToolPolicy.from_dict(tool_policy) if isinstance(tool_policy, dict) else None,
            limits=Limits.from_dict(limits) if isinstance(limits, dict) else None,
            metadata=Metadata.from_dict(metadata) if isinstance(metadata, dict) else None,
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class RunStatus:
    run_id: str
    state: str
    started_at: str | None = None
    ended_at: str | None = None
    runtime_instance_id: str | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "run_id": self.run_id,
                "state": self.state,
                "started_at": self.started_at,
                "ended_at": self.ended_at,
                "runtime_instance_id": self.runtime_instance_id,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RunStatus":
        return RunStatus(
            run_id=data["run_id"],
            state=data["state"],
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            runtime_instance_id=data.get("runtime_instance_id"),
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: str
    ok: bool
    output: dict[str, Any] | None = None
    error: Error | None = None
    artifacts: list[ResourceRef] | None = None
    usage: dict[str, Any] | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        artifacts = [a.to_dict() for a in self.artifacts] if self.artifacts is not None else None
        return _omit_none(
            {
                "run_id": self.run_id,
                "ok": self.ok,
                "output": self.output,
                "error": self.error.to_dict() if self.error is not None else None,
                "artifacts": artifacts,
                "usage": self.usage,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RunResult":
        error = data.get("error")
        artifacts = data.get("artifacts")
        return RunResult(
            run_id=data["run_id"],
            ok=bool(data["ok"]),
            output=data.get("output"),
            error=Error.from_dict(error) if isinstance(error, dict) else None,
            artifacts=[ResourceRef.from_dict(x) for x in artifacts] if isinstance(artifacts, list) else None,
            usage=data.get("usage"),
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class RunEvent:
    run_id: str
    seq: int
    type: str
    time: str
    data: dict[str, Any] | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "run_id": self.run_id,
                "seq": self.seq,
                "type": self.type,
                "time": self.time,
                "data": self.data,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RunEvent":
        return RunEvent(
            run_id=data["run_id"],
            seq=int(data["seq"]),
            type=data["type"],
            time=data["time"],
            data=data.get("data"),
            extensions=data.get("extensions"),
        )

