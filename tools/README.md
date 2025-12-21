# Tools

Helper scripts for validating and bundling the ARP standard.

Run commands from the repository root.

Quick starts:
- JSON parse lint: `python3` [`tools/lint/lint_json.py`](lint/lint_json.py)
- JSON Schema validation (requires deps): `python3` [`tools/validate/validate_json_vectors.py`](validate/validate_json_vectors.py) `--include-examples`
- OpenAPI validation (requires deps): `python3` [`tools/validate/validate_openapi.py`](validate/validate_openapi.py) `--version v1`
- Python model codegen (requires deps): `python3` [`tools/codegen/python/model/generate.py`](codegen/python/model/generate.py)
- Python client codegen (requires deps): `python3` [`tools/codegen/python/client/generate.py`](codegen/python/client/generate.py)
- Python server codegen (requires deps): `python3` [`tools/codegen/python/server/generate.py`](codegen/python/server/generate.py)
- Python packages build (requires deps): `python3` [`tools/codegen/python/build_local.py`](codegen/python/build_local.py) `--clean`

See:

- Validation: [`tools/validate/`](validate/)
- Codegen (models): [`tools/codegen/python/model/`](codegen/python/model/)
- Codegen (client): [`tools/codegen/python/client/`](codegen/python/client/)
- Codegen (server): [`tools/codegen/python/server/`](codegen/python/server/)
