# Spec overview

The normative contract lives under [`spec/v1/`](../spec/v1/README.md).

## Layout

- [`spec/v1/openapi/`](../spec/v1/openapi/) — HTTP interfaces (OpenAPI)
- [`spec/v1/schemas/`](../spec/v1/schemas/) — payload schemas (JSON Schema)
- [`spec/v1/examples/`](../spec/v1/examples/) — example payloads
- [`spec/v1/conformance/`](../spec/v1/conformance/) — golden vectors + endpoint requirements

## Conventions

- **Versioned paths:** all HTTP endpoints are rooted at `/v1/...`.
- **Errors:** non-2xx responses should return an `ErrorEnvelope`.
- **Extensions:** many payloads include an `extensions` map for vendor-specific fields.
- **Endpoints:** endpoint fields use URI strings (for example `http://127.0.0.1:43120`).

## See also

- Services: [`docs/services.md`](services.md)
- Conformance: [`docs/conformance.md`](conformance.md)
- Python SDK: [`docs/python-sdk.md`](python-sdk.md)
