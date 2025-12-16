# Bundle (OpenAPI)

OpenAPI files under `spec/<version>/openapi/` reference shared JSON Schemas via `$ref`.

Many generators work best with a single self-contained OpenAPI document per service, so bundling typically:
- resolves external `$ref`s into a single file
- optionally rewrites internal `$ref`s for deterministic codegen

Recommended approaches:
- `@redocly/cli` (`redocly bundle ...`)
- `swagger-cli` (`swagger-cli bundle ...`)

This repo intentionally keeps `spec/` free of generated/bundled artifacts. Bundle outputs should go under `dist/` (gitignored).

