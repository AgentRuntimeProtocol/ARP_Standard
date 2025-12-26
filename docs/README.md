# ARP Standard Docs

Short, practical docs for working with the ARP Standard and its Python client, models, and server bases.

## Start here

- Spec (normative): [`spec/v1/`](../spec/v1/README.md)
- Spec layout + conventions: [`docs/spec.md`](spec.md)
- Security profiles (auth configuration): [`docs/security-profiles.md`](security-profiles.md)
- Service overview (what talks to what): [`docs/services.md`](services.md)
- Conformance vectors + validation: [`docs/conformance.md`](conformance.md)
- Endpoint conformance checker (`arp-conformance`): [`conformance/python/`](../conformance/python/README.md)
- Python client + models (`arp-standard-client` / `arp-standard-model`): [`docs/python-client.md`](python-client.md)
- Python server bases (`arp-standard-server`): [`docs/python-server.md`](python-server.md)

## Quick commands

Run these from the repository root.

Validate JSON vectors (requires `jsonschema`):

```bash
python3 -m pip install -r tools/validate/requirements.txt
python3 tools/validate/validate_json_vectors.py --include-examples
```

Validate OpenAPI specs (requires `ruamel.yaml`):

```bash
python3 -m pip install -r tools/validate/requirements.txt
python3 tools/validate/validate_openapi.py --version v1
```

Generate the Python client + models + server locally (requires codegen deps):

```bash
python3 -m pip install -r tools/codegen/python/model/requirements.txt
python3 -m pip install -r tools/codegen/python/client/requirements.txt
python3 -m pip install -r tools/codegen/python/server/requirements.txt
python3 tools/codegen/python/model/generate.py
python3 tools/codegen/python/client/generate.py
python3 tools/codegen/python/server/generate.py
```
