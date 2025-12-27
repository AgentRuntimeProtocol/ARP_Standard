# Required vs optional (v1)

All services MUST implement:
- `GET /v1/health`
- `GET /v1/version`

Run Gateway MUST implement:
- `POST /v1/runs`
- `GET /v1/runs/{run_id}`
- `POST /v1/runs/{run_id}:cancel`

Optional:
- `GET /v1/runs/{run_id}/events`
- `GET /v1/node-runs/{node_run_id}/events`
- `POST /v1/atomic-node-runs/{node_run_id}:cancel`
- `POST /v1/composite-node-runs/{node_run_id}:cancel`

Run Coordinator MUST implement:
- `POST /v1/runs`
- `GET /v1/runs/{run_id}`
- `POST /v1/runs/{run_id}:cancel`
- `POST /v1/node-runs`
- `GET /v1/node-runs/{node_run_id}`
- `POST /v1/node-runs/{node_run_id}:evaluation`
- `POST /v1/node-runs/{node_run_id}:complete`

Composite Executor MUST implement:
- `POST /v1/composite-node-runs:begin`

Atomic Executor MUST implement:
- `POST /v1/atomic-node-runs:execute`

Node Registry MUST implement:
- `GET /v1/node-types`
- `POST /v1/node-types`
- `GET /v1/node-types/{node_type_id}`

Selection MUST implement:
- `POST /v1/candidate-sets`

PDP MUST implement:
- `POST /v1/policy:decide`
