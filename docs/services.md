# Services

ARP defines node-centric HTTP services. Each service must implement `GET /v1/health` and `GET /v1/version`.

## Run Gateway

Purpose: client-facing run API.

Required endpoints:

- `POST /v1/runs`
- `GET /v1/runs/{run_id}`
- `POST /v1/runs/{run_id}:cancel`

Optional endpoints:

- `GET /v1/runs/{run_id}/events`

## Run Coordinator

Purpose: run authority for NodeRun lifecycle, graph patches, evaluation, and completion.

Required endpoints:

- `POST /v1/node-runs`
- `GET /v1/node-runs/{node_run_id}`
- `POST /v1/graph-patches`
- `POST /v1/node-runs/{node_run_id}:evaluation`
- `POST /v1/node-runs/{node_run_id}:complete`

## Atomic Executor

Purpose: execute atomic NodeRuns.

Required endpoints:

- `POST /v1/atomic-node-runs:execute`

## Composite Executor

Purpose: begin composite NodeRun assignments.

Required endpoints:

- `POST /v1/composite-node-runs:begin`

## Node Registry

Purpose: publish and retrieve NodeType definitions.

Required endpoints:

- `GET /v1/node-types`
- `POST /v1/node-types`
- `GET /v1/node-types/{node_type_id}`

## Selection

Purpose: generate bounded candidate sets for subtasks.

Required endpoints:

- `POST /v1/candidate-sets`

## PDP (optional component)

Purpose: standard policy decision API if a PDP is deployed.

Required endpoints (when implemented):

- `POST /v1/policy:decide`

## See also

- Spec overview: [`docs/spec.md`](spec.md)
- Conformance: [`docs/conformance.md`](conformance.md)
