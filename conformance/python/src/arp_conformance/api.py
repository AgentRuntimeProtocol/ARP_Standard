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
    runtime_url: str | None = None,
    tool_registry_url: str | None = None,
    daemon_url: str | None = None,
    headers: dict[str, str] | None = None,
    options: RunnerOptions | None = None,
) -> list[ConformanceReport]:
    """
    Run conformance across multiple services.

    Any URL left as `None` is skipped.
    """

    reports: list[ConformanceReport] = []
    for service, url in [
        ("runtime", runtime_url),
        ("tool-registry", tool_registry_url),
        ("daemon", daemon_url),
    ]:
        if url is None:
            continue
        reports.append(run(service=service, base_url=url, tier=tier, headers=headers, options=options))
    return reports

