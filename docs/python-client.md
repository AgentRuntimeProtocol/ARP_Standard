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
from arp_standard_client.run_gateway import RunGatewayClient
from arp_standard_model import NodeTypeRef, RunGatewayStartRunRequest, RunStartRequest

client = RunGatewayClient(base_url="http://127.0.0.1:8080", bearer_token="your-jwt")
run = client.start_run(
    RunGatewayStartRunRequest(
        body=RunStartRequest(
            root_node_type_ref=NodeTypeRef(node_type_id="example.com/node-types/my-root", version="1.0.0"),
            input={"goal": "Hello, ARP"},
        )
    )
)
print(run.model_dump(exclude_none=True))
```

## Authentication (JWT Bearer)

Pass a JWT when constructing the client:

```python
client = RunGatewayClient(
    base_url="http://127.0.0.1:8080",
    bearer_token="your-jwt",
)
```

See also: [`docs/security-profiles.md`](security-profiles.md) for the standard auth configuration profiles (`Dev-Insecure`, `Dev-Secure-Keycloak`, `Enterprise`).

## Streaming (NDJSON)

The Python client currently treats `application/x-ndjson` as plain text for codegen. Streaming helpers are planned, but not implemented yet.

You can manually split the response for now:

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

## Requests and params

All client methods require a single request object from `arp_standard_model`. These request objects wrap:

- `params`: path/query parameters (if any)
- `body`: JSON request body (if any)

Request and params models are service-prefixed (e.g., `RunGatewayGetRunRequest`, `NodeRegistryListNodeTypesRequest`) to avoid collisions across services.
Request body models are also exported with a `*RequestBody` alias (e.g., `RunStartRequestBody`).

Example:

```python
from arp_standard_model import RunGatewayGetRunParams, RunGatewayGetRunRequest

req = RunGatewayGetRunRequest(params=RunGatewayGetRunParams(run_id="run_123"))
resp = client.get_run(req)
```

## Response payloads

Client methods return the spec-defined payload objects directly (for example: `Run`, `Health`, `VersionInfo`) rather
than service-specific `*Response` wrappers. For forward-compatible additions, use `extensions` (and `metadata` where
available); arbitrary top-level fields are not allowed by the schemas (`additionalProperties: false`).

## Wire format and serialization

Models use the exact JSON field names from the spec (no aliasing). When you need to serialize manually, use `model_dump(exclude_none=True)`.

## Forward compatibility

Models ignore unknown fields by default (Pydantic v2 behavior), so newer servers can add optional fields without breaking older clients. Other language clients should follow the same rule.

## Spec reference

Each package exports `SPEC_REF` (for example, `spec/v1@v0.3.5`) to indicate the spec tag used to generate the package.

## Generate locally (developers)

Run these from the repository root.

```bash
python3 -m pip install -r tools/codegen/python/model/requirements.txt
python3 -m pip install -r tools/codegen/python/client/requirements.txt

python3 tools/codegen/python/model/generate.py --version v1
python3 tools/codegen/python/client/generate.py --version v1
```

## Release (PyPI)

1. Update versions to match:
   - [`models/python/pyproject.toml`](../models/python/pyproject.toml)
   - [`models/python/src/arp_standard_model/__init__.py`](../models/python/src/arp_standard_model/__init__.py)
   - [`clients/python/pyproject.toml`](../clients/python/pyproject.toml)
   - [`clients/python/src/arp_standard_client/__init__.py`](../clients/python/src/arp_standard_client/__init__.py)
2. Tag the release:

```bash
git tag v0.3.5
git push origin v0.3.5
```

## See also

- Package README: [`clients/python/README.md`](../clients/python/README.md)
- Server bases: [`docs/python-server.md`](python-server.md)
