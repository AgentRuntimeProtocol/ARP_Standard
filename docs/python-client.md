# Python Client + Models

- Client PyPI distribution: `arp-standard-client`
- Client import package: `arp_standard_client`
- Models PyPI distribution: `arp-standard-model`
- Models import package: `arp_standard_model`
- Client README: [`clients/python/README.md`](../clients/python/README.md)
- Models README: [`models/python/README.md`](../models/python/README.md)

## Install

```bash
python3 -m pip install arp-standard-client
```

Models only:

```bash
python3 -m pip install arp-standard-model
```

## Basic usage

```python
from arp_standard_client.daemon import DaemonClient
from arp_standard_model import DaemonCreateInstancesRequest, InstanceCreateRequestBody

client = DaemonClient(base_url="http://127.0.0.1:8082")
created = client.create_instances(
    DaemonCreateInstancesRequest(
        body=InstanceCreateRequestBody(runtime_profile="default", count=1)
    )
)
print(created.model_dump(exclude_none=True))
```

## Authentication (API key)

Pass API keys via headers when constructing the client:

```python
client = DaemonClient(
    base_url="http://127.0.0.1:8082",
    headers={"X-API-Key": "your-api-key"},
)
```

## Streaming (NDJSON)

The Python client currently treats `application/x-ndjson` as plain text for codegen. Streaming helpers are planned, but not implemented yet.

You can manually split the response for now:

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

## Requests and params

All client methods require a single request object from `arp_standard_model`. These request objects wrap:

- `params`: path/query parameters (if any)
- `body`: JSON request body (if any)

Request and params models are service-prefixed (e.g., `DaemonListRunsRequest`, `RuntimeGetRunStatusRequest`) to avoid collisions across services.
Request body models are also exported with a `*RequestBody` alias (e.g., `InstanceCreateRequestBody`).

Example:

```python
from arp_standard_model import DaemonListRunsParams, DaemonListRunsRequest

req = DaemonListRunsRequest(params=DaemonListRunsParams(page_size=50))
resp = client.list_runs(req)
```

## Wire format and serialization

Models use the exact JSON field names from the spec (no aliasing). When you need to serialize manually, use `model_dump(exclude_none=True)`.

## Forward compatibility

Models ignore unknown fields by default (Pydantic v2 behavior), so newer servers can add optional fields without breaking older clients. Other language clients should follow the same rule.

## Spec reference

Each package exports `SPEC_REF` (for example, `spec/v1@v0.2.0`) to indicate the spec tag used to generate the package.

## Generate locally (developers)

Run these from the repository root.

```bash
python3 -m pip install -r tools/codegen/python/model/requirements.txt
python3 -m pip install -r tools/codegen/python/client/requirements.txt
python3 tools/codegen/python/model/generate.py
python3 tools/codegen/python/client/generate.py
```

## Release (PyPI)

1. Update versions to match:
   - [`models/python/pyproject.toml`](../models/python/pyproject.toml)
   - [`models/python/src/arp_standard_model/__init__.py`](../models/python/src/arp_standard_model/__init__.py)
   - [`clients/python/pyproject.toml`](../clients/python/pyproject.toml)
   - [`clients/python/src/arp_standard_client/__init__.py`](../clients/python/src/arp_standard_client/__init__.py)
2. Tag the release:

```bash
git tag v0.2.0
git push origin v0.2.0
```

## See also

- Package README: [`clients/python/README.md`](../clients/python/README.md)
- Server bases: [`docs/python-server.md`](python-server.md)
