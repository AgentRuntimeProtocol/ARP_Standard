from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from arp_conformance import SPEC_REF
from arp_conformance.http import HttpClient
from arp_conformance.report import CheckResult, ConformanceReport, HttpExchange, ResultStatus, Timer
from arp_conformance.schemas import SchemaRegistry
from arp_conformance.spec_loader import Endpoint, RequiredEndpoints, load_required_endpoints


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
    tool_id: str | None = None
    tool_name: str | None = None
    runtime_profile: str | None = None


def _epoch_ms() -> int:
    return int(time.time() * 1000)


def _fill_path(path_template: str) -> str:
    replacements = {
        "{run_id}": "run_conformance_" + uuid.uuid4().hex[:12],
        "{tool_id}": "tool_conformance_" + uuid.uuid4().hex[:12],
        "{instance_id}": "inst_conformance_" + uuid.uuid4().hex[:12],
        "{runtime_profile}": "profile_conformance_" + uuid.uuid4().hex[:12],
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

            if service == "runtime":
                results.extend(self._check_core_runtime())
                if tier == "deep":
                    results.extend(self._check_deep_runtime())
            elif service == "tool-registry":
                results.extend(self._check_core_tool_registry())
            elif service == "daemon":
                results.extend(self._check_core_daemon())
                if tier == "deep":
                    results.extend(self._check_deep_daemon())
            else:
                results.append(
                    _mk_check(
                        check_id="guard.service",
                        name="Service kind supported",
                        status=ResultStatus.FAIL,
                        message=f"Unsupported service: {service}",
                    )
                )
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
        if service == "runtime":
            required += self._required.runtime
        elif service == "tool-registry":
            required += self._required.tool_registry
        elif service == "daemon":
            required += self._required.daemon
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
        elif method == "GET" and endpoint.path_template == "/v1/tools":
            expects_success_schema = "schemas/tool_registry/tools/tool_definition.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/tools/{tool_id}":
            expects_success_schema = "schemas/tool_registry/tools/tool_definition.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/tool-invocations":
            json_body = {}
            expects_success_schema = "schemas/tool_registry/tools/tool_invocation_result.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/runs":
            json_body = {}
            expects_success_schema = "schemas/runtime/runs/run_status.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/runs/{run_id}":
            expects_success_schema = "schemas/runtime/runs/run_status.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/runs/{run_id}/result":
            expects_success_schema = "schemas/runtime/runs/run_result.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/instances":
            expects_success_schema = "schemas/daemon/instances/instance_list_response.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/instances":
            json_body = {}
            expects_success_schema = "schemas/daemon/instances/instance_create_response.schema.json"
        elif method == "DELETE" and endpoint.path_template == "/v1/instances/{instance_id}":
            expects_no_content = True
        elif method == "POST" and endpoint.path_template == "/v1/instances:register":
            json_body = {}
            expects_success_schema = "schemas/daemon/instances/instance_register_response.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/admin/runtime-profiles":
            expects_success_schema = "schemas/daemon/runtime_profiles/runtime_profile_list_response.schema.json"
        elif method == "PUT" and endpoint.path_template == "/v1/admin/runtime-profiles/{runtime_profile}":
            json_body = {}
            expects_success_schema = "schemas/daemon/runtime_profiles/runtime_profile.schema.json"
        elif method == "DELETE" and endpoint.path_template == "/v1/admin/runtime-profiles/{runtime_profile}":
            expects_no_content = True
        elif method == "GET" and endpoint.path_template == "/v1/runs":
            expects_success_schema = "schemas/daemon/runs/run_list_response.schema.json"
        elif method == "POST" and endpoint.path_template == "/v1/runs":
            json_body = {}
            expects_success_schema = "schemas/runtime/runs/run_status.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/runs/{run_id}":
            expects_success_schema = "schemas/runtime/runs/run_status.schema.json"
        elif method == "GET" and endpoint.path_template == "/v1/runs/{run_id}/result":
            expects_success_schema = "schemas/runtime/runs/run_result.schema.json"

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

            if endpoint.path_template == "/v1/tools" and isinstance(data, list):
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

    def _check_core_runtime(self) -> list[CheckResult]:
        out: list[CheckResult] = []
        run_id = "run_conformance_" + uuid.uuid4().hex[:12]
        body = {"run_id": run_id, "input": {"goal": "ARP conformance test run"}, "limits": {"timeout_ms": 10_000, "max_steps": 1}}
        timer = Timer()
        resp = self._client.request("POST", "/v1/runs", json_body=body)
        exchange = HttpExchange(
            method="POST",
            url=resp.url,
            request_body=body,
            status_code=resp.status_code,
            content_type=resp.content_type(),
        )
        if resp.status_code >= 400:
            data, errs = _expect_json(resp.text, on_error="POST /v1/runs error was not valid JSON")
            if data is not None:
                errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
            out.append(
                _mk_check(
                    check_id="core.runtime.create_run",
                    name="POST /v1/runs (minimal success-path)",
                    status=ResultStatus.FAIL,
                    message=f"Expected 200 RunStatus, got {resp.status_code}",
                    exchange=exchange,
                    errors=errs,
                    timer=timer,
                )
            )
            return out

        data, errs = _expect_json(resp.text, on_error="POST /v1/runs success was not valid JSON")
        if errs:
            out.append(
                _mk_check(
                    check_id="core.runtime.create_run",
                    name="POST /v1/runs (minimal success-path)",
                    status=ResultStatus.FAIL,
                    message="RunStatus JSON parse failed",
                    exchange=exchange,
                    errors=errs,
                    timer=timer,
                )
            )
            return out

        schema_errors = self._schemas.validate(data, schema_path="schemas/runtime/runs/run_status.schema.json")
        if schema_errors:
            out.append(
                _mk_check(
                    check_id="core.runtime.create_run",
                    name="POST /v1/runs (minimal success-path)",
                    status=ResultStatus.FAIL,
                    message="RunStatus did not match schema",
                    exchange=HttpExchange(
                        method="POST",
                        url=resp.url,
                        request_body=body,
                        status_code=resp.status_code,
                        content_type=resp.content_type(),
                        response_body=data,
                    ),
                    errors=schema_errors,
                    timer=timer,
                )
            )
            return out

        out.append(
            _mk_check(
                check_id="core.runtime.create_run",
                name="POST /v1/runs (minimal success-path)",
                status=ResultStatus.PASS,
                message="OK",
                exchange=HttpExchange(
                    method="POST",
                    url=resp.url,
                    request_body=body,
                    status_code=resp.status_code,
                    content_type=resp.content_type(),
                    response_body=data,
                ),
                timer=timer,
            )
        )

        run_id_from_status = data.get("run_id") if isinstance(data, dict) else None
        if not isinstance(run_id_from_status, str) or not run_id_from_status:
            run_id_from_status = run_id

        out.extend(self._poll_runtime_run(run_id_from_status))
        out.extend(self._get_runtime_result(run_id_from_status))
        return out

    def _poll_runtime_run(self, run_id: str) -> list[CheckResult]:
        out: list[CheckResult] = []
        deadline = time.time() + self._options.poll_timeout_s
        last: Any | None = None
        while time.time() < deadline:
            timer = Timer()
            resp = self._client.request("GET", f"/v1/runs/{run_id}")
            if resp.status_code >= 400:
                data, errs = _expect_json(resp.text, on_error="GET /v1/runs/{run_id} error was not valid JSON")
                if data is not None:
                    errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
                out.append(
                    _mk_check(
                        check_id="core.runtime.poll_status",
                        name="GET /v1/runs/{run_id} (poll)",
                        status=ResultStatus.FAIL,
                        message=f"Expected 200 RunStatus, got {resp.status_code}",
                        exchange=HttpExchange(
                            method="GET",
                            url=resp.url,
                            status_code=resp.status_code,
                            content_type=resp.content_type(),
                            response_body=data,
                        ),
                        errors=errs,
                        timer=timer,
                    )
                )
                return out

            data, errs = _expect_json(resp.text, on_error="GET /v1/runs/{run_id} success was not valid JSON")
            if errs:
                out.append(
                    _mk_check(
                        check_id="core.runtime.poll_status",
                        name="GET /v1/runs/{run_id} (poll)",
                        status=ResultStatus.FAIL,
                        message="RunStatus JSON parse failed",
                        exchange=HttpExchange(
                            method="GET",
                            url=resp.url,
                            status_code=resp.status_code,
                            content_type=resp.content_type(),
                        ),
                        errors=errs,
                        timer=timer,
                    )
                )
                return out
            schema_errors = self._schemas.validate(data, schema_path="schemas/runtime/runs/run_status.schema.json")
            if schema_errors:
                out.append(
                    _mk_check(
                        check_id="core.runtime.poll_status",
                        name="GET /v1/runs/{run_id} (poll)",
                        status=ResultStatus.FAIL,
                        message="RunStatus did not match schema",
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
                )
                return out

            last = data
            state = data.get("state") if isinstance(data, dict) else None
            if state in {"succeeded", "failed", "canceled"}:
                out.append(
                    _mk_check(
                        check_id="core.runtime.poll_status",
                        name="GET /v1/runs/{run_id} (poll)",
                        status=ResultStatus.PASS,
                        message=f"Terminal state: {state}",
                        exchange=HttpExchange(
                            method="GET",
                            url=resp.url,
                            status_code=resp.status_code,
                            content_type=resp.content_type(),
                            response_body=data,
                        ),
                        timer=timer,
                    )
                )
                return out
            time.sleep(self._options.poll_interval_s)

        out.append(
            _mk_check(
                check_id="core.runtime.poll_status",
                name="GET /v1/runs/{run_id} (poll)",
                status=ResultStatus.FAIL,
                message="Polling timed out before terminal state",
                exchange=None if last is None else HttpExchange(method="GET", url="/v1/runs/{run_id}", response_body=last),
            )
        )
        return out

    def _get_runtime_result(self, run_id: str) -> list[CheckResult]:
        timer = Timer()
        resp = self._client.request("GET", f"/v1/runs/{run_id}/result")
        if resp.status_code >= 400:
            data, errs = _expect_json(resp.text, on_error="GET /v1/runs/{run_id}/result error was not valid JSON")
            if data is not None:
                errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
            return [
                _mk_check(
                    check_id="core.runtime.get_result",
                    name="GET /v1/runs/{run_id}/result",
                    status=ResultStatus.FAIL,
                    message=f"Expected 200 RunResult, got {resp.status_code}",
                    exchange=HttpExchange(
                        method="GET",
                        url=resp.url,
                        status_code=resp.status_code,
                        content_type=resp.content_type(),
                        response_body=data,
                    ),
                    errors=errs,
                    timer=timer,
                )
            ]
        data, errs = _expect_json(resp.text, on_error="GET /v1/runs/{run_id}/result success was not valid JSON")
        if errs:
            return [
                _mk_check(
                    check_id="core.runtime.get_result",
                    name="GET /v1/runs/{run_id}/result",
                    status=ResultStatus.FAIL,
                    message="RunResult JSON parse failed",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code),
                    errors=errs,
                    timer=timer,
                )
            ]
        schema_errors = self._schemas.validate(data, schema_path="schemas/runtime/runs/run_result.schema.json")
        if schema_errors:
            return [
                _mk_check(
                    check_id="core.runtime.get_result",
                    name="GET /v1/runs/{run_id}/result",
                    status=ResultStatus.FAIL,
                    message="RunResult did not match schema",
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
            ]
        return [
            _mk_check(
                check_id="core.runtime.get_result",
                name="GET /v1/runs/{run_id}/result",
                status=ResultStatus.PASS,
                message="OK",
                exchange=HttpExchange(
                    method="GET",
                    url=resp.url,
                    status_code=resp.status_code,
                    content_type=resp.content_type(),
                    response_body=data,
                ),
                timer=timer,
            )
        ]

    def _generate_args_from_schema(self, schema: Any) -> Any:
        if not isinstance(schema, dict):
            return {}
        schema_type = schema.get("type")
        if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
            return schema["enum"][0]
        if schema_type == "string":
            return "conformance"
        if schema_type == "integer":
            return 0
        if schema_type == "number":
            return 0
        if schema_type == "boolean":
            return False
        if schema_type == "array":
            return []
        if schema_type == "object":
            props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
            required = schema.get("required") if isinstance(schema.get("required"), list) else []
            out: dict[str, Any] = {}
            for key in required:
                if key in props:
                    out[key] = self._generate_args_from_schema(props[key])
            return out
        return {}

    def _check_core_tool_registry(self) -> list[CheckResult]:
        out: list[CheckResult] = []
        timer = Timer()
        resp = self._client.request("GET", "/v1/tools")
        if resp.status_code >= 400:
            data, errs = _expect_json(resp.text, on_error="GET /v1/tools error was not valid JSON")
            if data is not None:
                errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
            out.append(
                _mk_check(
                    check_id="core.tool_registry.list_tools",
                    name="GET /v1/tools",
                    status=ResultStatus.FAIL,
                    message=f"Expected 200 tool list, got {resp.status_code}",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                    errors=errs,
                    timer=timer,
                )
            )
            return out

        data, errs = _expect_json(resp.text, on_error="GET /v1/tools success was not valid JSON")
        if errs or not isinstance(data, list):
            out.append(
                _mk_check(
                    check_id="core.tool_registry.list_tools",
                    name="GET /v1/tools",
                    status=ResultStatus.FAIL,
                    message="Expected JSON array",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code),
                    errors=errs,
                    timer=timer,
                )
            )
            return out

        schema_errors: list[str] = []
        for i, item in enumerate(data):
            schema_errors.extend(
                [f"[{i}] {e}" for e in self._schemas.validate(item, schema_path="schemas/tool_registry/tools/tool_definition.schema.json")]
            )
        if schema_errors:
            out.append(
                _mk_check(
                    check_id="core.tool_registry.list_tools",
                    name="GET /v1/tools",
                    status=ResultStatus.FAIL,
                    message="Tool list did not match schema",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                    errors=schema_errors,
                    timer=timer,
                )
            )
            return out

        out.append(
            _mk_check(
                check_id="core.tool_registry.list_tools",
                name="GET /v1/tools",
                status=ResultStatus.PASS,
                message="OK",
                exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                timer=timer,
            )
        )

        selected: dict[str, Any] | None = None
        if self._options.tool_id:
            selected = next((t for t in data if isinstance(t, dict) and t.get("tool_id") == self._options.tool_id), None)
        if selected is None and self._options.tool_name:
            selected = next((t for t in data if isinstance(t, dict) and t.get("name") == self._options.tool_name), None)
        if selected is None and data:
            selected = data[0] if isinstance(data[0], dict) else None

        if selected is None:
            out.append(
                _mk_check(
                    check_id="core.tool_registry.select_tool",
                    name="Select tool for invocation",
                    status=ResultStatus.SKIP,
                    message="No tools available to invoke (provide --tool-id/--tool-name or configure registry)",
                )
            )
            out.append(
                _mk_check(
                    check_id="core.tool_registry.invoke_tool",
                    name="POST /v1/tool-invocations",
                    status=ResultStatus.WARN,
                    message="Skipping invocation because no tools were available",
                )
            )
            return out

        tool_id = selected.get("tool_id") if isinstance(selected, dict) else None
        if not isinstance(tool_id, str) or not tool_id:
            out.append(
                _mk_check(
                    check_id="core.tool_registry.select_tool",
                    name="Select tool for invocation",
                    status=ResultStatus.FAIL,
                    message="Selected tool missing tool_id",
                )
            )
            return out

        timer = Timer()
        resp = self._client.request("GET", f"/v1/tools/{tool_id}")
        if resp.status_code >= 400:
            data, errs = _expect_json(resp.text, on_error="GET /v1/tools/{tool_id} error was not valid JSON")
            if data is not None:
                errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
            out.append(
                _mk_check(
                    check_id="core.tool_registry.get_tool",
                    name="GET /v1/tools/{tool_id}",
                    status=ResultStatus.FAIL,
                    message=f"Expected 200 ToolDefinition, got {resp.status_code}",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                    errors=errs,
                    timer=timer,
                )
            )
            return out

        tool_def, errs = _expect_json(resp.text, on_error="GET /v1/tools/{tool_id} success was not valid JSON")
        if errs:
            out.append(
                _mk_check(
                    check_id="core.tool_registry.get_tool",
                    name="GET /v1/tools/{tool_id}",
                    status=ResultStatus.FAIL,
                    message="ToolDefinition JSON parse failed",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code),
                    errors=errs,
                    timer=timer,
                )
            )
            return out

        schema_errors = self._schemas.validate(tool_def, schema_path="schemas/tool_registry/tools/tool_definition.schema.json")
        if schema_errors:
            out.append(
                _mk_check(
                    check_id="core.tool_registry.get_tool",
                    name="GET /v1/tools/{tool_id}",
                    status=ResultStatus.FAIL,
                    message="ToolDefinition did not match schema",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=tool_def),
                    errors=schema_errors,
                    timer=timer,
                )
            )
            return out

        out.append(
            _mk_check(
                check_id="core.tool_registry.get_tool",
                name="GET /v1/tools/{tool_id}",
                status=ResultStatus.PASS,
                message="OK",
                exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=tool_def),
                timer=timer,
            )
        )

        input_schema = tool_def.get("input_schema") if isinstance(tool_def, dict) else None
        args = self._generate_args_from_schema(input_schema) if input_schema is not None else {}

        invocation_id = "inv_conformance_" + uuid.uuid4().hex[:12]
        body = {"invocation_id": invocation_id, "tool_id": tool_id, "args": args}
        timer = Timer()
        resp = self._client.request("POST", "/v1/tool-invocations", json_body=body)
        if resp.status_code >= 400:
            data, errs = _expect_json(resp.text, on_error="POST /v1/tool-invocations error was not valid JSON")
            if data is not None:
                errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
            out.append(
                _mk_check(
                    check_id="core.tool_registry.invoke_tool",
                    name="POST /v1/tool-invocations",
                    status=ResultStatus.FAIL,
                    message=f"Expected 200 ToolInvocationResult, got {resp.status_code}",
                    exchange=HttpExchange(method="POST", url=resp.url, request_body=body, status_code=resp.status_code, response_body=data),
                    errors=errs,
                    timer=timer,
                )
            )
            return out

        result, errs = _expect_json(resp.text, on_error="POST /v1/tool-invocations success was not valid JSON")
        if errs:
            out.append(
                _mk_check(
                    check_id="core.tool_registry.invoke_tool",
                    name="POST /v1/tool-invocations",
                    status=ResultStatus.FAIL,
                    message="ToolInvocationResult JSON parse failed",
                    exchange=HttpExchange(method="POST", url=resp.url, request_body=body, status_code=resp.status_code),
                    errors=errs,
                    timer=timer,
                )
            )
            return out

        schema_errors = self._schemas.validate(result, schema_path="schemas/tool_registry/tools/tool_invocation_result.schema.json")
        if schema_errors:
            out.append(
                _mk_check(
                    check_id="core.tool_registry.invoke_tool",
                    name="POST /v1/tool-invocations",
                    status=ResultStatus.FAIL,
                    message="ToolInvocationResult did not match schema",
                    exchange=HttpExchange(method="POST", url=resp.url, request_body=body, status_code=resp.status_code, response_body=result),
                    errors=schema_errors,
                    timer=timer,
                )
            )
            return out

        ok_value = result.get("ok") if isinstance(result, dict) else None
        status = ResultStatus.PASS if ok_value is True else ResultStatus.WARN
        message = "OK" if ok_value is True else "Invocation returned ok=false (schema-valid, but tool may not be configured)"
        out.append(
            _mk_check(
                check_id="core.tool_registry.invoke_tool",
                name="POST /v1/tool-invocations",
                status=status,
                message=message,
                exchange=HttpExchange(method="POST", url=resp.url, request_body=body, status_code=resp.status_code, response_body=result),
                timer=timer,
            )
        )
        return out

    def _check_core_daemon(self) -> list[CheckResult]:
        out: list[CheckResult] = []
        created_profile: str | None = None
        created_instances: list[str] = []

        def cleanup() -> None:
            if not self._options.cleanup:
                return
            for instance_id in created_instances:
                try:
                    self._client.request("DELETE", f"/v1/instances/{instance_id}")
                except Exception:
                    pass
            if created_profile is not None:
                try:
                    self._client.request("DELETE", f"/v1/admin/runtime-profiles/{created_profile}")
                except Exception:
                    pass

        try:
            # 1) list profiles
            timer = Timer()
            resp = self._client.request("GET", "/v1/admin/runtime-profiles")
            if resp.status_code >= 400:
                data, errs = _expect_json(resp.text, on_error="GET /v1/admin/runtime-profiles error was not valid JSON")
                if data is not None:
                    errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
                out.append(
                    _mk_check(
                        check_id="core.daemon.list_runtime_profiles",
                        name="GET /v1/admin/runtime-profiles",
                        status=ResultStatus.FAIL,
                        message=f"Expected 200 RuntimeProfileListResponse, got {resp.status_code}",
                        exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                        errors=errs,
                        timer=timer,
                    )
                )
                return out

            profile_list, errs = _expect_json(resp.text, on_error="GET /v1/admin/runtime-profiles success was not valid JSON")
            if errs:
                out.append(
                    _mk_check(
                        check_id="core.daemon.list_runtime_profiles",
                        name="GET /v1/admin/runtime-profiles",
                        status=ResultStatus.FAIL,
                        message="RuntimeProfileListResponse JSON parse failed",
                        exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code),
                        errors=errs,
                        timer=timer,
                    )
                )
                return out

            schema_errors = self._schemas.validate(
                profile_list, schema_path="schemas/daemon/runtime_profiles/runtime_profile_list_response.schema.json"
            )
            if schema_errors:
                out.append(
                    _mk_check(
                        check_id="core.daemon.list_runtime_profiles",
                        name="GET /v1/admin/runtime-profiles",
                        status=ResultStatus.FAIL,
                        message="RuntimeProfileListResponse did not match schema",
                        exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=profile_list),
                        errors=schema_errors,
                        timer=timer,
                    )
                )
                return out

            out.append(
                _mk_check(
                    check_id="core.daemon.list_runtime_profiles",
                    name="GET /v1/admin/runtime-profiles",
                    status=ResultStatus.PASS,
                    message="OK",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=profile_list),
                    timer=timer,
                )
            )

            profiles = profile_list.get("profiles") if isinstance(profile_list, dict) else None
            chosen_profile: str | None = None
            if self._options.runtime_profile:
                chosen_profile = self._options.runtime_profile
            elif isinstance(profiles, list) and profiles:
                first = profiles[0]
                if isinstance(first, dict) and isinstance(first.get("runtime_profile"), str):
                    chosen_profile = first["runtime_profile"]

            if chosen_profile is None:
                chosen_profile = "conformance_profile_" + uuid.uuid4().hex[:10]
                created_profile = chosen_profile
                timer = Timer()
                upsert_body = {"description": "ARP conformance test profile"}
                resp = self._client.request("PUT", f"/v1/admin/runtime-profiles/{chosen_profile}", json_body=upsert_body)
                if resp.status_code >= 400:
                    data, errs = _expect_json(resp.text, on_error="PUT /v1/admin/runtime-profiles/{runtime_profile} error was not valid JSON")
                    if data is not None:
                        errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
                    out.append(
                        _mk_check(
                            check_id="core.daemon.create_runtime_profile",
                            name="PUT /v1/admin/runtime-profiles/{runtime_profile}",
                            status=ResultStatus.FAIL,
                            message=f"Expected 200 RuntimeProfile, got {resp.status_code}",
                            exchange=HttpExchange(
                                method="PUT",
                                url=resp.url,
                                request_body=upsert_body,
                                status_code=resp.status_code,
                                response_body=data,
                            ),
                            errors=errs,
                            timer=timer,
                        )
                    )
                    return out

                profile, errs = _expect_json(resp.text, on_error="PUT /v1/admin/runtime-profiles/{runtime_profile} success was not valid JSON")
                if errs:
                    out.append(
                        _mk_check(
                            check_id="core.daemon.create_runtime_profile",
                            name="PUT /v1/admin/runtime-profiles/{runtime_profile}",
                            status=ResultStatus.FAIL,
                            message="RuntimeProfile JSON parse failed",
                            exchange=HttpExchange(method="PUT", url=resp.url, request_body=upsert_body, status_code=resp.status_code),
                            errors=errs,
                            timer=timer,
                        )
                    )
                    return out
                schema_errors = self._schemas.validate(
                    profile, schema_path="schemas/daemon/runtime_profiles/runtime_profile.schema.json"
                )
                if schema_errors:
                    out.append(
                        _mk_check(
                            check_id="core.daemon.create_runtime_profile",
                            name="PUT /v1/admin/runtime-profiles/{runtime_profile}",
                            status=ResultStatus.FAIL,
                            message="RuntimeProfile did not match schema",
                            exchange=HttpExchange(method="PUT", url=resp.url, request_body=upsert_body, status_code=resp.status_code, response_body=profile),
                            errors=schema_errors,
                            timer=timer,
                        )
                    )
                    return out
                out.append(
                    _mk_check(
                        check_id="core.daemon.create_runtime_profile",
                        name="PUT /v1/admin/runtime-profiles/{runtime_profile}",
                        status=ResultStatus.PASS,
                        message="OK",
                        exchange=HttpExchange(method="PUT", url=resp.url, request_body=upsert_body, status_code=resp.status_code, response_body=profile),
                        timer=timer,
                    )
                )

            # 2) create instance
            timer = Timer()
            create_body = {"runtime_profile": chosen_profile, "count": 1}
            resp = self._client.request("POST", "/v1/instances", json_body=create_body)
            if resp.status_code >= 400:
                data, errs = _expect_json(resp.text, on_error="POST /v1/instances error was not valid JSON")
                if data is not None:
                    errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
                out.append(
                    _mk_check(
                        check_id="core.daemon.create_instance",
                        name="POST /v1/instances",
                        status=ResultStatus.FAIL,
                        message=f"Expected 200 InstanceCreateResponse, got {resp.status_code}",
                        exchange=HttpExchange(method="POST", url=resp.url, request_body=create_body, status_code=resp.status_code, response_body=data),
                        errors=errs,
                        timer=timer,
                    )
                )
                return out

            created, errs = _expect_json(resp.text, on_error="POST /v1/instances success was not valid JSON")
            if errs:
                out.append(
                    _mk_check(
                        check_id="core.daemon.create_instance",
                        name="POST /v1/instances",
                        status=ResultStatus.FAIL,
                        message="InstanceCreateResponse JSON parse failed",
                        exchange=HttpExchange(method="POST", url=resp.url, request_body=create_body, status_code=resp.status_code),
                        errors=errs,
                        timer=timer,
                    )
                )
                return out

            schema_errors = self._schemas.validate(
                created, schema_path="schemas/daemon/instances/instance_create_response.schema.json"
            )
            if schema_errors:
                out.append(
                    _mk_check(
                        check_id="core.daemon.create_instance",
                        name="POST /v1/instances",
                        status=ResultStatus.FAIL,
                        message="InstanceCreateResponse did not match schema",
                        exchange=HttpExchange(method="POST", url=resp.url, request_body=create_body, status_code=resp.status_code, response_body=created),
                        errors=schema_errors,
                        timer=timer,
                    )
                )
                return out

            instances = created.get("instances") if isinstance(created, dict) else None
            instance_id: str | None = None
            if isinstance(instances, list) and instances:
                first = instances[0]
                if isinstance(first, dict) and isinstance(first.get("instance_id"), str):
                    instance_id = first["instance_id"]
            if not instance_id:
                out.append(
                    _mk_check(
                        check_id="core.daemon.create_instance",
                        name="POST /v1/instances",
                        status=ResultStatus.FAIL,
                        message="InstanceCreateResponse.instances[0].instance_id missing",
                        exchange=HttpExchange(method="POST", url=resp.url, request_body=create_body, status_code=resp.status_code, response_body=created),
                        timer=timer,
                    )
                )
                return out

            created_instances.append(instance_id)
            out.append(
                _mk_check(
                    check_id="core.daemon.create_instance",
                    name="POST /v1/instances",
                    status=ResultStatus.PASS,
                    message="OK",
                    exchange=HttpExchange(method="POST", url=resp.url, request_body=create_body, status_code=resp.status_code, response_body=created),
                    timer=timer,
                )
            )

            # 3) submit run async
            run_id = "run_conformance_" + uuid.uuid4().hex[:12]
            run_body = {
                "run_id": run_id,
                "input": {"goal": "ARP conformance daemon run"},
                "runtime_selector": {"instance_id": instance_id},
                "limits": {"timeout_ms": 10_000, "max_steps": 1},
            }
            timer = Timer()
            resp = self._client.request("POST", "/v1/runs", json_body=run_body)
            if resp.status_code != 202:
                data, errs = _expect_json(resp.text, on_error="POST /v1/runs error was not valid JSON")
                if data is not None:
                    errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
                out.append(
                    _mk_check(
                        check_id="core.daemon.submit_run",
                        name="POST /v1/runs",
                        status=ResultStatus.FAIL,
                        message=f"Expected 202 RunStatus, got {resp.status_code}",
                        exchange=HttpExchange(method="POST", url=resp.url, request_body=run_body, status_code=resp.status_code, response_body=data),
                        errors=errs,
                        timer=timer,
                    )
                )
                return out

            status_obj, errs = _expect_json(resp.text, on_error="POST /v1/runs success was not valid JSON")
            if errs:
                out.append(
                    _mk_check(
                        check_id="core.daemon.submit_run",
                        name="POST /v1/runs",
                        status=ResultStatus.FAIL,
                        message="RunStatus JSON parse failed",
                        exchange=HttpExchange(method="POST", url=resp.url, request_body=run_body, status_code=resp.status_code),
                        errors=errs,
                        timer=timer,
                    )
                )
                return out
            schema_errors = self._schemas.validate(status_obj, schema_path="schemas/runtime/runs/run_status.schema.json")
            if schema_errors:
                out.append(
                    _mk_check(
                        check_id="core.daemon.submit_run",
                        name="POST /v1/runs",
                        status=ResultStatus.FAIL,
                        message="RunStatus did not match schema",
                        exchange=HttpExchange(method="POST", url=resp.url, request_body=run_body, status_code=resp.status_code, response_body=status_obj),
                        errors=schema_errors,
                        timer=timer,
                    )
                )
                return out
            out.append(
                _mk_check(
                    check_id="core.daemon.submit_run",
                    name="POST /v1/runs",
                    status=ResultStatus.PASS,
                    message="OK",
                    exchange=HttpExchange(method="POST", url=resp.url, request_body=run_body, status_code=resp.status_code, response_body=status_obj),
                    timer=timer,
                )
            )

            # 4) poll + result
            out.extend(self._poll_daemon_run(run_id))
            out.extend(self._get_daemon_result(run_id))
            return out
        finally:
            cleanup()

    def _poll_daemon_run(self, run_id: str) -> list[CheckResult]:
        out: list[CheckResult] = []
        deadline = time.time() + self._options.poll_timeout_s
        last: Any | None = None
        while time.time() < deadline:
            timer = Timer()
            resp = self._client.request("GET", f"/v1/runs/{run_id}")
            if resp.status_code >= 400:
                data, errs = _expect_json(resp.text, on_error="GET /v1/runs/{run_id} error was not valid JSON")
                if data is not None:
                    errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
                out.append(
                    _mk_check(
                        check_id="core.daemon.poll_status",
                        name="GET /v1/runs/{run_id} (poll)",
                        status=ResultStatus.FAIL,
                        message=f"Expected 200 RunStatus, got {resp.status_code}",
                        exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                        errors=errs,
                        timer=timer,
                    )
                )
                return out

            data, errs = _expect_json(resp.text, on_error="GET /v1/runs/{run_id} success was not valid JSON")
            if errs:
                out.append(
                    _mk_check(
                        check_id="core.daemon.poll_status",
                        name="GET /v1/runs/{run_id} (poll)",
                        status=ResultStatus.FAIL,
                        message="RunStatus JSON parse failed",
                        exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code),
                        errors=errs,
                        timer=timer,
                    )
                )
                return out
            schema_errors = self._schemas.validate(data, schema_path="schemas/runtime/runs/run_status.schema.json")
            if schema_errors:
                out.append(
                    _mk_check(
                        check_id="core.daemon.poll_status",
                        name="GET /v1/runs/{run_id} (poll)",
                        status=ResultStatus.FAIL,
                        message="RunStatus did not match schema",
                        exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                        errors=schema_errors,
                        timer=timer,
                    )
                )
                return out

            last = data
            state = data.get("state") if isinstance(data, dict) else None
            if state in {"succeeded", "failed", "canceled"}:
                out.append(
                    _mk_check(
                        check_id="core.daemon.poll_status",
                        name="GET /v1/runs/{run_id} (poll)",
                        status=ResultStatus.PASS,
                        message=f"Terminal state: {state}",
                        exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                        timer=timer,
                    )
                )
                return out
            time.sleep(self._options.poll_interval_s)

        out.append(
            _mk_check(
                check_id="core.daemon.poll_status",
                name="GET /v1/runs/{run_id} (poll)",
                status=ResultStatus.FAIL,
                message="Polling timed out before terminal state",
                exchange=None if last is None else HttpExchange(method="GET", url="/v1/runs/{run_id}", response_body=last),
            )
        )
        return out

    def _get_daemon_result(self, run_id: str) -> list[CheckResult]:
        timer = Timer()
        resp = self._client.request("GET", f"/v1/runs/{run_id}/result")
        if resp.status_code >= 400:
            data, errs = _expect_json(resp.text, on_error="GET /v1/runs/{run_id}/result error was not valid JSON")
            if data is not None:
                errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
            return [
                _mk_check(
                    check_id="core.daemon.get_result",
                    name="GET /v1/runs/{run_id}/result",
                    status=ResultStatus.FAIL,
                    message=f"Expected 200 RunResult, got {resp.status_code}",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                    errors=errs,
                    timer=timer,
                )
            ]

        data, errs = _expect_json(resp.text, on_error="GET /v1/runs/{run_id}/result success was not valid JSON")
        if errs:
            return [
                _mk_check(
                    check_id="core.daemon.get_result",
                    name="GET /v1/runs/{run_id}/result",
                    status=ResultStatus.FAIL,
                    message="RunResult JSON parse failed",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code),
                    errors=errs,
                    timer=timer,
                )
            ]
        schema_errors = self._schemas.validate(data, schema_path="schemas/runtime/runs/run_result.schema.json")
        if schema_errors:
            return [
                _mk_check(
                    check_id="core.daemon.get_result",
                    name="GET /v1/runs/{run_id}/result",
                    status=ResultStatus.FAIL,
                    message="RunResult did not match schema",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                    errors=schema_errors,
                    timer=timer,
                )
            ]
        return [
            _mk_check(
                check_id="core.daemon.get_result",
                name="GET /v1/runs/{run_id}/result",
                status=ResultStatus.PASS,
                message="OK",
                exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                timer=timer,
            )
        ]

    def _check_deep_runtime(self) -> list[CheckResult]:
        # Optional endpoints are best-effort and may be SKIP.
        out: list[CheckResult] = []
        dummy_run_id = "run_conformance_" + uuid.uuid4().hex[:12]
        # cancel
        timer = Timer()
        resp = self._client.request("POST", f"/v1/runs/{dummy_run_id}:cancel", json_body={})
        if resp.status_code in {404, 405}:
            out.append(
                _mk_check(
                    check_id="deep.runtime.cancel",
                    name="POST /v1/runs/{run_id}:cancel (optional)",
                    status=ResultStatus.SKIP,
                    message="Endpoint not implemented (404/405)",
                    timer=timer,
                )
            )
        elif resp.status_code >= 400:
            data, errs = _expect_json(resp.text, on_error="Cancel error was not valid JSON")
            if data is not None:
                errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
            out.append(
                _mk_check(
                    check_id="deep.runtime.cancel",
                    name="POST /v1/runs/{run_id}:cancel (optional)",
                    status=ResultStatus.PASS,
                    message="Endpoint responded with error envelope (shape OK)",
                    exchange=HttpExchange(method="POST", url=resp.url, request_body={}, status_code=resp.status_code, response_body=data),
                    errors=errs,
                    timer=timer,
                )
            )
        else:
            data, errs = _expect_json(resp.text, on_error="Cancel success was not valid JSON")
            schema_errors = [] if data is None else self._schemas.validate(data, schema_path="schemas/runtime/runs/run_status.schema.json")
            status = ResultStatus.FAIL if errs or schema_errors else ResultStatus.PASS
            out.append(
                _mk_check(
                    check_id="deep.runtime.cancel",
                    name="POST /v1/runs/{run_id}:cancel (optional)",
                    status=status,
                    message="OK" if status == ResultStatus.PASS else "Response did not match expected schema",
                    exchange=HttpExchange(method="POST", url=resp.url, request_body={}, status_code=resp.status_code, response_body=data),
                    errors=[*errs, *schema_errors],
                    timer=timer,
                )
            )

        # events (SSE)
        timer = Timer()
        resp = self._client.stream_sample(
            "GET",
            f"/v1/runs/{dummy_run_id}/events",
            headers={"Accept": "text/event-stream"},
            max_bytes=2048,
        )
        ct = resp.content_type()
        if resp.status_code in {404, 405}:
            out.append(
                _mk_check(
                    check_id="deep.runtime.events",
                    name="GET /v1/runs/{run_id}/events (optional)",
                    status=ResultStatus.SKIP,
                    message="Endpoint not implemented (404/405)",
                    timer=timer,
                )
            )
        elif resp.status_code >= 400:
            data, errs = _expect_json(resp.text, on_error="Events error was not valid JSON")
            if data is not None:
                errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
            out.append(
                _mk_check(
                    check_id="deep.runtime.events",
                    name="GET /v1/runs/{run_id}/events (optional)",
                    status=ResultStatus.PASS,
                    message="Endpoint responded with error envelope (shape OK)",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, content_type=ct, response_body=data),
                    errors=errs,
                    timer=timer,
                )
            )
        else:
            if ct != "text/event-stream":
                out.append(
                    _mk_check(
                        check_id="deep.runtime.events",
                        name="GET /v1/runs/{run_id}/events (optional)",
                        status=ResultStatus.FAIL,
                        message=f"Expected Content-Type text/event-stream, got {ct!r}",
                        exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, content_type=ct),
                        timer=timer,
                    )
                )
            else:
                validated_any = False
                schema_errors: list[str] = []
                for raw_line in resp.text.splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        line = line.removeprefix("data:").strip()
                    if not line.startswith("{"):
                        continue
                    payload, errs = _expect_json(line, on_error="SSE line was not valid JSON")
                    if errs:
                        schema_errors.extend(errs)
                        continue
                    schema_errors.extend(self._schemas.validate(payload, schema_path="schemas/runtime/runs/run_event.schema.json"))
                    validated_any = True
                    break

                status = ResultStatus.PASS if not schema_errors else ResultStatus.WARN
                message = "OK" if validated_any and not schema_errors else "SSE stream reachable; no event validated from sample"
                out.append(
                    _mk_check(
                        check_id="deep.runtime.events",
                        name="GET /v1/runs/{run_id}/events (optional)",
                        status=status,
                        message=message,
                        exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, content_type=ct),
                        errors=schema_errors,
                        timer=timer,
                    )
                )
        return out

    def _check_deep_daemon(self) -> list[CheckResult]:
        out: list[CheckResult] = []
        dummy_run_id = "run_conformance_" + uuid.uuid4().hex[:12]
        timer = Timer()
        resp = self._client.request("GET", f"/v1/runs/{dummy_run_id}/trace")
        if resp.status_code in {404, 405}:
            out.append(
                _mk_check(
                    check_id="deep.daemon.trace",
                    name="GET /v1/runs/{run_id}/trace (optional)",
                    status=ResultStatus.SKIP,
                    message="Endpoint not implemented (404/405)",
                    timer=timer,
                )
            )
            return out
        if resp.status_code >= 400:
            data, errs = _expect_json(resp.text, on_error="Trace error was not valid JSON")
            if data is not None:
                errs.extend(self._schemas.validate(data, schema_path="schemas/common/error.schema.json"))
            out.append(
                _mk_check(
                    check_id="deep.daemon.trace",
                    name="GET /v1/runs/{run_id}/trace (optional)",
                    status=ResultStatus.PASS,
                    message="Endpoint responded with error envelope (shape OK)",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                    errors=errs,
                    timer=timer,
                )
            )
            return out

        data, errs = _expect_json(resp.text, on_error="Trace success was not valid JSON")
        if errs:
            out.append(
                _mk_check(
                    check_id="deep.daemon.trace",
                    name="GET /v1/runs/{run_id}/trace (optional)",
                    status=ResultStatus.FAIL,
                    message="Trace response JSON parse failed",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code),
                    errors=errs,
                    timer=timer,
                )
            )
            return out

        schema_errors = self._schemas.validate(data, schema_path="schemas/daemon/runs/trace_response.schema.json")
        if schema_errors:
            out.append(
                _mk_check(
                    check_id="deep.daemon.trace",
                    name="GET /v1/runs/{run_id}/trace (optional)",
                    status=ResultStatus.FAIL,
                    message="TraceResponse did not match schema",
                    exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                    errors=schema_errors,
                    timer=timer,
                )
            )
            return out
        out.append(
            _mk_check(
                check_id="deep.daemon.trace",
                name="GET /v1/runs/{run_id}/trace (optional)",
                status=ResultStatus.PASS,
                message="OK",
                exchange=HttpExchange(method="GET", url=resp.url, status_code=resp.status_code, response_body=data),
                timer=timer,
            )
        )
        return out
