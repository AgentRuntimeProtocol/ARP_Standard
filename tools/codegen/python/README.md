# Python Codegen

Run commands from the repository root.
Generators live under `tools/codegen/python/{model,client,server}`; this directory hosts shared helpers.

The canonical source of truth is [`spec/v1/`](../../../spec/v1/README.md). Python artifacts live under [`models/python/`](../../../models/python/README.md), [`clients/python/`](../../../clients/python/README.md), and [`kits/python/`](../../../kits/python/README.md).

This repo uses `datamodel-code-generator` to generate Pydantic models from the OpenAPI files under `spec/<version>/openapi/`.
It also uses `openapi-python-client` to generate the Python client scaffolding, then patches the generated client to consume `arp-standard-model`.
After low-level generation, the pipeline generates a small facade layer (`facade.py`) per service and rewrites each service package’s `__init__.py` to export the curated facade surface.
Request and params models (service-prefixed) are generated into `arp-standard-model` for facade inputs.

## Validation + reports

- OpenAPI validation runs before codegen to catch broken `$ref`s or unsupported features.
- CI uploads a codegen report and the generated source tarball as build artifacts for review.
  - Generate locally: `python3 tools/codegen/python/report_codegen.py --version v1`

## Generate

```bash
python3 -m pip install -r tools/codegen/python/model/requirements.txt
python3 -m pip install -r tools/codegen/python/client/requirements.txt
python3 -m pip install -r tools/codegen/python/server/requirements.txt
python3 tools/codegen/python/model/generate.py
python3 tools/codegen/python/client/generate.py
python3 tools/codegen/python/server/generate.py
```

Outputs are written under:
- `models/python/src/arp_standard_model/_generated.py`
- `models/python/src/arp_standard_model/_requests.py`
- `clients/python/src/arp_standard_client/tool_registry/`
- `clients/python/src/arp_standard_client/runtime/`
- `clients/python/src/arp_standard_client/daemon/`
- `kits/python/src/arp_standard_server/tool_registry/`
- `kits/python/src/arp_standard_server/runtime/`
- `kits/python/src/arp_standard_server/daemon/`

These generated directories are intentionally not committed to git (see `.gitignore`).

## Build + validate locally

```bash
python3 -m pip install -r tools/codegen/python/model/requirements.txt
python3 -m pip install -r tools/codegen/python/client/requirements-dev.txt
python3 -m pip install -r tools/codegen/python/server/requirements.txt
python3 -m pip install -r tools/validate/requirements.txt
python3 tools/codegen/python/build_local.py --clean
```

## Notes

- The generator bundles local `$ref` JSON Schemas into a single OpenAPI document per service for codegen purposes.
- CI and release workflows generate the models + client + server before building/publishing.
- Pydantic patching is automated (`tools/codegen/python/client/patch_client_to_pydantic.py`). Do not edit generated code directly; extend the patcher or the generator instead.
