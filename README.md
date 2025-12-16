# ARP Standard

Canonical, language-agnostic API and schema contracts for Agent Runtime Protocol (ARP) components.

This repository is the source of truth for:
- Versioned HTTP+JSON interfaces (OpenAPI) for cross-component communication.
- JSON Schemas for request/response payloads and trace/event formats.
- Conformance vectors (golden JSON) for implementers.

## Layout

- `spec/` — the normative standard (schemas, OpenAPI, examples, conformance)
- `tools/` — validation, bundling, and codegen helpers
- `sdks/` — SDK package scaffolds (generated at build time)
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

## Publishing (PyPI)

The Python SDK is published as `arp-standard-py` from `sdks/python/` via GitHub Actions (OIDC / Trusted Publishing).

1. Update versions to match:
   - `sdks/python/pyproject.toml`
   - `sdks/python/src/arp_sdk/__init__.py`
2. Push a tag to trigger the publish workflow:

```bash
git tag arp-standard-py-v<version>
git push origin arp-standard-py-v<version>
```

Notes:
- The workflow generates the SDK from `spec/` at build time using `tools/codegen/python/generate.py`.
- Wheels/sdists are uploaded as GitHub Actions run artifacts and attached to the GitHub Release for the tag.
