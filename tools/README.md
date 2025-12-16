# Tools

Helper scripts for validating and bundling the ARP standard.

Quick starts:
- JSON parse lint: `python tools/lint/lint_json.py`
- JSON Schema validation (requires deps): `python tools/validate/validate_json_vectors.py --include-examples`
- Python SDK codegen (requires deps): `python tools/codegen/python/generate.py --version v1beta1`
- Python SDK build (requires deps): `python tools/codegen/python/build_local.py --version v1beta1 --clean`

See `tools/validate/` for JSON vector validation and `tools/bundle/` for OpenAPI bundling.
