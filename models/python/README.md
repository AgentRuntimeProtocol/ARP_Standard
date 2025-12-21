# ARP Standard Python Models (`arp-standard-model`)

Generated Pydantic models for the ARP Standard (v1).

## Install

```bash
python3 -m pip install arp-standard-model
```

## Usage

```python
from arp_standard_model import (
    RunRequestBody,
    RunStatus,
    RuntimeGetRunStatusParams,
    RuntimeGetRunStatusRequest,
)

req = RuntimeGetRunStatusRequest(params=RuntimeGetRunStatusParams(run_id="run_123"))
```

## Request model conventions

- `*RequestBody` aliases point to JSON body models (e.g., `RunRequestBody`).
- `*Params` models represent path/query parameters.
- `*Request` models wrap `params` and/or `body` and are used by the client facade.
- Request and params models are service-prefixed to avoid collisions (e.g., `RuntimeGetRunStatusRequest`).

## Wire format

Models use the exact JSON field names from the spec (no aliasing). When serializing manually, use `model_dump(exclude_none=True)`.

## Spec reference

`arp_standard_model.SPEC_REF` exposes the spec tag (for example, `spec/v1@v0.2.1`) used to generate the package.

## See also

- Spec (normative): [`spec/v1/`](../../spec/v1/README.md)
- Python client: [`clients/python/README.md`](../../clients/python/README.md)
