# Conformance

Conformance is defined by:

- JSON Schema validation for golden vectors under [`spec/v1/conformance/json_vectors/`](../spec/v1/conformance/json_vectors/)
- Required endpoints listed in [`spec/v1/conformance/rules/required.md`](../spec/v1/conformance/rules/required.md)

In addition, ARP ships an official endpoint-level conformance checker:
- [`arp-conformance`](../conformance/python/README.md): validates **running** services against the ARP Standard schemas.

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

## Validate running services (endpoints)

Install:

```bash
python3 -m pip install arp-conformance
```

Examples:

```bash
arp-conformance check run-gateway --url http://localhost:8080 --tier smoke
arp-conformance check node-registry --url http://localhost:8081 --tier surface
arp-conformance check run-coordinator --url http://localhost:8082 --tier surface
```

Tier definitions and current limitations (core/deep are placeholders for node-centric v1) live in the `arp-conformance` README:
- [`conformance/python/README.md`](../conformance/python/README.md)

## See also

- Spec overview: [`docs/spec.md`](spec.md)
- Services: [`docs/services.md`](services.md)
