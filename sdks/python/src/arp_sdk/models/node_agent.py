from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import Extensions, Metadata, _omit_none


@dataclass(frozen=True, slots=True)
class RuntimeInstance:
    instance_id: str
    state: str
    runtime_version: str
    runtime_type: str
    address: str | None = None
    capabilities: dict[str, Any] | None = None
    metadata: Metadata | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "instance_id": self.instance_id,
                "state": self.state,
                "runtime_version": self.runtime_version,
                "runtime_type": self.runtime_type,
                "address": self.address,
                "capabilities": self.capabilities,
                "metadata": self.metadata.to_dict() if self.metadata is not None else None,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RuntimeInstance":
        metadata = data.get("metadata")
        return RuntimeInstance(
            instance_id=data["instance_id"],
            state=data["state"],
            runtime_version=data["runtime_version"],
            runtime_type=data["runtime_type"],
            address=data.get("address"),
            capabilities=data.get("capabilities"),
            metadata=Metadata.from_dict(metadata) if isinstance(metadata, dict) else None,
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class InstanceCreateRequest:
    profile: str
    count: int | None = None
    env: dict[str, str] | None = None
    args: list[str] | None = None
    labels: dict[str, str] | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "profile": self.profile,
                "count": self.count,
                "env": self.env,
                "args": self.args,
                "labels": self.labels,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "InstanceCreateRequest":
        return InstanceCreateRequest(
            profile=data["profile"],
            count=data.get("count"),
            env=data.get("env"),
            args=list(data["args"]) if "args" in data else None,
            labels=data.get("labels"),
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class InstanceCreateResponse:
    instances: list[RuntimeInstance]
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "instances": [instance.to_dict() for instance in self.instances],
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "InstanceCreateResponse":
        return InstanceCreateResponse(
            instances=[RuntimeInstance.from_dict(x) for x in data["instances"]],
            extensions=data.get("extensions"),
        )

