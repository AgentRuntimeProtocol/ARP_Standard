# Contributing

## What belongs here

- Versioned, language-agnostic contracts under `spec/`
- Examples and conformance vectors that validate against the schemas
- Tooling under `tools/` that helps validate/bundle/codegen the standard

## Process (high-level)

1. Make changes under `spec/<version>/`.
2. Update `spec/<version>/CHANGELOG.md`.
3. Add or update examples and conformance vectors.
4. Run validation tooling (see `tools/README.md`).

## Style conventions

- JSON fields use `snake_case`.
- Prefer strict schemas (`additionalProperties: false`) and use `extensions` for passthrough data.
- Keep schemas small and composable; prefer `$ref` over duplication.

