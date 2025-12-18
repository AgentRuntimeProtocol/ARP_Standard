# Tools

Helper scripts for validating and bundling the ARP standard.

Run commands from the repository root.

Quick starts:
- JSON parse lint: `python3` [`tools/lint/lint_json.py`](lint/lint_json.py)
- JSON Schema validation (requires deps): `python3` [`tools/validate/validate_json_vectors.py`](validate/validate_json_vectors.py) `--include-examples`
- Python SDK codegen (requires deps): `python3` [`tools/codegen/python/generate.py`](codegen/python/generate.py)
- Python SDK build (requires deps): `python3` [`tools/codegen/python/build_local.py`](codegen/python/build_local.py) `--clean`

See:

- Validation: [`tools/validate/`](validate/)
- Codegen: [`tools/codegen/python/`](codegen/python/)
