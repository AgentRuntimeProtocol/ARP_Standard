# ARP Standard Python SDK

Python client and model layer aligned with `spec/v1beta1`.

- PyPI distribution: `arp-standard-py`
- Import package: `arp_sdk`

## Install from source (editable)

```bash
python -m pip install -r tools/codegen/python/requirements.txt
python tools/codegen/python/generate.py --version v1beta1
python -m pip install -e sdks/python
```

## Usage

```python
from arp_sdk.daemon import DaemonClient, ListRunsRequest
from arp_sdk.models import InstanceCreateRequest

client = DaemonClient(base_url="http://127.0.0.1:8082")
health = client.health()
instances = client.list_instances()
created = client.create_instances(InstanceCreateRequest(runtime_profile="default", count=1))
runs = client.list_runs(ListRunsRequest(page_size=50))
```

## Build artifact locally

```bash
python -m pip install -r tools/codegen/python/requirements-dev.txt
python tools/codegen/python/build_local.py --version v1beta1 --clean
```

## Release (PyPI)

The GitHub Actions workflow `release` publishes this package when you push a tag matching:

- `v<version>` (example: `v1.0.0b2`)

The workflow verifies the tag matches `sdks/python/pyproject.toml` and `arp_sdk.__version__`, then builds and publishes using PyPI Trusted Publishing (OIDC).
It also rejects tags that are not contained in `origin/main`.

On tag pushes, the workflow also creates a GitHub Release and uploads the wheel/sdist as release assets.
