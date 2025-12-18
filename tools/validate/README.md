# Validate

Validate conformance vectors (and optionally examples) against the JSON Schemas.

Run commands from the repository root.

## Install

```bash
python3 -m pip install -r tools/validate/requirements.txt
```

## Validate conformance vectors

```bash
python3 tools/validate/validate_json_vectors.py
```

## Validate conformance vectors + examples

```bash
python3 tools/validate/validate_json_vectors.py --include-examples
```
