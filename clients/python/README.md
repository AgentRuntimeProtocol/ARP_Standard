# ARP Standard Python Client (`arp-standard-client`)

## Install

```bash
python3 -m pip install arp-standard-client
```

## Usage

```python
from arp_standard_client.daemon import DaemonClient
from arp_standard_model import (
    DaemonCreateInstancesRequest,
    DaemonHealthRequest,
    DaemonListInstancesRequest,
    DaemonListRunsParams,
    DaemonListRunsRequest,
    InstanceCreateRequestBody,
)

client = DaemonClient(base_url="http://127.0.0.1:8082")
health = client.health(DaemonHealthRequest())
instances = client.list_instances(DaemonListInstancesRequest())
created = client.create_instances(
    DaemonCreateInstancesRequest(
        body=InstanceCreateRequestBody(runtime_profile="default", count=1)
    )
)
runs = client.list_runs(DaemonListRunsRequest(params=DaemonListRunsParams(page_size=50)))
```

### Request objects

All facade methods require a single request object from `arp_standard_model`. These request objects wrap:

- `params`: path/query parameters (if any)
- `body`: JSON request body (if any)

Request and params models are service-prefixed (e.g., `DaemonListRunsRequest`, `RuntimeGetRunStatusRequest`) to avoid collisions.
Request body models are also exported with a `*RequestBody` alias (e.g., `InstanceCreateRequestBody`).

### Wire format

Models use the exact JSON field names from the spec (no aliasing). When serializing manually, use `model_dump(exclude_none=True)`.

## Authentication (API key)

```python
client = DaemonClient(
    base_url="http://127.0.0.1:8082",
    headers={"X-API-Key": "your-api-key"},
)
```

## Streaming (NDJSON)

Streaming endpoints currently return NDJSON as plain text. Helpers are planned but not implemented yet.

```python
from arp_standard_client.runtime import RuntimeClient
from arp_standard_model import RuntimeStreamRunEventsParams, RuntimeStreamRunEventsRequest

runtime = RuntimeClient(base_url="http://127.0.0.1:8081")
text = runtime.get_run_events(
    RuntimeStreamRunEventsRequest(params=RuntimeStreamRunEventsParams(run_id=run_id))
)
for line in text.splitlines():
    if not line:
        continue
    # json.loads(line)
```

## Spec reference

`arp_standard_client.SPEC_REF` exposes the spec tag (for example, `spec/v1@v0.2.1`) used to generate the package.

## See also

### General Documentation
- Spec (normative): [`spec/v1/`](../../spec/v1/README.md)
- Docs index: [`docs/README.md`](../../docs/README.md)
- Repository README: [`README.md`](../../README.md)

### Python Specific Documentation
- Python client + models docs: [`docs/python-client.md`](../../docs/python-client.md)
- Model package: [`models/python/README.md`](../../models/python/README.md)
- Codegen (developers): [`tools/codegen/python/README.md`](../../tools/codegen/python/README.md)
