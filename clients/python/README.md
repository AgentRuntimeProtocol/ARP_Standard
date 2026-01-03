# ARP Standard Python Client (`arp-standard-client`)

## Install

```bash
python3 -m pip install arp-standard-client
```

## Usage

```python
from arp_standard_client.run_gateway import RunGatewayClient
from arp_standard_model import (
    NodeTypeRef,
    RunGatewayHealthRequest,
    RunGatewayStartRunRequest,
    RunStartRequest,
)

client = RunGatewayClient(base_url="http://127.0.0.1:8080", bearer_token="your-jwt")
health = client.health(RunGatewayHealthRequest())
run = client.start_run(
    RunGatewayStartRunRequest(
        body=RunStartRequest(
            root_node_type_ref=NodeTypeRef(
                node_type_id="example.com/node-types/my-root",
                version="1.0.0",
            ),
            input={"goal": "Hello, ARP"},
        )
    )
)
```

### Request objects

All facade methods require a single request object from `arp_standard_model`. These request objects wrap:

- `params`: path/query parameters (if any)
- `body`: JSON request body (if any)

Request and params models are service-prefixed (e.g., `RunGatewayGetRunRequest`, `NodeRegistryListNodeTypesRequest`) to avoid collisions.
Request body models are also exported with a `*RequestBody` alias (e.g., `RunStartRequestBody`).

### Response payloads

Client methods return the spec-defined payload objects directly (for example: `Run`, `Health`, `VersionInfo`) rather
than service-specific `*Response` wrappers. For forward-compatible additions, use `extensions` (and `metadata` where
available); arbitrary top-level fields are not allowed by the schemas (`additionalProperties: false`).

### Wire format

Models use the exact JSON field names from the spec (no aliasing). When serializing manually, use `model_dump(mode="json", exclude_none=True)`.

## Authentication (JWT Bearer)

```python
client = RunGatewayClient(
    base_url="http://127.0.0.1:8080",
    bearer_token="your-jwt",
)
```

## Streaming (NDJSON)

Streaming endpoints currently return NDJSON as plain text. Helpers are planned but not implemented yet.

```python
from arp_standard_client.run_gateway import RunGatewayClient
from arp_standard_model import RunGatewayStreamRunEventsParams, RunGatewayStreamRunEventsRequest

gateway = RunGatewayClient(base_url="http://127.0.0.1:8080", bearer_token="your-jwt")
text = gateway.stream_run_events(
    RunGatewayStreamRunEventsRequest(params=RunGatewayStreamRunEventsParams(run_id=run_id))
)
for line in text.splitlines():
    if not line:
        continue
    # json.loads(line)
```

## Spec reference

`arp_standard_client.SPEC_REF` exposes the spec tag (for example, `spec/v1@v0.3.7`) used to generate the package.

## See also

### General Documentation
- Spec (normative): [`spec/v1/`](../../spec/v1/README.md)
- Docs index: [`docs/README.md`](../../docs/README.md)
- Security profiles (auth configuration): [`docs/security-profiles.md`](../../docs/security-profiles.md)
- Repository README: [`README.md`](../../README.md)

### Python Specific Documentation
- Python client + models docs: [`docs/python-client.md`](../../docs/python-client.md)
- Model package: [`models/python/README.md`](../../models/python/README.md)
- Codegen (developers): [`tools/codegen/python/README.md`](../../tools/codegen/python/README.md)
