# ARP Standard

Canonical, language-agnostic API and schema contracts for Agent Runtime Protocol (ARP) components.

This repository is the source of truth for:
- Versioned HTTP+JSON interfaces (OpenAPI) for cross-component communication.
- JSON Schemas for request/response payloads and trace/event formats.
- Conformance vectors (golden JSON) for implementers.

## Layout

- `spec/` — the normative standard (schemas, OpenAPI, examples, conformance)
- `tools/` — validation, bundling, and codegen helpers
- `sdks/` — generated SDK artifacts (language-specific)
- `docs/` — standard documentation for contributors/implementers

## Versioning

ARP uses Kubernetes-style pre-stable API versions:
- `v1alpha1` (breaking changes allowed)
- `v1beta1` (mostly stable)
- `v1` (stable)

## Extension mechanism

Top-level objects MAY include:

```json
{ "extensions": { "org.example.key": { "any": "json" } } }
```

Keys must include a namespace prefix to avoid collisions (`<reverse_dns_or_org>.<key>`).

