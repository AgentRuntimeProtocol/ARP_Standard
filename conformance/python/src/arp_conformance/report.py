from __future__ import annotations

import json
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum


class ResultStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass(frozen=True)
class HttpExchange:
    method: str
    url: str
    request_body: object | None = None
    status_code: int | None = None
    content_type: str | None = None
    response_body: object | None = None


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    name: str
    status: ResultStatus
    message: str
    exchange: HttpExchange | None = None
    errors: list[str] = field(default_factory=list)
    duration_ms: int | None = None


@dataclass(frozen=True)
class ConformanceReport:
    service: str
    tier: str
    spec_ref: str
    started_at_epoch_ms: int
    finished_at_epoch_ms: int
    results: list[CheckResult]

    @property
    def ok(self) -> bool:
        return not any(r.status == ResultStatus.FAIL for r in self.results)

    def ok_strict(self) -> bool:
        return not any(r.status in (ResultStatus.FAIL, ResultStatus.WARN, ResultStatus.SKIP) for r in self.results)

    def counts(self) -> dict[str, int]:
        out = {s.value: 0 for s in ResultStatus}
        for r in self.results:
            out[r.status.value] += 1
        return out

    def to_dict(self) -> dict[str, object]:
        return {
            "service": self.service,
            "tier": self.tier,
            "spec_ref": self.spec_ref,
            "started_at_epoch_ms": self.started_at_epoch_ms,
            "finished_at_epoch_ms": self.finished_at_epoch_ms,
            "counts": self.counts(),
            "ok": self.ok,
            "results": [
                {
                    "check_id": r.check_id,
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "errors": r.errors,
                    "duration_ms": r.duration_ms,
                    "exchange": None
                    if r.exchange is None
                    else {
                        "method": r.exchange.method,
                        "url": r.exchange.url,
                        "request_body": r.exchange.request_body,
                        "status_code": r.exchange.status_code,
                        "content_type": r.exchange.content_type,
                        "response_body": r.exchange.response_body,
                    },
                }
                for r in self.results
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False)

    def to_junit_element(self) -> ET.Element:
        testsuite = ET.Element("testsuite")
        testsuite.set("name", f"arp-conformance:{self.service}:{self.tier}")
        testsuite.set("tests", str(len(self.results)))
        failures = sum(1 for r in self.results if r.status == ResultStatus.FAIL)
        skipped = sum(1 for r in self.results if r.status == ResultStatus.SKIP)
        testsuite.set("failures", str(failures))
        testsuite.set("skipped", str(skipped))

        for r in self.results:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("classname", self.service)
            testcase.set("name", r.check_id)
            if r.duration_ms is not None:
                testcase.set("time", f"{r.duration_ms / 1000.0:.3f}")
            if r.status == ResultStatus.SKIP:
                sk = ET.SubElement(testcase, "skipped")
                sk.text = r.message
            elif r.status == ResultStatus.FAIL:
                fl = ET.SubElement(testcase, "failure")
                fl.set("message", r.message)
                if r.errors:
                    fl.text = "\n".join(r.errors)
            elif r.status == ResultStatus.WARN:
                sysout = ET.SubElement(testcase, "system-out")
                sysout.text = f"WARN: {r.message}\n" + ("\n".join(r.errors) if r.errors else "")

        return testsuite

    def to_junit_xml(self) -> str:
        return ET.tostring(self.to_junit_element(), encoding="utf-8", xml_declaration=True).decode("utf-8")


def reports_to_junit_xml(reports: list[ConformanceReport]) -> str:
    root = ET.Element("testsuites")
    for report in reports:
        root.append(report.to_junit_element())
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


@dataclass(frozen=True)
class Timer:
    start_ns: int = field(default_factory=time.monotonic_ns)

    def elapsed_ms(self) -> int:
        return int((time.monotonic_ns() - self.start_ns) / 1_000_000)
