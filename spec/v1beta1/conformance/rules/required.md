# Required vs optional (v1beta1)

All services MUST implement:
- `GET /v1beta1/health`
- `GET /v1beta1/version`

Tool Registry MUST implement:
- `GET /v1beta1/tools`
- `GET /v1beta1/tools/{tool_id}`
- `POST /v1beta1/tool-invocations`

Runtime MUST implement:
- `POST /v1beta1/runs`
- `GET /v1beta1/runs/{run_id}`
- `GET /v1beta1/runs/{run_id}/result`

Daemon MUST implement:
- `GET /v1beta1/instances`
- `POST /v1beta1/instances`
- `DELETE /v1beta1/instances/{instance_id}`
- `POST /v1beta1/instances:register`
- `GET /v1beta1/admin/runtime-profiles`
- `PUT /v1beta1/admin/runtime-profiles/{runtime_profile}`
- `DELETE /v1beta1/admin/runtime-profiles/{runtime_profile}`
- `GET /v1beta1/runs`
- `POST /v1beta1/runs`
- `GET /v1beta1/runs/{run_id}`
- `GET /v1beta1/runs/{run_id}/result`

Optional (v1beta1):
- `POST /v1beta1/runs/{run_id}:cancel` (runtime)
- `GET /v1beta1/runs/{run_id}/events` (runtime)
- `GET /v1beta1/runs/{run_id}/trace` (daemon)
