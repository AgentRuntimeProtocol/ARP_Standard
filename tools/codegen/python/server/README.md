# Python Server Codegen

Run commands from the repository root.

This generator produces the FastAPI server scaffolding under `kits/python/` using the OpenAPI specs in `spec/<version>/openapi/`.

## Generate

```bash
python3 -m pip install -r tools/codegen/python/server/requirements.txt
python3 tools/codegen/python/server/generate.py --version v1
```

Outputs are written under:
- `kits/python/src/arp_standard_server/run_gateway/`
- `kits/python/src/arp_standard_server/run_coordinator/`
- `kits/python/src/arp_standard_server/atomic_executor/`
- `kits/python/src/arp_standard_server/composite_executor/`
- `kits/python/src/arp_standard_server/node_registry/`
- `kits/python/src/arp_standard_server/selection/`
- `kits/python/src/arp_standard_server/pdp/`
