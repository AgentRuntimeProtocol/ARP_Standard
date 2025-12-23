# Required vs optional (v1)

All services MUST implement:
- `GET /v1/health`
- `GET /v1/version`

Tool Registry MUST implement:
- `GET /v1/tools`
- `GET /v1/tools/{tool_id}`
- `POST /v1/tool-invocations`

Runtime MUST implement:
- `POST /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/result`

Daemon MUST implement:
- `GET /v1/instances`
- `POST /v1/instances`
- `DELETE /v1/instances/{instance_id}`
- `POST /v1/instances:register`
- `GET /v1/admin/runtime-profiles`
- `PUT /v1/admin/runtime-profiles/{runtime_profile}`
- `DELETE /v1/admin/runtime-profiles/{runtime_profile}`
- `GET /v1/runs`
- `POST /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/result`

Optional (v1):
- `POST /v1/runs/{run_id}:cancel` (runtime)
- `GET /v1/runs/{run_id}/events` (runtime)
- `GET /v1/runs/{run_id}/trace` (daemon)
