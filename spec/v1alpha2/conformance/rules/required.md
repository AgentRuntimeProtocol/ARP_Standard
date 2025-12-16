# Required vs optional (v1alpha2)

All services MUST implement:
- `GET /v1alpha2/health`
- `GET /v1alpha2/version`

Tool Registry MUST implement:
- `GET /v1alpha2/tools`
- `GET /v1alpha2/tools/{tool_id}`
- `POST /v1alpha2/tool-invocations`

Runtime MUST implement:
- `POST /v1alpha2/runs`
- `GET /v1alpha2/runs/{run_id}`
- `GET /v1alpha2/runs/{run_id}/result`

Daemon MUST implement:
- `GET /v1alpha2/instances`
- `POST /v1alpha2/instances`
- `DELETE /v1alpha2/instances/{instance_id}`
- `POST /v1alpha2/runs`
- `GET /v1alpha2/runs/{run_id}`
- `GET /v1alpha2/runs/{run_id}/result`

Optional (v1alpha2):
- `POST /v1alpha2/runs/{run_id}:cancel` (runtime)
- `GET /v1alpha2/runs/{run_id}/events` (runtime)
- `GET /v1alpha2/runs/{run_id}/trace` (daemon)
