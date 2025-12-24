# ARP Conformance Toolkit `arp-conformance`

`arp-conformance` is the official conformance checker for **ARP Standard (v1)** HTTP services including Runtime, Tool Registry, and Daemon.

It runs black-box HTTP checks against a base URL and validates:
- Required routes exist and are reachable
- Success + error responses match the ARP envelopes including `ErrorEnvelope`
- Response bodies are valid against the **normative JSON Schemas** from the ARP Standard snapshot embedded in this package

What it does **not** validate:
- “Agent quality” / correctness of model outputs
- Performance, scalability, security posture, or multi-tenancy
- Internal implementation details, since it is wire-level only

This package is **SDK-independent**: it does not depend on generated SDK packages like `arp-standard-model`, `arp-standard-client`, or `arp-standard-server`. It validates directly from the spec snapshot.

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

Most basic level of testing, considered the safest option since it is `GET`-only.

```bash
arp-conformance check runtime --url http://localhost:8081 --tier smoke
```

### Surface conformance

The second safest conformance test, where no resource **creation** happens. 

```bash
arp-conformance check runtime --url http://localhost:8081 --tier surface
arp-conformance check tool-registry --url http://localhost:8082 --tier surface
arp-conformance check daemon --url http://localhost:8083 --tier surface
```

### Run conformance on multiple services

```bash
arp-conformance check all \
  --runtime-url http://localhost:8081 \
  --tool-registry-url http://localhost:8082 \
  --daemon-url http://localhost:8083 \
  --tier surface
```

## Tiers at a glance

| Tier      | What it tests                                                    | Creates state? | Safe for `prod`? | Typical use                               |
| --------- | ----------------------------------------------------------------- | -------------: | -------------: | ----------------------------------------- |
| `smoke`   | Service is reachable + speaking ARP (`/v1/health`, `/v1/version`) |             No |            Yes | Fast local sanity check; PR gating        |
| `surface` | Required routes exist + success/error envelopes are schema-valid  |             No |         Usually | Early implementation; contract regression |
| `core`    | Minimal success-path workflow works end-to-end                    |       **Yes** |             No | Staging; nightly CI                       |
| `deep`    | Optional endpoints + stronger behavioral guarantees               |       **Yes** |             No | Pre-release / “full” validation           |

Conformance definition:

> A service “passes ARP conformance (tier X)” if `arp-conformance` produces **no FAIL** results at that tier (and optionally no `WARN`/`SKIP` when using `--strict`).

## Safety (before you run `core` / `deep`)

`core` and `deep` require `--allow-mutations` and will send real state-changing requests, depending on service type:
- Runtime: creates a run (`POST /v1/runs`) and polls status/result.
- Tool Registry: invokes a tool (`POST /v1/tool-invocations`).
- Daemon: may create a runtime profile (if none exists), creates an instance, submits a run, polls status/result, and cleans up by default.

Use staging/dev URLs unless you are confident about side effects. If you want to keep resources for debugging, use `--no-cleanup`.

## Core conformance (creates real state; staging/dev recommended)

```bash
arp-conformance check runtime --url http://localhost:8081 --tier core --allow-mutations
arp-conformance check tool-registry --url http://localhost:8082 --tier core --allow-mutations
arp-conformance check daemon --url http://localhost:8083 --tier core --allow-mutations
```

## Output and reports

### Example output (text)

```text
service=runtime tier=surface spec=spec/v1@v0.2.6
counts={'PASS': 10, 'FAIL': 0, 'WARN': 0, 'SKIP': 0} ok=True
- PASS smoke.health: OK
- PASS smoke.version: OK
```

### Export JSON / JUnit

```bash
arp-conformance check runtime --url http://localhost:8081 --tier surface --format json --out arp-conformance.json
arp-conformance check runtime --url http://localhost:8081 --tier core --allow-mutations --format junit --out arp-conformance.xml
```

### CI gating

- By default, the CLI exits non-zero when there is at least one `FAIL`.
- Use `--strict` to also fail on `WARN` and `SKIP` (useful when you want a hard guarantee).
- In GitHub Actions, a non-zero exit code fails the step/job.

## Compatibility / pinning

Rule of thumb: pin `arp-conformance==X.Y.Z` to validate services targeting the ARP spec / SDK release `X.Y.Z`.

```bash
pipx install "arp-conformance==0.2.6"
arp-conformance --version
python -c "import arp_conformance; print(arp_conformance.SPEC_REF)"
```

## Interpreting failures (fast debug loop)

- `401`/`403`: pass auth headers via `--headers` or `--headers-file`.
- Timeouts / polling failures: bump `--timeout`, `--poll-timeout`, and/or `--poll-interval`.
- Schema mismatch: inspect the response body (use `--format json --out ...`) and confirm you pinned the toolkit version you intended (`arp_conformance.SPEC_REF`).
- `WARN`/`SKIP`: decide whether you want `--strict` in your environment.

## Recommended usage

