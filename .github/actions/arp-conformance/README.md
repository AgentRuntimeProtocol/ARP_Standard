# ARP Conformance Action

This composite action installs `arp-conformance` from PyPI and runs it against your ARP services.

## Inputs

- `python_version`: Python version for the runner (default: `3.11`)
- `service`: `runtime` | `tool-registry` | `daemon` | `all` (required)
- `tier`: `smoke` | `surface` | `core` | `deep` (default: `smoke`)
- `url`: base URL (required for non-`all`)
- `runtime_url`, `tool_registry_url`, `daemon_url`: URLs for `service=all`
- `tool_id`, `tool_name`: select a tool for Tool Registry invocation
- `runtime_profile`: select/create a runtime profile for Daemon checks
- `headers`: optional multiline `KEY=VALUE`
- `allow_mutations`: `true`/`false` (required for `core`/`deep`, default: `false`)
- `strict`: `true`/`false` (default: `false`)
- `report_format`: `text` | `json` | `junit` (default: `json`)
- `report_path`: output path (default: `arp-conformance.json`)
- `upload_artifact`: upload report (default: `true`)
- `artifact_name`: artifact name (default: `arp-conformance-report`)
- `package_version`: install a specific `arp-conformance` version (default: if the action ref is `vX.Y.Z`, installs `X.Y.Z`; otherwise installs latest)

## Example

```yaml
jobs:
  conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: AgentRuntimeProtocol/ARP_Standard/.github/actions/arp-conformance@v0.2.2
        with:
          service: runtime
          url: http://localhost:8081
          tier: surface
          report_format: json
          report_path: arp-conformance.json
```
