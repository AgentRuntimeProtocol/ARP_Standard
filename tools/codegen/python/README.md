# Python Codegen

The canonical source of truth is `spec/`. Python SDK artifacts live under `sdks/python/`.

This repo uses `openapi-python-client` to generate the Python SDK clients and models from the OpenAPI files under `spec/<version>/openapi/`.

## Generate

```bash
python -m pip install -r tools/codegen/python/requirements.txt
python tools/codegen/python/generate.py --version v1alpha2
```

Outputs are written under:
- `sdks/python/src/arp_sdk/tool_registry/`
- `sdks/python/src/arp_sdk/runtime/`
- `sdks/python/src/arp_sdk/daemon/`

These generated directories are intentionally not committed to git (see `.gitignore`).

## Build + validate locally

```bash
python -m pip install -r tools/codegen/python/requirements-dev.txt
python tools/codegen/python/build_local.py --version v1alpha2 --clean
```

## Notes

- The generator bundles local `$ref` JSON Schemas into a single OpenAPI document per service for codegen purposes.
- CI and release workflows generate the SDK before building/publishing.
