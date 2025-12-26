# Security profiles

AuthN and AuthZ are crucial yet complex aspects of developing any system, and ARP is no different. Different developers will have different auth requirements, and ARP aims to make this easier both in concept and in practice, by introducing **Security Profiles**. 

> [!NOTE]
> For people not familial with AuthN and AuthZ: AuthN is authentication, where a service verify that the caller **is who they say they are**. AuthZ is authorization, where a service verify that the caller **can do what they are trying to do**. 
> 
> AuthN is the foundation for AuthZ, and ARP focuses on AuthN to help components establish each other's identity. ARP also makes AuthZ easier by providing `arp-policy` as a helper to enforce AWS-IAM-like authorization policies at service boundaries (for example: Run Gateway, Node Registry, Selection).

The ARP Standard wire contract for authentication is always:

- HTTP header: `Authorization: Bearer <JWT>`
- OpenAPI scheme: `components.securitySchemes.ArpBearerJWT` in `spec/v1/openapi/*.openapi.yaml`

**Security profiles** are named presets for how developers start and configure an ARP service components. By following these instructions, you can achieve your desired level of authentication for your specific needs. Following the profiles **do not** change the wire contract itself. 

## How to use security profiles

1. **Pick a profile** (`Dev-Insecure`, `Dev-Secure-Keycloak`, `Enterprise`).
2. **Configure your ARP service** (usually env vars; for Python you can also pass `AuthSettings(...)`).
3. **If the profile uses auth**, obtain a JWT and send it as `Authorization: Bearer <JWT>` (or `bearer_token=...` in the Python client).

If you’re using the Python SDK (`arp-standard-server`), auth is configured either by:

- **Env vars** (default): if you don’t pass `auth_settings=...`, `AuthSettings.from_env()` is used.
- **Code**: pass `auth_settings=AuthSettings(...)` when creating the app.
- **Profile shortcut (optional)**: set `ARP_AUTH_PROFILE=...` (and usually `ARP_AUTH_SERVICE_ID=...`) to auto-fill common defaults.

---

## Profile 0: `Dev-Insecure` (auth disabled; local hacking/tests)

### 1) Configure the server

Set:

```bash
export ARP_AUTH_MODE=disabled
```

Or use the profile shortcut:

```bash
export ARP_AUTH_PROFILE=dev-insecure
```

Optional:

```bash
export ARP_AUTH_DEV_SUBJECT=dev
```

### 2) Start your service

- If your service uses `AuthSettings.from_env()`, just start it normally.
- Or explicitly configure in code:

```python
from arp_standard_server import AuthSettings

app = MyRunGateway().create_app(auth_settings=AuthSettings(mode="disabled"))
```

### 3) Call the service (no token)

- Don’t send `Authorization`.
- In `arp-standard-client`, omit `bearer_token`.

Notes:
- `GET /v1/health` and `GET /v1/version` are exempt from auth by default (`ARP_AUTH_EXEMPT_PATHS`), so no principal is set for those requests.

---

## Profile 1: `Dev-Secure-Keycloak` (local Keycloak; production-like AuthN)

### 1) Start a local issuer (Keycloak)

Use the dev STS helper:

```bash
python3 -m pip install arp-sts-keycloak
arp-sts-keycloak init --output ./arp-keycloak
cd ./arp-keycloak
docker compose up -d
```

Defaults:
- Issuer: `http://localhost:8080/realms/arp-dev`
- Clients: one per ARP service (for example: `arp-run-gateway`, `arp-run-coordinator`, `arp-node-registry`, `arp-selection`)

### 2) Configure each ARP service to require JWTs

For each service, set:

```bash
export ARP_AUTH_MODE=required
export ARP_AUTH_ISSUER=http://localhost:8080/realms/arp-dev
export ARP_AUTH_AUDIENCE=arp-run-gateway   # set per service (example: arp-run-gateway | arp-run-coordinator | arp-node-registry | arp-selection)
```

Or use the profile shortcut:

```bash
export ARP_AUTH_PROFILE=dev-secure-keycloak
export ARP_AUTH_SERVICE_ID=arp-run-gateway   # sets the default audience
```

Then start that service normally.

### 3) Get a token and call the service

Example (client credentials):

```bash
TOKEN="$(
  curl -sS -X POST \
    http://localhost:8080/realms/arp-dev/protocol/openid-connect/token \
    -d 'grant_type=client_credentials' \
    -d 'client_id=arp-run-gateway' \
    -d 'client_secret=arp-run-gateway-secret' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"access_token\"])'
)"
```

