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

## Migration notes (Unreleased)

- `InstanceCreateRequest.profile` -> `InstanceCreateRequest.runtime_profile`
- `InstanceCreateRequest.env/args` -> `InstanceCreateRequest.overrides.env/args`
- `InstanceCreateRequest.overrides.tool_registry_url` (new)
- `RuntimeInstance.runtime_api_base_url` -> `RuntimeInstance.runtime_api_endpoint`
- `RuntimeInstance.runtime_type` -> `RuntimeInstance.runtime_name`
- `RunRequest.runtime_selector.profile` -> `RunRequest.runtime_selector.runtime_profile`
- `RunRequest.runtime_selector.runtime_type` -> `RunRequest.runtime_selector.runtime_name`
- `RunRequest.runtime_selector.address` -> `RunRequest.runtime_selector.runtime_api_endpoint`
