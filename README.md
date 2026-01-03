<div align="center">
  <a href="https://agent-runtime-protocol.com/">
    <picture>
      <source srcset="./images/ARP_Long_Transparent.png">
      <img alt="ARP Logo" src="./images/ARP_Long_Transparent.png" width="80%">
    </picture>
  </a>
</div>

<div align="center">
  <h3>The open, modern, modular standard for agentic system.</h3>
</div>

<div align="center">

  <a href="https://pypi.org/project/arp-standard-model/#history" target="_blank"><img src="https://img.shields.io/pypi/v/arp-standard-model?label=arp-standard-model" alt="Version - Model"></a>
  <a href="https://pypistats.org/packages/arp-standard-model" target="_blank"><img src="https://img.shields.io/pepy/dt/arp-standard-model" alt="PyPI - Downloads - Model"></a>
  <a href="https://opensource.org/licenses/MIT" target="_blank"><img src="https://img.shields.io/pypi/l/arp-standard-model" alt="PyPI - License"></a>

  <a href="https://pypi.org/project/arp-standard-server/#history" target="_blank"><img src="https://img.shields.io/pypi/v/arp-standard-server?label=arp-standard-server" alt="Version - Server"></a>
  <a href="https://pypistats.org/packages/arp-standard-server" target="_blank"><img src="https://img.shields.io/pepy/dt/arp-standard-server" alt="PyPI - Downloads - Server"></a>
  <a href="https://opensource.org/licenses/MIT" target="_blank"><img src="https://img.shields.io/pypi/l/arp-standard-server" alt="PyPI - License"></a>

  <a href="https://pypi.org/project/arp-standard-client/#history" target="_blank"><img src="https://img.shields.io/pypi/v/arp-standard-client?label=arp-standard-client" alt="Version - Client"></a> 
  <a href="https://pypistats.org/packages/arp-standard-client" target="_blank"><img src="https://img.shields.io/pepy/dt/arp-standard-client" alt="PyPI - Downloads - Client"></a>
  <a href="https://opensource.org/licenses/MIT" target="_blank"><img src="https://img.shields.io/pypi/l/arp-standard-client" alt="PyPI - License"></a>

  <a href="https://www.reddit.com/r/AgentRuntimeProtocol/" target="_blank"><img src="https://img.shields.io/badge/reddit-r%2FAgentRuntimeProtocol-ff6314?logo=reddit" alt="Reddit"></a>
   
</div>
<div align="center">
  <a href="https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/agentruntimeprotocol/ARP_Standard" target="_blank"><img src="https://img.shields.io/static/v1?label=Dev%20Containers%20For%20ARP%20Standard&message=Open&color=blue&logo=visualstudiocode" alt="Open in Dev Containers"></a>
  <a href="https://codespaces.new/agentruntimeprotocol/ARP_Standard" target="_blank"><img src="https://github.com/codespaces/badge.svg" alt="Open ARP Standard in Github Codespace" title="Open ARP Standard in Github Codespace" width="150" height="20"></a>
</div>

---

_**Agent Runtime Protocol**_ is an open standard for running agentic workflows in a consistent way across runtimes, tools, model providers, environments, and even protocols. It is built to be open, modular, adaptive, and distributed. 

ARP is:
- **Language-agnostic**: the standard is defined as contracts, not as a single official client or server library.
- **Cloud/model-agnostic**: designed to support multiple deployment environments and model providers. Components can live close or far from each other.
- **Modular**: every component can be swapped out (gateways, coordinators, executors, registries, policy, control planes).
- **Standard-first**: contracts are the product wedge; implementations exist to validate and accelerate adoption.
- **Interoperable**: alternative protocols like *MCP* and *A2A* can interact with or be incorporated in the ARP ecosystem with simple, often first-party wrappers.

## What's in this repo

- Current standard: [`spec/v1/`](spec/v1/README.md)
- Docs: [`docs/`](docs/README.md)
- Generated Python client: [`clients/python/`](clients/python/README.md)
- Generated Python models: [`models/python/`](models/python/README.md)
- Generated Python server bases: [`kits/python/`](kits/python/README.md)
- Conformance checker (Python): [`conformance/python/`](conformance/python/README.md)
- Tooling (codegen, validation): [`tools/`](tools/)

## Start here

If you want the exact contracts:
- Read the ARP Standard: [`spec/v1/`](spec/v1/README.md)
- Play with the generated Python client + models to see the contracts in action.
- Optionally, the docs: [`docs/README.md`](docs/README.md)

If you want something runnable:
- Use [JARVIS](https://github.com/AgentRuntimeProtocol/JARVIS_Release), the first‑party reference stack implementing the ARP Standard service set.
- JARVIS exists not only as a product, but also as an validation of the standard and to provide a working reference implementation.

## Why ARP

Most agent systems today carry one or more of the following risks:
- Framework-specific: it is hard to swap out runtime/tool stacks.
- Product-specific: coupled to a vendor’s hosted platform.
- Integration-heavy: every agent and tool combination needs custom wiring.

ARP’s goal is to make agent ecosystems composable:
- A Run Gateway exposes client-facing run APIs.
- A Run Coordinator owns run lifecycle, enforcement, and audit history.
- Atomic and Composite Executors execute NodeRuns.
- A Node Registry publishes NodeTypes; a Selection service generates bounded candidate sets.
- Any compliant client can talk to any compliant component.

Unlike monolithic agent systems, you can adopt ARP incrementally:
1) Register Atomic NodeTypes for existing services/tools.
2) Deploy Atomic Executors for execution (in-proc or on-wire).
3) Add a Run Coordinator + Run Gateway for durable runs and enforcement.
4) Add Node Registry + Selection as shared services (optional for dev).
5) Add policy (PDP), approvals, and observability as needed.

