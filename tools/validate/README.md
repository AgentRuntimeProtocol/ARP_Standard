# Validate

Validate conformance vectors (and optionally examples) against the JSON Schemas.

## Install

```bash
python -m pip install -r tools/validate/requirements.txt
```

## Validate conformance vectors

```bash
python tools/validate/validate_json_vectors.py
```

## Validate conformance vectors + examples

```bash
python tools/validate/validate_json_vectors.py --include-examples
```

