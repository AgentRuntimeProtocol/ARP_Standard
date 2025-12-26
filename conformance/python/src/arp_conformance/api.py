from __future__ import annotations

from arp_conformance.runner import ConformanceRunner, RunnerOptions
from arp_conformance.report import ConformanceReport


def run(
    *,
    service: str,
    base_url: str,
    tier: str,
    headers: dict[str, str] | None = None,
    options: RunnerOptions | None = None,
) -> ConformanceReport:
    """
    Run `arp-conformance` programmatically.

    This is intentionally small and stable: pass a service kind, base URL, and tier.
    """

    runner = ConformanceRunner(base_url=base_url, headers=headers, options=options or RunnerOptions())
    return runner.run(service=service, tier=tier)


def run_all(
    *,
    tier: str,
    run_gateway_url: str | None = None,
    run_coordinator_url: str | None = None,
    atomic_executor_url: str | None = None,
    composite_executor_url: str | None = None,
    node_registry_url: str | None = None,
    selection_url: str | None = None,
    pdp_url: str | None = None,
    headers: dict[str, str] | None = None,
    options: RunnerOptions | None = None,
) -> list[ConformanceReport]:
    """
    Run conformance across multiple services.

    Any URL left as `None` is skipped.
    """

    reports: list[ConformanceReport] = []
    for service, url in [
        ("run-gateway", run_gateway_url),
        ("run-coordinator", run_coordinator_url),
        ("atomic-executor", atomic_executor_url),
        ("composite-executor", composite_executor_url),
        ("node-registry", node_registry_url),
        ("selection", selection_url),
        ("pdp", pdp_url),
    ]:
        if url is None:
            continue
        reports.append(run(service=service, base_url=url, tier=tier, headers=headers, options=options))
    return reports
