# Python Server Bases (`arp-standard-server`)

- PyPI distribution: `arp-standard-server`
- Import package: `arp_standard_server`
- Model package: `arp-standard-model` (`arp_standard_model`)

## Install

```bash
python3 -m pip install arp-standard-server
```

## Basic usage

```python
from arp_standard_server.daemon import BaseDaemonServer
from arp_standard_model import DaemonCreateInstancesRequest, InstanceCreateRequestBody

class MyDaemon(BaseDaemonServer):
    async def create_instances(self, request: DaemonCreateInstancesRequest):
        body = request.body
        # business logic here
        return ...

app = MyDaemon().create_app()
```

## Service base classes

- `BaseRuntimeServer`
- `BaseToolRegistryServer`
- `BaseDaemonServer`

## Authentication (API key)

```python
app = MyDaemon().create_app(api_key="your-api-key")
```

## Request objects

Server methods accept a single request object from `arp_standard_model`:

- `*Params` for path/query parameters
- `*RequestBody` for JSON bodies
- `*Request` wrappers with `params` and/or `body`

## Validation errors

FastAPI request validation errors are mapped to an ARP `ErrorEnvelope` with HTTP 400.

## Wire format and serialization

Requests and responses use the exact JSON field names from the spec (no aliasing). When you serialize models manually, use `model_dump(exclude_none=True)`.

## Abstract method enforcement

Base server classes use `ABC` + `@abstractmethod`. Instantiating a class that does not implement all required endpoints raises a `TypeError` before the app is created.

## Streaming (NDJSON)

NDJSON endpoints currently use plain text payloads. Streaming helpers are planned but not implemented yet.

## Generate locally (developers)

Run these from the repository root.

```bash
python3 -m pip install -r tools/codegen/python/model/requirements.txt
python3 -m pip install -r tools/codegen/python/server/requirements.txt
python3 tools/codegen/python/model/generate.py
python3 tools/codegen/python/server/generate.py
```

## Spec reference

`arp_standard_server.SPEC_REF` exposes the spec tag (for example, `spec/v1@v0.2.2`) used to generate the package.
