# Conformance

Conformance is defined by:

- JSON Schema validation for golden vectors under [`spec/v1/conformance/json_vectors/`](../spec/v1/conformance/json_vectors/)
- Required endpoints listed in [`spec/v1/conformance/rules/required.md`](../spec/v1/conformance/rules/required.md)

## Validate locally

Run these from the repository root.

Install validator deps:

```bash
python3 -m pip install -r tools/validate/requirements.txt
```

Run validation:

```bash
python3 tools/validate/validate_json_vectors.py --include-examples
```

Success means every JSON file in:

- [`spec/v1/conformance/json_vectors/`](../spec/v1/conformance/json_vectors/)
- [`spec/v1/examples/`](../spec/v1/examples/) (when `--include-examples` is set)

validates against its matching schema in [`spec/v1/schemas/`](../spec/v1/schemas/).

## See also

- Spec overview: [`docs/spec.md`](spec.md)
- Services: [`docs/services.md`](services.md)
