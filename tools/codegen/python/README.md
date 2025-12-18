# Python Codegen

Run commands from the repository root.

The canonical source of truth is [`spec/v1/`](../../../spec/v1/README.md). Python SDK artifacts live under [`sdks/python/`](../../../sdks/python/README.md).

This repo uses `openapi-python-client` to generate the Python SDK clients and models from the OpenAPI files under `spec/<version>/openapi/`.
After low-level generation, the pipeline also generates a small facade layer (`sdk.py`) per service and rewrites each service package’s `__init__.py` to export the curated facade surface.

## Generate

```bash
python3 -m pip install -r tools/codegen/python/requirements.txt
python3 tools/codegen/python/generate.py
```

Outputs are written under:
- `sdks/python/src/arp_sdk/tool_registry/`
- `sdks/python/src/arp_sdk/runtime/`
- `sdks/python/src/arp_sdk/daemon/`

These generated directories are intentionally not committed to git (see `.gitignore`).

## Build + validate locally

```bash
python3 -m pip install -r tools/codegen/python/requirements-dev.txt
python3 tools/codegen/python/build_local.py --clean
```

## Notes

- The generator bundles local `$ref` JSON Schemas into a single OpenAPI document per service for codegen purposes.
- CI and release workflows generate the SDK before building/publishing.
