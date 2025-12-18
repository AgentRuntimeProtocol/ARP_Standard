# Contributing

## What belongs here

- Versioned contracts under [`spec/`](spec/) (current: [`spec/v1/`](spec/v1/README.md))
- Examples: [`spec/v1/examples/`](spec/v1/examples/)
- Conformance vectors: [`spec/v1/conformance/`](spec/v1/conformance/)
- Tooling under [`tools/`](tools/) that helps validate/codegen the standard

## Process (high-level)

1. Make changes under [`spec/v1/`](spec/v1/README.md).
2. Update [`spec/v1/CHANGELOG.md`](spec/v1/CHANGELOG.md).
3. Add or update examples and conformance vectors.
4. Run validation tooling (see [`tools/README.md`](tools/README.md)).

## Style conventions

- JSON fields use `snake_case`.
- Prefer strict schemas (`additionalProperties: false`) and use `extensions` for passthrough data.
- Keep schemas small and composable; prefer `$ref` over duplication.