Local development:
- Use `smoke` first to confirm the service is reachable.
- Use `surface` during early implementation to validate routes + response envelopes, even before end-to-end behavior works.
- Use `core` when the service is fully wired and you can safely allow test mutations (`--allow-mutations`).

CI:
- On pull requests: run `smoke` or `surface` against a locally started service container.
- On nightly / integration pipelines: run `core` (and optionally `deep`) with `--allow-mutations`.

## Authentication and headers

If your service requires auth, pass headers:

```bash
arp-conformance check runtime \
  --url https://example.com \
  --tier surface \
  --headers "Authorization=Bearer ..."
```

For CI, prefer a headers file:

```bash
cat > headers.env <<'EOF'
Authorization=Bearer ...
EOF

arp-conformance check runtime --url https://example.com --tier surface --headers-file headers.env
```

## CI recipes (GitHub Actions)

This repo provides a composite action that installs `arp-conformance` from PyPI and runs it:
- `AgentRuntimeProtocol/ARP_Standard/.github/actions/arp-conformance`

By default, when you reference the action as `.../arp-conformance@vX.Y.Z`, it installs `arp-conformance==X.Y.Z`. You can override with `package_version`.

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
      - uses: AgentRuntimeProtocol/ARP_Standard/.github/actions/arp-conformance@v0.2.6
        with:
          service: runtime
          url: http://localhost:8081
          tier: surface
          report_format: json
          report_path: arp-conformance.json
```

### Core gate on nightly (mutations enabled; JUnit output)

```yaml
name: arp-conformance-nightly
on:
  schedule:
    - cron: "0 3 * * *"
jobs:
  core:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Start your service under test (docker compose, process, etc) before running conformance.
      - uses: AgentRuntimeProtocol/ARP_Standard/.github/actions/arp-conformance@v0.2.6
        with:
          service: runtime
          url: http://localhost:8081
          tier: core
          allow_mutations: "true"
          report_format: junit
          report_path: arp-conformance.xml
          upload_artifact: "true"
