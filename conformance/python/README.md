# ARP Conformance Toolkit `arp-conformance`

`arp-conformance` is the official conformance checker for **ARP Standard (v1)** HTTP services in the node-centric stack:

- Run Gateway
- Run Coordinator
- Atomic Executor
- Composite Executor
- Node Registry
- Selection
- PDP (optional component)

It runs black-box HTTP checks against a base URL and validates:
- Required routes exist and are reachable
- Success + error responses match the ARP envelopes (including `ErrorEnvelope`)
- Response bodies validate against the **normative JSON Schemas** embedded in this package

What it does **not** validate:
- Planner/model quality
- Performance, scalability, or security posture
- Internal implementation details (wire-level only)

This package is **SDK-independent**: it does not depend on generated SDK packages like `arp-standard-model`, `arp-standard-client`, or `arp-standard-server`.

> [!IMPORTANT]
> **Version pinning**
>
> This toolkit embeds a spec snapshot. Pin `arp-conformance==X.Y.Z` to validate services built against the same ARP spec / SDK version `X.Y.Z`.
>
> View the embedded snapshot:
> - `arp-conformance --version`
> - `python -c "import arp_conformance; print(arp_conformance.SPEC_REF)"`

## Install

```bash
python3 -m pip install arp-conformance
```

## Quick start

### Smoke test

Safest level of testing (`GET`-only).

```bash
arp-conformance check run-gateway --url http://localhost:8080 --tier smoke
```

### Surface conformance

Validates required endpoints and envelope schemas without creating resources.

```bash
arp-conformance check run-gateway --url http://localhost:8080 --tier surface
arp-conformance check run-coordinator --url http://localhost:8081 --tier surface
arp-conformance check node-registry --url http://localhost:8082 --tier surface
```

### Run conformance on multiple services

```bash
arp-conformance check all \
  --run-gateway-url http://localhost:8080 \
  --run-coordinator-url http://localhost:8081 \
  --node-registry-url http://localhost:8082 \
  --tier surface
```

## Tiers at a glance

| Tier      | What it tests                                                    | Creates state? | Safe for `prod`? | Typical use                               |
| --------- | ----------------------------------------------------------------- | -------------: | -------------: | ----------------------------------------- |
| `smoke`   | Service is reachable + speaking ARP (`/v1/health`, `/v1/version`) |             No |            Yes | Fast local sanity check; PR gating        |
| `surface` | Required routes exist + success/error envelopes are schema-valid  |             No |         Usually | Early implementation; contract regression |
| `core`    | Placeholder for end-to-end success-paths (see note below)         |             No |            Yes | Future staged validation                  |
| `deep`    | Placeholder for optional endpoints + richer behaviors             |             No |            Yes | Future pre-release validation             |

> [!NOTE]
> For node-centric v1, `core` and `deep` are not yet defined. The toolkit reports `SKIP` for these tiers until
> the spec defines portable end-to-end flows. Use `smoke` and `surface` for now.

## Output and reports

### Example output (text)

```text
service=run-gateway tier=surface spec=spec/v1@v0.3.1
counts={'PASS': 5, 'FAIL': 0, 'WARN': 0, 'SKIP': 0} ok=True
- PASS smoke.health: OK
- PASS smoke.version: OK
```

### Export JSON / JUnit

```bash
arp-conformance check run-gateway --url http://localhost:8080 --tier surface --format json --out arp-conformance.json
arp-conformance check run-gateway --url http://localhost:8080 --tier surface --format junit --out arp-conformance.xml
```

### CI gating

- By default, the CLI exits non-zero when there is at least one `FAIL`.
- Use `--strict` to also fail on `WARN` and `SKIP`.

## Compatibility / pinning

Rule of thumb: pin `arp-conformance==X.Y.Z` to validate services targeting the ARP spec / SDK release `X.Y.Z`.

```bash
pipx install "arp-conformance==0.3.1"
arp-conformance --version
python -c "import arp_conformance; print(arp_conformance.SPEC_REF)"
```

## Authentication and headers

If your service requires auth, pass headers:

```bash
arp-conformance check run-gateway \
  --url https://example.com \
  --tier surface \
  --headers "Authorization=Bearer ..."
```

For CI, prefer a headers file:

```bash
cat > headers.env <<'EOT'
Authorization=Bearer ...
EOT

arp-conformance check run-gateway --url https://example.com --tier surface --headers-file headers.env
```

## CI recipes (GitHub Actions)

This repo provides a composite action that installs `arp-conformance` from PyPI and runs it:
- `AgentRuntimeProtocol/ARP_Standard/.github/actions/arp-conformance`

By default, when you reference the action as `.../arp-conformance@vX.Y.Z`, it installs `arp-conformance==X.Y.Z`.

### Surface gate on PR (no resource creation)

```yaml
name: arp-conformance
on: [pull_request]
jobs:
  surface:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Start your service under test (docker compose, process, etc) before running conformance.
      - uses: AgentRuntimeProtocol/ARP_Standard/.github/actions/arp-conformance@v0.3.1
        with:
          service: run-gateway
          url: http://localhost:8080
          tier: surface
          report_format: json
          report_path: arp-conformance.json
```

## Commands at a glance

- `arp-conformance check run-gateway --url <base-url> [flags]`
- `arp-conformance check run-coordinator --url <base-url> [flags]`
- `arp-conformance check atomic-executor --url <base-url> [flags]`
- `arp-conformance check composite-executor --url <base-url> [flags]`
- `arp-conformance check node-registry --url <base-url> [flags]`
- `arp-conformance check selection --url <base-url> [flags]`
- `arp-conformance check pdp --url <base-url> [flags]`
- `arp-conformance check all --run-gateway-url ... --run-coordinator-url ... [flags]`

## Flags (common)

- `--tier smoke|surface|core|deep`
- `--headers KEY=VALUE` (repeatable)
- `--headers-file path`
- `--timeout <seconds>`
- `--retries <n>`
- `--strict`
- `--format text|json|junit`
- `--out <path>`
- `--spec v1`
- `--spec-path <path>`
