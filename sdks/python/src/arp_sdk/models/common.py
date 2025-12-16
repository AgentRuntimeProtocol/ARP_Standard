from __future__ import annotations

from dataclasses import dataclass
from typing import Any

Extensions = dict[str, Any]


def _omit_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


@dataclass(frozen=True, slots=True)
class ErrorCause:
    message: str
    code: str | None = None
    details: dict[str, Any] | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ErrorCause":
        return ErrorCause(
            code=data.get("code"),
            message=data["message"],
            details=data.get("details"),
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class Error:
    code: str
    message: str
    details: dict[str, Any] | None = None
    retryable: bool | None = None
    cause: ErrorCause | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "retryable": self.retryable,
                "cause": self.cause.to_dict() if self.cause is not None else None,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Error":
        cause = data.get("cause")
        return Error(
            code=data["code"],
            message=data["message"],
            details=data.get("details"),
            retryable=data.get("retryable"),
            cause=ErrorCause.from_dict(cause) if isinstance(cause, dict) else None,
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class ErrorEnvelope:
    error: Error
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none({"error": self.error.to_dict(), "extensions": self.extensions})

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ErrorEnvelope":
        return ErrorEnvelope(
            error=Error.from_dict(data["error"]),
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class VersionInfoBuild:
    commit: str | None = None
    built_at: str | None = None
    dirty: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "commit": self.commit,
                "built_at": self.built_at,
                "dirty": self.dirty,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "VersionInfoBuild":
        return VersionInfoBuild(
            commit=data.get("commit"),
            built_at=data.get("built_at"),
            dirty=data.get("dirty"),
        )


@dataclass(frozen=True, slots=True)
class VersionInfo:
    service_name: str
    service_version: str
    supported_api_versions: list[str]
    build: VersionInfoBuild | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "service_name": self.service_name,
                "service_version": self.service_version,
                "supported_api_versions": self.supported_api_versions,
                "build": self.build.to_dict() if self.build is not None else None,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "VersionInfo":
        build = data.get("build")
        return VersionInfo(
            service_name=data["service_name"],
            service_version=data["service_version"],
            supported_api_versions=list(data["supported_api_versions"]),
            build=VersionInfoBuild.from_dict(build) if isinstance(build, dict) else None,
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class HealthCheck:
    name: str
    status: str
    message: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "name": self.name,
                "status": self.status,
                "message": self.message,
                "details": self.details,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "HealthCheck":
        return HealthCheck(
            name=data["name"],
            status=data["status"],
            message=data.get("message"),
            details=data.get("details"),
        )


@dataclass(frozen=True, slots=True)
class Health:
    status: str
    time: str
    checks: list[HealthCheck] | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        checks = [c.to_dict() for c in self.checks] if self.checks is not None else None
        return _omit_none(
            {
                "status": self.status,
                "time": self.time,
                "checks": checks,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Health":
        checks = data.get("checks")
        return Health(
            status=data["status"],
            time=data["time"],
            checks=[HealthCheck.from_dict(x) for x in checks] if isinstance(checks, list) else None,
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class ResourceRef:
    type: str
    id: str
    uri: str | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "type": self.type,
                "id": self.id,
                "uri": self.uri,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ResourceRef":
        return ResourceRef(
            type=data["type"],
            id=data["id"],
            uri=data.get("uri"),
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class Pagination:
    next_page_token: str | None = None
    page_size: int | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "next_page_token": self.next_page_token,
                "page_size": self.page_size,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Pagination":
        return Pagination(
            next_page_token=data.get("next_page_token"),
            page_size=data.get("page_size"),
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class Metadata:
    labels: dict[str, str] | None = None
    annotations: dict[str, str] | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "labels": self.labels,
                "annotations": self.annotations,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Metadata":
        return Metadata(
            labels=data.get("labels"),
            annotations=data.get("annotations"),
            extensions=data.get("extensions"),
        )

