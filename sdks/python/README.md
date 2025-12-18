# ARP Standard Python SDK (`arp-standard-py`)

## Install

```bash
python3 -m pip install arp-standard-py
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

## See also

### General Documentation
- Spec (normative): [`spec/v1/`](../../spec/v1/README.md)
- Docs index: [`docs/README.md`](../../docs/README.md)
- Repository README: [`README.md`](../../README.md)

### Python Specific Documentation
- Python SDK docs: [`docs/python-sdk.md`](../../docs/python-sdk.md)
- Codegen (developers): [`tools/codegen/python/README.md`](../../tools/codegen/python/README.md)

