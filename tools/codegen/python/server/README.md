# Python Server Codegen

Run commands from the repository root.

This generator produces the FastAPI server scaffolding under `kits/python/` using the OpenAPI specs in `spec/<version>/openapi/`.

## Generate

```bash
python3 -m pip install -r tools/codegen/python/server/requirements.txt
python3 tools/codegen/python/server/generate.py --version v1
```

Outputs are written under:
- `kits/python/src/arp_standard_server/daemon/`
- `kits/python/src/arp_standard_server/runtime/`
- `kits/python/src/arp_standard_server/tool_registry/`