## Interoperability with other standards

ARP is designed to interoperate, not compete in a silo.

Examples:
- Tool ecosystems: import MCP tools as Atomic NodeTypes via an MCP adapter (executed by an Atomic Executor).
- Agent-to-agent: bridge to A2A-style communication where needed.
- Agent-as-a-service: provide facades compatible with Agent Protocol style APIs.

Some of these adapters are being built in the first-party *JARVIS* stack. ARP is not a walled garden—it is meant to work with existing and upcoming standards, and can serve as a “glue layer” between them.

## Design principles

Standard design goals:
- Strong contracts: explicit schemas, consistent error envelopes, stable versioning.
- Forward compatibility: flexible extension points for new feature needs.
- Capability discovery: clients can detect supported feature sets to avoid lockstep upgrades.
- Conformance testing in client/server packages: generated client and server packages are validated against the schemas to provide reliable artifacts that adhere to the standard.

In addition, ARP ships an official endpoint-level conformance checker:
- `arp-conformance` validates running v1 services (Run Gateway, Run Coordinator, Executors, Node Registry, Selection) against the ARP Standard schemas.

## Clients and server bases

The published Python SDKs target the v1 node-centric service set (Run Gateway / Run Coordinator / Executors / Node Registry / Selection).
Some languages also ship a companion models package and a server base package (builder kit) to implement components with the same contracts.

They’re also useful for integration/conformance testing: write tests that call your service via the client and validate behavior against the contracts.

### Language support

Currently, Python packages are published:
- Python client: [`arp-standard-client`](clients/python/README.md) (imported as `arp_standard_client`)
- Python models: [`arp-standard-model`](models/python/README.md) (imported as `arp_standard_model`)
- Python server bases: [`arp-standard-server`](kits/python/README.md) (imported as `arp_standard_server`)

Other client libraries (JavaScript, Go, etc.) are planned/in progress.

### Install (Python)

```bash
python3 -m pip install arp-standard-client
```

Models only:

```bash
python3 -m pip install arp-standard-model
```

Server bases:

```bash
python3 -m pip install arp-standard-server
```

### Conformance checker (Python CLI)

```bash
python3 -m pip install arp-conformance
arp-conformance check run-gateway --url http://127.0.0.1:8080 --tier smoke
```

### Quick example

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
print(run.model_dump(mode="json", exclude_none=True))
```

### Server example (FastAPI)

```python
from arp_standard_server import AuthSettings
from arp_standard_server.run_gateway import BaseRunGatewayServer
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
        return ...

    async def stream_run_events(self, request: RunGatewayStreamRunEventsRequest) -> str:
        return ""

    async def version(self, request: RunGatewayVersionRequest) -> VersionInfo:
        return ...

app = MyRunGateway().create_app(auth_settings=AuthSettings(mode="disabled"))
```

### Authentication (JWT Bearer)

```python
client = RunGatewayClient(
    base_url="http://127.0.0.1:8080",
    bearer_token="your-jwt",
)
```

### Streaming (NDJSON)

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

### Code generation

The spec in [`spec/v1/`](spec/v1/README.md) is the source of truth for the ARP Standard.

Code generation pipelines read the contracts (OpenAPI + JSON Schemas) and generate language-specific client packages (and models where applicable) automatically at release time.

The generated artifacts are validated against the spec schemas and published to their corresponding package providers (for example, `PyPI` for Python).

> [!NOTE]
> Never manually edit generated files. They will be overwritten by new generations.

For client/server codegen developers, see [`tools/codegen/python/README.md`](tools/codegen/python/README.md).

## Versioning

ARP uses versioned API namespaces (Kubernetes-style):
- `v1` (current; `/v1/...`)

All endpoints in the v1 spec are versioned under the `/v1` path prefix (e.g. `GET /v1/health`).

## Docs

- Docs index: [`docs/README.md`](docs/README.md)
- Spec overview: [`docs/spec.md`](docs/spec.md)
- Security profiles (auth configuration): [`docs/security-profiles.md`](docs/security-profiles.md)
- Services overview: [`docs/services.md`](docs/services.md)
- Conformance: [`docs/conformance.md`](docs/conformance.md)
- Python client + models: [`docs/python-client.md`](docs/python-client.md)
- Python server bases: [`docs/python-server.md`](docs/python-server.md)

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

Ways to contribute:
- Add conformance tests and golden vectors to expand client validation coverage.
- Build interoperability bridges (MCP, A2A, Agent Protocol) and feed back schema needs.
- Propose standard changes backed by concrete implementation evidence.
- Any other things that the core devs didn't think of. We know there's a lot.

Contribution model:
- Standards changes should be justified by real implementation evidence (e.g., “I tried X in an ARP‑compliant way, but Y made it impossible; Z would fix it.”).
- Prefer prototyping new needs via `extension` fields first; once proven, propose moving them into normative fields in a future version.

## Security

If you find a security issue, please send a private communication to the maintainers, or file an issue with minimal detail and request an owner contact. Do not discuss security issues in public forums.

## License

MIT License applies to this repo. See [`LICENSE`](LICENSE).