Use it:
- HTTP: `Authorization: Bearer $TOKEN`
- Python: `RunGatewayClient(..., bearer_token=TOKEN)`

What to expect:
- Missing/invalid `Authorization` returns `401` with `WWW-Authenticate: Bearer ...` and an `ErrorEnvelope`.

---

## Profile 2: `Enterprise` (external issuer / STS)

### 1) Configure the server (bring your own issuer)

Recommended:

```bash
export ARP_AUTH_MODE=required
export ARP_AUTH_ISSUER=https://issuer.example.com/realms/arp
export ARP_AUTH_AUDIENCE=arp-run-gateway   # set per service
```

Or use the profile shortcut:

```bash
export ARP_AUTH_PROFILE=enterprise
export ARP_AUTH_ISSUER=https://issuer.example.com/realms/arp
export ARP_AUTH_SERVICE_ID=arp-run-gateway
```

Optional overrides:
- If your issuer does not support (or you don’t want) OIDC discovery:

```bash
export ARP_AUTH_JWKS_URI=https://issuer.example.com/.well-known/jwks.json
```

- If you need a custom discovery URL:

```bash
export ARP_AUTH_OIDC_DISCOVERY_URL=https://issuer.example.com/.well-known/openid-configuration
```

### 2) Get a token and call the service

How you obtain the JWT depends on your issuer (Okta/Entra/Auth0/etc). Once you have it:
- HTTP: `Authorization: Bearer <JWT>`
- Python: pass it as `bearer_token=...`

---

## Optional auth mode (variant: incremental adoption)

Use this when you want “token if you have it” behavior (still validates real tokens).

### 1) Configure the server

```bash
export ARP_AUTH_MODE=optional
export ARP_AUTH_ISSUER=...
export ARP_AUTH_AUDIENCE=...
```

Optional:

```bash
export ARP_AUTH_ANONYMOUS_SUBJECT=anonymous
```

### 2) Expected behavior

- Missing `Authorization` → request proceeds with an anonymous principal (default `sub="anonymous"`).
- Invalid `Authorization` / invalid token → `401`.
- Valid token → principal is set from JWT claims.

---

## Running conformance against secured services

When a service runs in `required` mode, pass `Authorization` to `arp-conformance`:

```bash
arp-conformance check run-gateway \
  --url http://localhost:8080 \
  --tier surface \
  --headers "Authorization=Bearer $TOKEN"
```

For CI, prefer `--headers-file`:

```bash
cat > headers.env <<'EOF'
Authorization=Bearer ...
EOF

arp-conformance check run-gateway --url https://example.com --tier surface --headers-file headers.env
```

---

## Reference: env vars (`arp-standard-server`)

`arp-standard-server` reads these via `AuthSettings.from_env()`:

- `ARP_AUTH_PROFILE`: `dev-insecure`, `dev-secure-keycloak`, or `enterprise` (optional shortcut)
- `ARP_AUTH_MODE`: `required` (default), `optional`, or `disabled`
- `ARP_AUTH_ISSUER`: issuer base URL (used for `iss` verification and OIDC discovery)
- `ARP_AUTH_AUDIENCE`: expected `aud` value
- `ARP_AUTH_SERVICE_ID`: sets a default audience when `ARP_AUTH_AUDIENCE` is not set
- `ARP_AUTH_JWKS_URI`: JWKS URL (overrides discovery)
- `ARP_AUTH_OIDC_DISCOVERY_URL`: OIDC discovery URL (overrides `ARP_AUTH_ISSUER` derivation)
- `ARP_AUTH_ALGORITHMS`: comma-separated allowed algs (default `RS256`)
- `ARP_AUTH_CLOCK_SKEW_SECONDS`: JWT leeway (default `60`)
- `ARP_AUTH_EXEMPT_PATHS`: comma-separated paths that bypass auth (default `/v1/health,/v1/version`)
- `ARP_AUTH_DEV_SUBJECT`: `sub` value used in `disabled` mode (default `dev`)
- `ARP_AUTH_ANONYMOUS_SUBJECT`: `sub` value used in `optional` mode when no header is present (default `anonymous`)

JWKS resolution:
- If `ARP_AUTH_JWKS_URI` is set, it is used directly.
- Else if `ARP_AUTH_OIDC_DISCOVERY_URL` is set, it is fetched and `jwks_uri` is used.
- Else if `ARP_AUTH_ISSUER` is set, discovery is derived as `<issuer>/.well-known/openid-configuration`.
- If `ARP_AUTH_MODE != disabled` and none of the above are provided, auth initialization fails early.
