# Changelog — `v1beta1`

## Unreleased

- Promoted `v1alpha2` to `v1beta1` (versioned paths updated).
- Added daemon run listing (`GET /v1beta1/runs`) and `RunListResponse`.
- Added daemon admin API for runtime profile safe list (`/v1beta1/admin/runtime-profiles`).
- Added daemon endpoint registration for external runtime instances (`POST /v1beta1/instances:register`).
- Introduced transport-agnostic endpoint locators (`EndpointLocator`) and renamed runtime instance endpoint field to `runtime_api_endpoint`.
- Breaking: renamed `profile` -> `runtime_profile`, `runtime_type` -> `runtime_name`, and moved instance env/args under `overrides`.
