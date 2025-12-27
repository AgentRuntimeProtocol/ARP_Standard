# ARP Standard Python Server (`arp-standard-server`)

FastAPI server scaffolding for implementing ARP components with spec-aligned request/response types.

## Install

```bash
python3 -m pip install arp-standard-server
```

## Usage

```python
from arp_standard_server.run_gateway import BaseRunGatewayServer
from arp_standard_server import AuthSettings
from arp_standard_model import (
    Health,
    Run,
    RunGatewayCancelRunRequest,
    RunGatewayGetRunRequest,
    RunGatewayHealthRequest,
    RunGatewayStartRunRequest,
    RunGatewayStreamRunEventsRequest,
    RunGatewayVersionRequest,
    VersionInfo,
)

class MyRunGateway(BaseRunGatewayServer):
    async def cancel_run(self, request: RunGatewayCancelRunRequest) -> Run:
        return ...

    async def get_run(self, request: RunGatewayGetRunRequest) -> Run:
        return ...

    async def health(self, request: RunGatewayHealthRequest) -> Health:
        return ...

    async def start_run(self, request: RunGatewayStartRunRequest) -> Run:
        body = request.body
        # business logic here
        return ...

    async def stream_run_events(self, request: RunGatewayStreamRunEventsRequest) -> str:
        return ""

    async def version(self, request: RunGatewayVersionRequest) -> VersionInfo:
        return ...

app = MyRunGateway().create_app(auth_settings=AuthSettings(mode="disabled"))
```

## Service base classes

- `BaseRunGatewayServer`
- `BaseRunCoordinatorServer`
- `BaseAtomicExecutorServer`
- `BaseCompositeExecutorServer`
- `BaseNodeRegistryServer`
- `BaseSelectionServer`
- `BasePdpServer`

## Request objects

All server methods accept a single request object from `arp_standard_model`:

- `*Params` for path/query parameters
- `*RequestBody` for JSON bodies
- `*Request` wrappers with `params` and/or `body`

## Response payloads

Server methods return the spec-defined payload objects directly (for example: `Run`, `Health`, `VersionInfo`) rather
than service-specific `*Response` wrappers. For forward-compatible additions, use `extensions` (and `metadata` where
available); arbitrary top-level fields are not allowed by the schemas (`additionalProperties: false`).

## Abstract method enforcement

Base server classes use `ABC` + `@abstractmethod`. Instantiating a class that does not implement all required endpoints raises a `TypeError` before the app is created.

## Authentication (JWT Bearer)

```python
app = MyRunGateway().create_app(
    auth_settings=AuthSettings(
        mode="required",
        issuer="https://issuer.example.com/realms/arp",
        audience="arp-run-gateway",
    )
)
```

See also: [`docs/security-profiles.md`](../../docs/security-profiles.md) for the standard auth configuration profiles (`Dev-Insecure`, `Dev-Secure-Keycloak`, `Enterprise`).

## Streaming (NDJSON)

NDJSON endpoints currently use plain text payloads. Streaming helpers are planned but not implemented yet.
