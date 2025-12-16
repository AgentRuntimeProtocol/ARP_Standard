# ARP Standard Python SDK

Python client and model layer aligned with `spec/v1alpha1`.

## Install (editable)

```bash
python -m pip install -e sdks/python
```

## Usage

```python
from arp_sdk.clients import ToolRegistryClient

client = ToolRegistryClient(base_url="http://localhost:8081")
tools = client.list_tools()
```

## Release (PyPI)

The GitHub Actions workflow `release` publishes this package when you push a tag matching:

- `arp-standard-py-v<version>` (example: `arp-standard-py-v1.0.0a1`)

The workflow verifies the tag matches `sdks/python/pyproject.toml` and `arp_sdk.__version__`, then builds and publishes using PyPI Trusted Publishing (OIDC).
