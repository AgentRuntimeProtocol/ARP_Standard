# ARP Standard — `v1` (Node-Centric, Draft)

Stable, versioned HTTP+JSON contracts for ARP/EP vNext.

`v1` defines the node-centric component boundaries described in `Business_Docs/ARP_HLD.md`.

Draft release tag: `v0.3.1` (see `CHANGELOG.md`).

## Contents

- `schemas/` — JSON Schemas for all payloads (shared models + request/response bodies)
- `openapi/` — service contracts (OpenAPI)
- `examples/` — illustrative example payloads
- `conformance/` — golden vectors + rules for implementers

## Required endpoints (all services)

- `GET /v1/health`
- `GET /v1/version`

## Service contracts (OpenAPI)

- Run Gateway: `openapi/run-gateway.openapi.yaml`
- Run Coordinator: `openapi/run-coordinator.openapi.yaml`
- Atomic Executor: `openapi/atomic-executor.openapi.yaml`
- Composite Executor: `openapi/composite-executor.openapi.yaml`
- Node Registry: `openapi/node-registry.openapi.yaml`
- Selection: `openapi/selection.openapi.yaml`
- Policy Decision Point (optional): `openapi/pdp.openapi.yaml`

## Transport and deployment

The canonical API surface is HTTP+JSON. Implementations may run the same contracts:
- on-wire,
- on `localhost`, or
- in-process (direct calls / embedded services),
as long as they preserve the same request/response semantics (including auth context propagation and error envelopes).
