from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from arp_conformance import SPEC_REF, __version__
from arp_conformance.report import ConformanceReport, reports_to_junit_xml

if TYPE_CHECKING:
    from arp_conformance.runner import RunnerOptions


def _parse_headers(values: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise SystemExit(f"Invalid --headers value (expected KEY=VALUE): {raw}")
        key, value = raw.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _load_headers_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise SystemExit(f"Invalid headers file line (expected KEY=VALUE): {line}")
        key, value = stripped.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _write_output(report: ConformanceReport, *, fmt: str, out_path: str | None) -> None:
    if fmt == "json":
        text = report.to_json()
    elif fmt == "junit":
        text = report.to_junit_xml()
    else:
        lines = [
            f"service={report.service} tier={report.tier} spec={report.spec_ref}",
            f"counts={report.counts()} ok={report.ok}",
        ]
        for r in report.results:
            lines.append(f"- {r.status.value} {r.check_id}: {r.message}")
            if r.status.value in {"FAIL", "WARN"} and r.errors:
                for e in r.errors:
                    lines.append(f"    - {e}")
        text = "\n".join(lines) + "\n"

    if out_path is None:
        sys.stdout.write(text)
        return
    Path(out_path).write_text(text, encoding="utf-8")
    sys.stdout.write(f"Wrote report: {out_path}\n")


def _write_multi_output(reports: list[ConformanceReport], *, fmt: str, out_path: str | None) -> None:
    if fmt == "json":
        payload = {"reports": [r.to_dict() for r in reports], "ok": all(r.ok for r in reports)}
        text = __import__("json").dumps(payload, indent=2, sort_keys=False) + "\n"
    elif fmt == "junit":
        text = reports_to_junit_xml(reports) + "\n"
    else:
        chunks: list[str] = []
        for report in reports:
            chunks.append(f"service={report.service} tier={report.tier} spec={report.spec_ref}")
            chunks.append(f"counts={report.counts()} ok={report.ok}")
            for r in report.results:
                chunks.append(f"- {r.status.value} {r.check_id}: {r.message}")
                if r.status.value in {"FAIL", "WARN"} and r.errors:
                    for e in r.errors:
                        chunks.append(f"    - {e}")
            chunks.append("")
        text = "\n".join(chunks)
    if out_path is None:
        sys.stdout.write(text)
        return
    Path(out_path).write_text(text, encoding="utf-8")
    sys.stdout.write(f"Wrote report: {out_path}\n")


def _exit_code(reports: list[ConformanceReport], *, strict: bool) -> int:
    if strict:
        return 0 if all(r.ok_strict() for r in reports) else 1
    return 0 if all(r.ok for r in reports) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arp-conformance")
    parser.add_argument("--version", action="version", version=f"arp-conformance {__version__} ({SPEC_REF})")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Run conformance checks")
    check_sub = check.add_subparsers(dest="service", required=True)

    def add_common_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--tier", default="smoke", choices=["smoke", "surface", "core", "deep"])
        p.add_argument("--headers", action="append", default=[], help="Repeatable KEY=VALUE headers")
        p.add_argument("--headers-file", type=str, help="Path to a KEY=VALUE per line file")
        p.add_argument("--timeout", type=float, default=10.0)
        p.add_argument("--retries", type=int, default=0)
        p.add_argument("--poll-timeout", type=float, default=60.0)
        p.add_argument("--poll-interval", type=float, default=1.0)
        p.add_argument("--allow-mutations", action="store_true", help="Allow mutation endpoints (required for core/deep)")
        p.add_argument("--no-cleanup", action="store_true", help="Disable cleanup of created resources")
        p.add_argument("--strict", action="store_true", help="Treat WARN/SKIP as failures")
        p.add_argument("--format", default="text", choices=["text", "json", "junit"])
        p.add_argument("--out", type=str, help="Write report to file instead of stdout")
        p.add_argument("--spec", default="v1", choices=["v1"])
        p.add_argument(
            "--spec-path",
            type=str,
            help="Use local spec directory (containing v1/ or a repo root containing spec/...)",
        )

    run_gateway = check_sub.add_parser("run-gateway", help="Check an ARP Run Gateway service")
    add_common_flags(run_gateway)
    run_gateway.add_argument("--url", required=True)

    run_coordinator = check_sub.add_parser("run-coordinator", help="Check an ARP Run Coordinator service")
    add_common_flags(run_coordinator)
    run_coordinator.add_argument("--url", required=True)

    atomic_executor = check_sub.add_parser("atomic-executor", help="Check an ARP Atomic Executor service")
    add_common_flags(atomic_executor)
    atomic_executor.add_argument("--url", required=True)

    composite_executor = check_sub.add_parser("composite-executor", help="Check an ARP Composite Executor service")
    add_common_flags(composite_executor)
    composite_executor.add_argument("--url", required=True)

    node_registry = check_sub.add_parser("node-registry", help="Check an ARP Node Registry service")
    add_common_flags(node_registry)
    node_registry.add_argument("--url", required=True)

    selection = check_sub.add_parser("selection", help="Check an ARP Selection service")
    add_common_flags(selection)
    selection.add_argument("--url", required=True)

    pdp = check_sub.add_parser("pdp", help="Check an ARP PDP service")
    add_common_flags(pdp)
    pdp.add_argument("--url", required=True)

    all_services = check_sub.add_parser("all", help="Check multiple ARP services")
    add_common_flags(all_services)
    all_services.add_argument("--run-gateway-url", type=str)
    all_services.add_argument("--run-coordinator-url", type=str)
    all_services.add_argument("--atomic-executor-url", type=str)
    all_services.add_argument("--composite-executor-url", type=str)
    all_services.add_argument("--node-registry-url", type=str)
    all_services.add_argument("--selection-url", type=str)
    all_services.add_argument("--pdp-url", type=str)

    args = parser.parse_args(argv)

    # Avoid importing HTTP dependencies for `--version`.
    from arp_conformance.api import run, run_all
    from arp_conformance.runner import RunnerOptions

    headers = _parse_headers(args.headers)
    if args.headers_file:
        headers.update(_load_headers_file(Path(args.headers_file)))
    if not headers:
        headers = None

    options = RunnerOptions(
        timeout_s=args.timeout,
        retries=args.retries,
        poll_timeout_s=args.poll_timeout,
        poll_interval_s=args.poll_interval,
        allow_mutations=args.allow_mutations,
        cleanup=not args.no_cleanup,
        strict=args.strict,
        spec_path=args.spec_path,
        spec_version=args.spec,
    )

    if args.command == "check" and args.service == "all":
        reports = run_all(
            tier=args.tier,
            run_gateway_url=args.run_gateway_url,
            run_coordinator_url=args.run_coordinator_url,
            atomic_executor_url=args.atomic_executor_url,
            composite_executor_url=args.composite_executor_url,
            node_registry_url=args.node_registry_url,
            selection_url=args.selection_url,
            pdp_url=args.pdp_url,
            headers=headers,
            options=options,
        )
        if not reports:
            raise SystemExit("No service URLs provided (use --run-gateway-url/--run-coordinator-url/...)")
        _write_multi_output(reports, fmt=args.format, out_path=args.out)
        return _exit_code(reports, strict=args.strict)

    report = run(
        service=args.service,
        base_url=args.url,
        tier=args.tier,
        headers=headers,
        options=options,
    )
    _write_output(report, fmt=args.format, out_path=args.out)
    return _exit_code([report], strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
