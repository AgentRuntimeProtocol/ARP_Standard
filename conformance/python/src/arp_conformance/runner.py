from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arp_conformance import SPEC_REF
from arp_conformance.http import HttpClient
from arp_conformance.report import CheckResult, ConformanceReport, HttpExchange, ResultStatus, Timer
from arp_conformance.schemas import SchemaRegistry
from arp_conformance.spec_loader import Endpoint, load_required_endpoints


@dataclass(frozen=True)
class RunnerOptions:
    timeout_s: float = 10.0
    retries: int = 0
    poll_timeout_s: float = 60.0
    poll_interval_s: float = 1.0
    allow_mutations: bool = False
    cleanup: bool = True
    strict: bool = False
    spec_path: str | None = None
    spec_version: str = "v1"


def _epoch_ms() -> int:
    return int(time.time() * 1000)


def _fill_path(path_template: str) -> str:
    replacements = {
        "{run_id}": "run_conformance_" + uuid.uuid4().hex[:12],
        "{node_run_id}": "node_run_conformance_" + uuid.uuid4().hex[:12],
        "{node_type_id}": "node_type_conformance_" + uuid.uuid4().hex[:12],
    }
    out = path_template
    for key, value in replacements.items():
        out = out.replace(key, value)
    return out


def _parse_json(text: str) -> Any:
    return json.loads(text)


def _expect_json(resp_text: str, *, on_error: str) -> tuple[Any | None, list[str]]:
    try:
        return _parse_json(resp_text), []
    except Exception as exc:
        return None, [f"{on_error}: {exc.__class__.__name__}: {exc}"]


def _mk_check(
    *,
    check_id: str,
    name: str,
    status: ResultStatus,
    message: str,
    exchange: HttpExchange | None = None,
    errors: list[str] | None = None,
    timer: Timer | None = None,
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        name=name,
        status=status,
        message=message,
        exchange=exchange,
        errors=errors or [],
        duration_ms=None if timer is None else timer.elapsed_ms(),
    )


