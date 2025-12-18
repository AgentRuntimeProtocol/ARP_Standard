# ARP Standard

Canonical HTTP+JSON contracts and schemas for Agent Runtime Protocol (ARP) components.

This repo contains:

- The normative spec: [`spec/v1/`](spec/v1/README.md)
- The generated Python SDK: [`arp-standard-py`](sdks/python/README.md) (imported as `arp_sdk`)

## The SDK
The SDKs generated and published are "client-focused" artifacts for an application to use for *talking with an ARP-Compliant component". For example, if your runtime needs to talk to an ARP-compliant Tool Registry, then the SDK provides an easy way without worrying about implementing each API call. 

It can also be used to do integration test validation for developers working on their ARP-compliant implementation for components like Agent Runtime, Daemon or Tool Registry. Just write tests to use SDK to call your service!

### Codegen
The SDK artifacts, as you can see, are not included in the repo itself. It is generated from the [`spec`](spec/README.md) defined, which serves as the source of truth for all SDKs, and is the *defacto* "ARP Standard". 

Code generation pipelines read the specs and generate language-specific SDK implementations automatically at release time. The generated artifacts are validated against the `spec` schemas, and published to their corresponding package providers, like `PyPI` for Python. 

> Never manually edit the generated files. They will be overwritten by new generations!

### Language/Framework Support

Currently only a Python `arp-standard-py` package is published via PyPi. See its [README](sdks/python/README.md).

There is ongoing work to develop other SDKs in JavaScript, Go etc. 

### Install (Python SDK)

```bash
# pip directly
pip install arp-standard-py

# or, pip as a python3 module
python3 -m pip install arp-standard-py
```

### Use Sample

```python
from arp_sdk.daemon import DaemonClient
from arp_sdk.models import InstanceCreateRequest

client = DaemonClient(base_url="http://127.0.0.1:8082")
created = client.create_instances(InstanceCreateRequest(runtime_profile="default", count=1))
print(created.to_dict())
```

## Versioning

ARP uses versioned API namespaces (Kubernetes-style):
- `v1` (stable)

## Docs

- Docs index: [`docs/README.md`](docs/README.md)
- Spec overview: [`docs/spec.md`](docs/spec.md)
- Services overview: [`docs/services.md`](docs/services.md)
- Conformance: [`docs/conformance.md`](docs/conformance.md)
- Python SDK: [`docs/python-sdk.md`](docs/python-sdk.md)

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License
MIT License applies to this repo.
See [`LICENSE`](LICENSE).
