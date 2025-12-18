# Python SDK (`arp-standard-py`)

- PyPI distribution: `arp-standard-py`
- Import package: `arp_sdk`
- Package README: [`sdks/python/README.md`](../sdks/python/README.md)

## Install

```bash
python3 -m pip install arp-standard-py
```

## Basic usage

```python
from arp_sdk.daemon import DaemonClient
from arp_sdk.models import InstanceCreateRequest

client = DaemonClient(base_url="http://127.0.0.1:8082")
created = client.create_instances(InstanceCreateRequest(runtime_profile="default", count=1))
print(created.to_dict())
```

## Generate locally (developers)

Run these from the repository root.

```bash
python3 -m pip install -r tools/codegen/python/requirements.txt
python3 tools/codegen/python/generate.py
```

## Release (PyPI)

1. Update versions to match:
   - [`sdks/python/pyproject.toml`](../sdks/python/pyproject.toml)
   - [`sdks/python/src/arp_sdk/__init__.py`](../sdks/python/src/arp_sdk/__init__.py)
2. Tag the release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## See also

- Package README: [`sdks/python/README.md`](../sdks/python/README.md)