class ConformanceRunner:
    def __init__(self, *, base_url: str, headers: dict[str, str] | None, options: RunnerOptions) -> None:
        self._client = HttpClient(
            base_url=base_url,
            headers=headers,
            timeout_s=options.timeout_s,
            retries=options.retries,
        )
        self._options = options
        spec_root = None if options.spec_path is None else Path(options.spec_path)
        self._schemas = SchemaRegistry.load(spec_path=spec_root, version=options.spec_version)
        self._required = load_required_endpoints(spec_path=spec_root, version=options.spec_version)

    def close(self) -> None:
        self._client.close()

    def run(self, *, service: str, tier: str) -> ConformanceReport:
        started = _epoch_ms()
        results: list[CheckResult] = []
        timer = Timer()
        try:
            if tier not in {"smoke", "surface", "core", "deep"}:
                raise ValueError(f"Unsupported tier: {tier}")
            if tier in {"core", "deep"} and not self._options.allow_mutations:
                results.append(
                    _mk_check(
                        check_id="guard.allow_mutations",
                        name="Require --allow-mutations",
                        status=ResultStatus.FAIL,
                        message="Tier requires --allow-mutations",
                        timer=timer,
                    )
                )
                return self._final_report(service, tier, started, results)

            results.extend(self._check_smoke())
            if tier == "smoke":
                return self._final_report(service, tier, started, results)

            results.extend(self._check_surface(service))
            if tier == "surface":
                return self._final_report(service, tier, started, results)

            results.extend(self._check_core(service))
            if tier == "deep":
                results.extend(self._check_deep(service))
            return self._final_report(service, tier, started, results)
        except Exception as exc:
            results.append(
                _mk_check(
                    check_id="runner.exception",
                    name="Unhandled runner error",
                    status=ResultStatus.FAIL,
                    message=f"{exc.__class__.__name__}: {exc}",
                )
            )
            return self._final_report(service, tier, started, results)
        finally:
            self.close()

    def _final_report(self, service: str, tier: str, started: int, results: list[CheckResult]) -> ConformanceReport:
        return ConformanceReport(
            service=service,
            tier=tier,
            spec_ref=SPEC_REF,
            started_at_epoch_ms=started,
            finished_at_epoch_ms=_epoch_ms(),
            results=results,
        )

    def _check_smoke(self) -> list[CheckResult]:
        out: list[CheckResult] = []
        out.append(self._check_health())
        out.append(self._check_version())
        return out

    def _check_health(self) -> CheckResult:
        timer = Timer()
        resp = self._client.request("GET", "/v1/health")
        ct = resp.content_type()
        exchange = HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, content_type=ct)
        if resp.status_code != 200:
            return _mk_check(
                check_id="smoke.health",
                name="GET /v1/health",
                status=ResultStatus.FAIL,
                message=f"Expected 200, got {resp.status_code}",
                exchange=exchange,
                timer=timer,
            )
        data, errs = _expect_json(resp.text, on_error="Health response was not valid JSON")
        if errs:
            return _mk_check(
                check_id="smoke.health",
                name="GET /v1/health",
                status=ResultStatus.FAIL,
                message="Health response JSON parse failed",
                exchange=exchange,
                errors=errs,
                timer=timer,
            )
        schema_errors = self._schemas.validate(data, schema_path="schemas/common/health.schema.json")
        if schema_errors:
            return _mk_check(
                check_id="smoke.health",
                name="GET /v1/health",
                status=ResultStatus.FAIL,
                message="Health response did not match schema",
                exchange=HttpExchange(
                    method="GET",
                    url=resp.url,
                    status_code=resp.status_code,
                    content_type=resp.content_type(),
                    response_body=data,
                ),
                errors=schema_errors,
                timer=timer,
            )
        status = ResultStatus.PASS if ct == "application/json" else ResultStatus.WARN
        message = "OK" if status == ResultStatus.PASS else f"OK (unexpected Content-Type {ct!r})"
        return _mk_check(
            check_id="smoke.health",
            name="GET /v1/health",
            status=status,
            message=message,
            exchange=HttpExchange(
                method="GET",
                url=resp.url,
                status_code=resp.status_code,
                content_type=ct,
                response_body=data,
            ),
            timer=timer,
        )

    def _check_version(self) -> CheckResult:
        timer = Timer()
        resp = self._client.request("GET", "/v1/version")
        ct = resp.content_type()
        exchange = HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, content_type=ct)
        if resp.status_code != 200:
            return _mk_check(
                check_id="smoke.version",
                name="GET /v1/version",
                status=ResultStatus.FAIL,
                message=f"Expected 200, got {resp.status_code}",
                exchange=exchange,
                timer=timer,
            )
        data, errs = _expect_json(resp.text, on_error="Version response was not valid JSON")
        if errs:
            return _mk_check(
                check_id="smoke.version",
                name="GET /v1/version",
                status=ResultStatus.FAIL,
                message="Version response JSON parse failed",
                exchange=exchange,
                errors=errs,
                timer=timer,
            )
        schema_errors = self._schemas.validate(data, schema_path="schemas/common/version_info.schema.json")
        if schema_errors:
            return _mk_check(
                check_id="smoke.version",
                name="GET /v1/version",
                status=ResultStatus.FAIL,
                message="Version response did not match schema",
                exchange=HttpExchange(
                    method="GET",
                    url=resp.url,
                    status_code=resp.status_code,
                    content_type=resp.content_type(),
                    response_body=data,
                ),
                errors=schema_errors,
                timer=timer,
            )
        supported = data.get("supported_api_versions") if isinstance(data, dict) else None
        if not isinstance(supported, list) or "v1" not in supported:
            return _mk_check(
                check_id="smoke.version.supported_versions",
                name="VersionInfo.supported_api_versions contains v1",
                status=ResultStatus.FAIL,
                message="supported_api_versions must include 'v1'",
                exchange=HttpExchange(
                    method="GET",
                    url=resp.url,
                    status_code=resp.status_code,
                    content_type=resp.content_type(),
                    response_body=data,
                ),
                timer=timer,
            )
        status = ResultStatus.PASS if ct == "application/json" else ResultStatus.WARN
        message = "OK" if status == ResultStatus.PASS else f"OK (unexpected Content-Type {ct!r})"
        return _mk_check(
            check_id="smoke.version",
            name="GET /v1/version",
            status=status,
            message=message,
            exchange=HttpExchange(
                method="GET",
                url=resp.url,
                status_code=resp.status_code,
                content_type=ct,
                response_body=data,
            ),
            timer=timer,
        )

    def _check_surface(self, service: str) -> list[CheckResult]:
        required = self._required.common[:]
        if service == "run-gateway":
            required += self._required.run_gateway
        elif service == "run-coordinator":
            required += self._required.run_coordinator
        elif service == "atomic-executor":
            required += self._required.atomic_executor
        elif service == "composite-executor":
            required += self._required.composite_executor
        elif service == "node-registry":
            required += self._required.node_registry
        elif service == "selection":
            required += self._required.selection
        elif service == "pdp":
            required += self._required.pdp
        else:
            return [
                _mk_check(
                    check_id="surface.service",
                    name="Service kind supported",
                    status=ResultStatus.FAIL,
                    message=f"Unsupported service: {service}",
                )
            ]

        out: list[CheckResult] = []
        for idx, ep in enumerate(required, start=1):
            out.append(self._surface_endpoint_check(ep, index=idx))
        return out

    def _surface_endpoint_check(self, endpoint: Endpoint, *, index: int) -> CheckResult:
        timer = Timer()
        path = _fill_path(endpoint.path_template)
        method = endpoint.method.upper()

        json_body: Any | None = None
        expects_success_schema: str | None = None
        expects_no_content = False

        # Required endpoint expectations (success paths)
        if method == "GET" and endpoint.path_template == "/v1/health":
            expects_success_schema = "schemas/common/health.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/version":
            expects_success_schema = "schemas/common/version_info.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/runs":
            json_body = {}
            expects_success_schema = "schemas/core/run.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/runs/{run_id}":
            expects_success_schema = "schemas/core/run.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/runs/{run_id}:cancel":
            expects_success_schema = "schemas/core/run.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/node-runs":
            json_body = {}
            expects_success_schema = "schemas/run_coordinator/node_runs/node_runs_create_response.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/node-runs/{node_run_id}":
            expects_success_schema = "schemas/core/node_run.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/node-runs/{node_run_id}:evaluation":
            json_body = {}
            expects_no_content = True
        elif method == "POST" and endpoint.path_template == "/v1/node-runs/{node_run_id}:complete":
            json_body = {}
            expects_no_content = True
        elif method == "POST" and endpoint.path_template == "/v1/composite-node-runs:begin":
            json_body = {}
            expects_success_schema = "schemas/composite_executor/node_runs/composite_begin_response.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/atomic-node-runs:execute":
            json_body = {}
            expects_success_schema = "schemas/atomic_executor/node_runs/atomic_execute_result.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/node-types":
            expects_success_schema = "schemas/core/node_type.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/node-types":
            json_body = {}
            expects_success_schema = "schemas/core/node_type.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/node-types/{node_type_id}":
            expects_success_schema = "schemas/core/node_type.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/candidate-sets":
            json_body = {}
            expects_success_schema = "schemas/core/candidate_set.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/policy:decide":
            json_body = {}
            expects_success_schema = "schemas/core/policy_decision.schema.json"

        resp = self._client.request(method, path, json_body=json_body)
        exchange = HttpExchange(
            method=method,
            url=resp.url,
            request_body=json_body,
            status_code=resp.status_code,
            content_type=resp.content_type(),
        )

        # Surface tier requires invalid mutation bodies to be rejected.
        if json_body == {} and method in {"POST", "PUT"} and resp.status_code < 400:
            return _mk_check(
                check_id=f"surface.{index:02d}",
                name=f"{method} {endpoint.path_template}",
                status=ResultStatus.FAIL,
                message="Expected non-2xx for intentionally invalid request body",
                exchange=exchange,
                timer=timer,
            )

        if expects_no_content and resp.status_code == 204:
            return _mk_check(
                check_id=f"surface.{index:02d}",
                name=f"{method} {endpoint.path_template}",
                status=ResultStatus.PASS,
                message="OK (204)",
                exchange=exchange,
                timer=timer,
            )

        # If success, validate schema if possible.
        if resp.status_code < 400:
            if expects_success_schema is None:
                return _mk_check(
                    check_id=f"surface.{index:02d}",
                    name=f"{method} {endpoint.path_template}",
                    status=ResultStatus.PASS,
                    message="OK",
                    exchange=exchange,
                    timer=timer,
                )

            data, errs = _expect_json(resp.text, on_error="Success response was not valid JSON")
            if errs:
                return _mk_check(
                    check_id=f"surface.{index:02d}",
                    name=f"{method} {endpoint.path_template}",
                    status=ResultStatus.FAIL,
                    message="Success response JSON parse failed",
                    exchange=exchange,
                    errors=errs,
                    timer=timer,
                )

            if endpoint.path_template == "/v1/node-types" and isinstance(data, list):
                errors: list[str] = []
                for i, item in enumerate(data):
                    errors.extend([f"[{i}] {e}" for e in self._schemas.validate(item, schema_path=expects_success_schema)])
                if errors:
                    return _mk_check(
                        check_id=f"surface.{index:02d}",
                        name=f"{method} {endpoint.path_template}",
                        status=ResultStatus.FAIL,
                        message="Tool list did not match schema",
                        exchange=HttpExchange(
                            method=method,
                            url=resp.url,
                            request_body=json_body,
                            status_code=resp.status_code,
                            content_type=resp.content_type(),
                            response_body=data,
                        ),
                        errors=errors,
                        timer=timer,
                    )
                return _mk_check(
                    check_id=f"surface.{index:02d}",
                    name=f"{method} {endpoint.path_template}",
                    status=ResultStatus.PASS,
                    message="OK",
                    exchange=HttpExchange(
                        method=method,
                        url=resp.url,
                        request_body=json_body,
                        status_code=resp.status_code,
                        content_type=resp.content_type(),
                        response_body=data,
                    ),
                    timer=timer,
                )

            schema_errors = self._schemas.validate(data, schema_path=expects_success_schema)
            if schema_errors:
                return _mk_check(
                    check_id=f"surface.{index:02d}",
                    name=f"{method} {endpoint.path_template}",
                    status=ResultStatus.FAIL,
                    message="Success response did not match schema",
                    exchange=HttpExchange(
                        method=method,
                        url=resp.url,
                        request_body=json_body,
                        status_code=resp.status_code,
                        content_type=resp.content_type(),
                        response_body=data,
                    ),
                    errors=schema_errors,
                    timer=timer,
                )

            return _mk_check(
                check_id=f"surface.{index:02d}",
                name=f"{method} {endpoint.path_template}",
                status=ResultStatus.PASS,
                message="OK",
                exchange=HttpExchange(
                    method=method,
                    url=resp.url,
                    request_body=json_body,
                    status_code=resp.status_code,
                    content_type=resp.content_type(),
                    response_body=data,
                ),
                timer=timer,
            )

        # Otherwise validate error envelope.
        data, errs = _expect_json(resp.text, on_error="Error response was not valid JSON")
        if errs:
            return _mk_check(
                check_id=f"surface.{index:02d}",
                name=f"{method} {endpoint.path_template}",
                status=ResultStatus.FAIL,
                message="Error response JSON parse failed",
                exchange=exchange,
                errors=errs,
                timer=timer,
            )
        schema_errors = self._schemas.validate(data, schema_path="schemas/common/error.schema.json")
        if schema_errors:
            return _mk_check(
                check_id=f"surface.{index:02d}",
                name=f"{method} {endpoint.path_template}",
                status=ResultStatus.FAIL,
                message="Error response did not match ErrorEnvelope schema",
                exchange=HttpExchange(
                    method=method,
                    url=resp.url,
                    request_body=json_body,
                    status_code=resp.status_code,
                    content_type=resp.content_type(),
                    response_body=data,
                ),
                errors=schema_errors,
                timer=timer,
            )

        return _mk_check(
            check_id=f"surface.{index:02d}",
            name=f"{method} {endpoint.path_template}",
            status=ResultStatus.PASS,
            message="OK (error path)",
            exchange=HttpExchange(
                method=method,
                url=resp.url,
                request_body=json_body,
                status_code=resp.status_code,
                content_type=resp.content_type(),
                response_body=data,
            ),
            timer=timer,
        )


    def _check_core(self, service: str) -> list[CheckResult]:
        return [
            _mk_check(
                check_id="core.unimplemented",
                name="Core conformance not implemented",
                status=ResultStatus.SKIP,
                message=f"Core tier is not defined for {service} in v1 yet",
            )
        ]

    def _check_deep(self, service: str) -> list[CheckResult]:
        return [
            _mk_check(
                check_id="deep.unimplemented",
                name="Deep conformance not implemented",
                status=ResultStatus.SKIP,
                message=f"Deep tier is not defined for {service} in v1 yet",
            )
        ]
