# Validate

Validate conformance vectors (and optionally examples) against the JSON Schemas.
Also validate the OpenAPI specs for unsupported features and broken references.

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

## Validate OpenAPI specs

```bash
python3 tools/validate/validate_openapi.py --version v1
```

## Validate generated artifacts are not checked in

```bash
python3 tools/validate/validate_generated_artifacts.py
```
