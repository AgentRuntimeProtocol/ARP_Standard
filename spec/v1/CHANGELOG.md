# Changelog — `v1`

## 0.2.4

- Add JWT Bearer authentication (`ArpBearerJWT`) to all service OpenAPI contracts and make endpoints secure-by-default (with `/v1/health` and `/v1/version` as explicit unauthenticated carve-outs).
- Standardize `401`/`403` responses for protected endpoints (`ErrorEnvelope`, plus `WWW-Authenticate` on `401`).

## 0.2.2

- Canonicalize titled schemas during codegen bundling to avoid duplicate model names; no contract changes.
- Promote inline enums (run/instance state, health status, run event type, tool source, trace level) to named schemas to avoid numbered enum classes.

## 0.2.1

- Python model codegen now emits explicit `default=None` for optional fields to satisfy type checkers; no contract changes.

## 0.2.0

- Version bump for generated artifacts and packaging updates; no contract changes.

## 0.1.0

- Initial stable release of `v1` (versioned paths under `/v1/...`).
