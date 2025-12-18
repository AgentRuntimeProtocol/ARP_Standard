# ARP Standard Docs

Short, practical docs for working with the ARP Standard and its Python SDK.

## Start here

- Spec (normative): [`spec/v1/`](../spec/v1/README.md)
- Spec layout + conventions: [`docs/spec.md`](spec.md)
- Service overview (what talks to what): [`docs/services.md`](services.md)
- Conformance vectors + validation: [`docs/conformance.md`](conformance.md)
- Python SDK (`arp-standard-py` / `arp_sdk`): [`docs/python-sdk.md`](python-sdk.md)

## Quick commands

Run these from the repository root.

Validate JSON vectors (requires `jsonschema`):

```bash
python3 -m pip install -r tools/validate/requirements.txt
python3 tools/validate/validate_json_vectors.py --include-examples
```

Generate the Python SDK locally (requires codegen deps):

```bash
python3 -m pip install -r tools/codegen/python/requirements.txt
python3 tools/codegen/python/generate.py
```
