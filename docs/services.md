# Services

ARP defines three primary HTTP services. Each must implement `GET /v1/health` and `GET /v1/version`.

## Tool Registry

Purpose: tool discovery + invocation.

Required endpoints:

- `GET /v1/tools`
- `GET /v1/tools/{tool_id}`
- `POST /v1/tool-invocations`

## Runtime

Purpose: execute runs.

Required endpoints:

- `POST /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/result`

Optional endpoints (not required for conformance):

- `POST /v1/runs/{run_id}:cancel`
- `GET /v1/runs/{run_id}/events`

## Daemon

Purpose: manage runtime instances and route runs to them.

Required endpoints:

- Instances: `GET /v1/instances`, `POST /v1/instances`, `DELETE /v1/instances/{instance_id}`
- External instances: `POST /v1/instances:register`
- Runtime profiles (safe list): `GET /v1/admin/runtime-profiles`, `PUT /v1/admin/runtime-profiles/{runtime_profile}`, `DELETE /v1/admin/runtime-profiles/{runtime_profile}`
- Runs: `GET /v1/runs`, `POST /v1/runs`, `GET /v1/runs/{run_id}`, `GET /v1/runs/{run_id}/result`

Optional endpoint (not required for conformance):

- `GET /v1/runs/{run_id}/trace`

## See also

- Spec overview: [`docs/spec.md`](spec.md)
- Conformance: [`docs/conformance.md`](conformance.md)
