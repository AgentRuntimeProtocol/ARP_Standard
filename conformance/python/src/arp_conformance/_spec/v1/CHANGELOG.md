# Changelog — `v1`

## v0.3.7 (draft)

- Python SDKs: serialize request bodies with `model_dump(mode="json", exclude_none=True)` to support `AnyUrl` fields.

## v0.3.5 (draft)

- Removed task graph / graph patch surface (`TaskGraph`, `GraphPatch`, `POST /v1/graph-patches`).
- Added Run lifecycle endpoints to Run Coordinator (`POST/GET /v1/runs`, `POST /v1/runs/{run_id}:cancel`).
- Added optional event streams on Run Coordinator (`GET /v1/runs/{run_id}/events`, `GET /v1/node-runs/{node_run_id}/events`).
- Extended NodeRun completion to include terminal `state` and optional `error`.
- Added optional cancel endpoints to Atomic/Composite Executors.
- Added `candidate_set_id` to `CandidateSet`.

## v0.3.0 (draft)

- Initial node-centric draft spec (Run Gateway, Run Coordinator, Composite/Atomic Executors, Node Registry, Selection, optional PDP).