```

## Tiers (detailed definitions)

All tiers produce per-check results with `PASS`, `FAIL`, `WARN`, or `SKIP`.

- `PASS`: required behavior is present and schema-valid.
- `FAIL`: required behavior is missing or schema-invalid.
- `WARN`: behavior is present but not ideal for conformance (for example: `401/403` without headers, or a workflow could not be completed due to missing prerequisites).
- `SKIP`: a check is not applicable (for example: optional endpoints in `deep` tier when the service does not implement them).

You can treat `WARN` and `SKIP` as failures using `--strict`.

### Tier `smoke`: connectivity + universal endpoints

Purpose: validate the service is reachable and speaking ARP.

Allowed side effects: none (`GET` only).

Checks:
- `GET /v1/health` returns `200` and matches the `Health` schema.
- `GET /v1/version` returns `200` and matches the `VersionInfo` schema.
- `supported_api_versions` contains `v1`.

<details>
<summary>Tier <code>surface</code>: URL + envelope conformance</summary>

Purpose: validate that required **routes exist** and responses are shaped correctly on both success and error paths, without requiring a fully working backend.

Allowed side effects:
- For mutation endpoints (`POST`, `PUT`, `DELETE`), `surface` sends **intentionally invalid** requests or uses clearly non-existent IDs to avoid creating resources.

What “surface conformance” means:
- For each required endpoint, the service must respond in a way that demonstrates the route is implemented:
  - Either a schema-valid success response (when applicable), or
  - A schema-valid `ErrorEnvelope` response (`default` error shape) for failures.

In addition, for mutation endpoints, `surface` includes a **basic request schema enforcement probe**:
- When given an obviously invalid JSON body (missing required fields), the service should return a non-2xx error with an `ErrorEnvelope`.

</details>

<details>
<summary>Tier <code>core</code>: minimal success-path and end-to-end protocol works</summary>

Purpose: prove at least ONE **real**, end-to-end workflow works for the service type, using the smallest spec-valid sequence.

Requires: `--allow-mutations` because this tier creates real runs and/or invocations.

What “minimal success-path” means:
- A shortest sequence of **spec-valid requests** that should succeed on a correctly configured service.
- Request bodies include only required fields (plus a stable `run_id`/`invocation_id` when helpful).
- Every success response body is validated against the normative JSON Schemas.

On the `--allow-mutations` flag and service-specific minimal success-paths:

#### What does `--allow-mutations` do

This is a safety guard: without `--allow-mutations`, `arp-conformance` will not run tiers that perform real state-changing requests like `core` and `deep`.

When enabled:
- Runtime `core` creates a real run via `POST /v1/runs` and polls status/result.
- Tool Registry `core` performs a real tool invocation via `POST /v1/tool-invocations` for a selected tool.
- Daemon `core` may create a runtime profile if none exists, creates an instance, submits a run, polls status/result, and by default deletes anything it created. You can disable cleanup with `--no-cleanup`.

`surface` does **not** require `--allow-mutations`; it may still send intentionally invalid mutation requests to verify that routes exist and that error responses match `ErrorEnvelope`, but it is designed to avoid creating resources.

#### Runtime (`core`)
1. `POST /v1/runs` with a minimal valid `RunRequest` (`input.goal` required).
2. Expect `200` `RunStatus` (schema-valid).
3. Poll `GET /v1/runs/{run_id}` until terminal state or timeout.
4. `GET /v1/runs/{run_id}/result` returns `200` `RunResult` (schema-valid).

Notes:
- `RunResult.ok` may be `true` or `false`; conformance validates the envelope and schema, not “agent quality”.

#### Tool Registry (`core`)
1. `GET /v1/tools` returns `200` and a schema-valid list.
2. Choose a tool:
   - Prefer `--tool-id`/`--tool-name` if provided.
   - Otherwise choose the first tool in the list.
3. `GET /v1/tools/{tool_id}` returns `200` `ToolDefinition`.
4. `POST /v1/tool-invocations` with a schema-valid `ToolInvocationRequest` returns `200` `ToolInvocationResult`.

Notes:
- If there are zero tools and you did not provide `--tool-id`/`--tool-name`, invocation checks are `SKIP` and the run is `WARN` unless `--strict`.
- If the invocation returns `ok=false`, it is schema-valid; it is reported as `WARN` (tool execution may not be configured) unless `--strict`.

#### Daemon (`core`)
1. `GET /v1/admin/runtime-profiles` returns `200` `RuntimeProfileListResponse`.
2. Choose a runtime profile:
   - Use `--runtime-profile` if provided,
   - Else pick the first returned profile,
   - Else create a temporary profile via `PUT /v1/admin/runtime-profiles/{runtime_profile}` (requires `--allow-mutations`).
3. `POST /v1/instances` creates `1` instance for the selected profile.
4. `POST /v1/runs` submits an async run (`202` `RunStatus`).
5. Poll `GET /v1/runs/{run_id}` until terminal.
6. `GET /v1/runs/{run_id}/result` returns `200` `RunResult`.
7. Cleanup (default): delete created instance and temp runtime profile (can disable with `--no-cleanup`).

</details>

<details>
<summary>Tier: <code>deep</code> (optional endpoints + stronger checks)</summary>

Purpose: validate optional endpoints and stronger behavioral guarantees.

Requires: `--allow-mutations` (builds on `core`).

Checks include:
- Runtime optional endpoints (if implemented):
  - `POST /v1/runs/{run_id}:cancel`
  - `GET /v1/runs/{run_id}/events` (`text/event-stream`)
- Daemon optional endpoint (if implemented):
  - `GET /v1/runs/{run_id}/trace`

If an optional endpoint is not implemented (`404`/`405`), it is `SKIP` (or `FAIL` with `--strict`).

</details>

## CLI reference

### Commands

- `arp-conformance check runtime --url <base-url> [flags]`
- `arp-conformance check tool-registry --url <base-url> [flags]`
- `arp-conformance check daemon --url <base-url> [flags]`
- `arp-conformance check all --runtime-url ... --tool-registry-url ... --daemon-url ... [flags]`

### Common flags

- `--tier {smoke,surface,core,deep}`
- `--headers KEY=VALUE` (repeatable)
- `--headers-file <path>` (`KEY=VALUE` per line)
- `--timeout <seconds>` (request timeout)
- `--retries <n>` (transport retries)
- `--poll-timeout <seconds>` and `--poll-interval <seconds>` (run polling)
- `--allow-mutations` (required for `core` and `deep`)
- `--no-cleanup` (don’t delete instances/profiles created by the checker)
- `--strict` (treat `WARN`/`SKIP` as failures)
- `--format {text,json,junit}` and `--out <path>`
- `--spec v1` (default) and `--spec-path <dir>` (use a local spec checkout; accepts either a repo root containing `spec/v1/` or a `spec/` directory containing `v1/`)

### Tool Registry flags

- `--tool-id <id>` / `--tool-name <name>`: select which tool to invoke for `core`/`deep`.

### Daemon flags

- `--runtime-profile <name>`: choose which runtime profile to use (or to create if missing).

## Library API (minimal)

```python
from arp_conformance.api import run

report = run(
    service="runtime",
    base_url="http://localhost:8081",
    tier="smoke",
)
print(report.ok)
print(report.to_json())
```

## Spec reference

`arp_conformance.SPEC_REF` exposes the spec tag used by the package (for example, `spec/v1@v0.2.6`).

The embedded spec snapshot lives under `arp_conformance/_spec/` inside the wheel.

## Development (maintainers)

When the spec changes, sync the embedded snapshot:

```bash
python3 tools/conformance/sync_spec.py --version v1
```

Then rebuild the package.

## Exit codes

- `0`: no `FAIL` results (and no `WARN`/`SKIP` when `--strict` is set)
- `1`: at least one `FAIL` (or `WARN`/`SKIP` with `--strict`)
- `2`: invalid CLI usage (bad arguments)
