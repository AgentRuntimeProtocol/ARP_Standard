# ARP Standard — `v1`

Stable, versioned HTTP+JSON contracts for ARP services.

## Contents

- [`schemas/`](schemas/) — JSON Schemas for all payloads
- [`openapi/`](openapi/) — service contracts (OpenAPI)
- [`examples/`](examples/) — illustrative example payloads
- [`conformance/`](conformance/) — golden vectors + rules for implementers

## Required endpoints (all services)

- `GET /v1/health`
- `GET /v1/version`

All endpoints in this spec are versioned under the `/v1` path prefix.

## See also

- Docs index: [`docs/README.md`](../../docs/README.md)
