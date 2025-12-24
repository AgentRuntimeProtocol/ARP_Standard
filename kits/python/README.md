# ARP Standard Python Server (`arp-standard-server`)

FastAPI server scaffolding for implementing ARP components with spec-aligned request/response types.

## Install

```bash
python3 -m pip install arp-standard-server
```

## Usage

```python
from arp_standard_server.daemon import BaseDaemonServer
from arp_standard_server import AuthSettings
from arp_standard_model import DaemonCreateInstancesRequest, InstanceCreateRequestBody

class MyDaemon(BaseDaemonServer):
    async def create_instances(self, request: DaemonCreateInstancesRequest):
        body = request.body
        # business logic here
        return ...

app = MyDaemon().create_app(auth_settings=AuthSettings(mode="disabled"))
```

## Service base classes

- `BaseRuntimeServer`
- `BaseToolRegistryServer`
- `BaseDaemonServer`

## Request objects

All server methods accept a single request object from `arp_standard_model`:

- `*Params` for path/query parameters
- `*RequestBody` for JSON bodies
- `*Request` wrappers with `params` and/or `body`

## Abstract method enforcement

Base server classes use `ABC` + `@abstractmethod`. Instantiating a class that does not implement all required endpoints raises a `TypeError` before the app is created.

## Authentication (JWT Bearer)

```python
app = MyDaemon().create_app(
    auth_settings=AuthSettings(
        mode="required",
        issuer="https://issuer.example.com/realms/arp",
        audience="arp-daemon",
    )
)
```

## Streaming (NDJSON)

NDJSON endpoints currently use plain text payloads. Streaming helpers are planned but not implemented yet.
