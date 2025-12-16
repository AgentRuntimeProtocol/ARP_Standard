# ARP Standard — `v1beta1`

`v1beta1` is a pre-stable version: breaking changes should be avoided and require clear migration guidance.

## Contents

- `schemas/` — JSON Schemas for all payloads
- `openapi/` — service contracts (OpenAPI)
- `examples/` — illustrative example payloads
- `conformance/` — golden vectors + rules for implementers

## Required endpoints (all services)

- `GET /v1beta1/health`
- `GET /v1beta1/version`
