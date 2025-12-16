from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import Extensions, _omit_none


@dataclass(frozen=True, slots=True)
class TraceEvent:
    run_id: str
    seq: int
    time: str
    level: str
    type: str
    data: dict[str, Any] | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none(
            {
                "run_id": self.run_id,
                "seq": self.seq,
                "time": self.time,
                "level": self.level,
                "type": self.type,
                "data": self.data,
                "extensions": self.extensions,
            }
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "TraceEvent":
        return TraceEvent(
            run_id=data["run_id"],
            seq=int(data["seq"]),
            time=data["time"],
            level=data["level"],
            type=data["type"],
            data=data.get("data"),
            extensions=data.get("extensions"),
        )


@dataclass(frozen=True, slots=True)
class TraceIndexRun:
    run_id: str
    trace_uri: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _omit_none({"run_id": self.run_id, "trace_uri": self.trace_uri})

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "TraceIndexRun":
        return TraceIndexRun(run_id=data["run_id"], trace_uri=data.get("trace_uri"))


@dataclass(frozen=True, slots=True)
class TraceIndex:
    runs: list[TraceIndexRun] | None = None
    extensions: Extensions | None = None

    def to_dict(self) -> dict[str, Any]:
        runs = [run.to_dict() for run in self.runs] if self.runs is not None else None
        return _omit_none({"runs": runs, "extensions": self.extensions})

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "TraceIndex":
        runs = data.get("runs")
        return TraceIndex(
            runs=[TraceIndexRun.from_dict(x) for x in runs] if isinstance(runs, list) else None,
            extensions=data.get("extensions"),
        )

