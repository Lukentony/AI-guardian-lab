# Configuration

Use `.env.example` as the current variable reference. Compose reads `.env`; host
Python scripts do not implicitly load or execute it. Back up private settings
before editing them. Never paste expanded configuration, keys or shell tracing
into issue reports.

## Credentials and service roles

| Variable | Purpose |
| --- | --- |
| API_KEY | Agent/Guardian authenticated API access; no empty/placeholder key |
| LOG_HMAC_KEY | Persistent audit signing key; preserve across upgrades |
| TASK_API_KEY | Separate operator credential for task registration and pattern approval |
| UI_USERNAME, UI_PASSWORD | Basic authentication for the browser UI |
| SYSTEM_ONE_API_KEY | Dedicated credential for the optional local model service |

The operator key must differ from the Agent key and is never sent to Agent or
model containers. For legacy audit compatibility, an unset LOG_HMAC_KEY falls
back to API_KEY; there is no built-in development key. A changed signing key
will not verify earlier signatures. New installations create distinct keys.

## Models and execution

- `LLM_PROVIDER`: generator provider, default `ollama`.
- `LLM_MODEL_CODER`: actual generator model name, including a provider prefix
  where LiteLLM requires one. Old `OLLAMA_MODEL_CODER` is not the runtime setting.
- `LLM_MODEL_EXPLAIN`: forensic analysis model. Compose forwards it as
  `FORENSICS_LLM_MODEL` to Guardian; the default is `deepseek-coder-v2:16b`.
- `OLLAMA_URL`: explicit local/private model service address; the Compose default
  host-gateway address differs from a host shell's localhost.
- `INTENT_LLM_MODEL`: bounded semantic reviewer used only when required.
- `EXECUTE_COMMANDS=false`: default simulation; setting true is not a sandbox.
  Real execution also requires an operator-registered task_id and workspace.
- `FAIL_CLOSED_ON_LLM_ERROR=false` no longer grants approval. Unavailable or
  malformed semantic review always denies; do not depend on the obsolete flag.

There is no automatic cloud fallback. Selecting a hosted generator shares task
data with that provider. System One accepts only local/private inference endpoints.

## Policy and patterns

`guardian/config/policy.yaml` must have enforced mode and disjoint green, yellow
and red binary lists. Invalid/missing policy prevents startup. The green list
includes the documented read-only `df` example; allowing a binary is not blanket
permission for every argument or shell construct.

Static `patterns.yaml` must compile completely. The `regex` engine enforces a
50 ms timeout per search, unlike the old uncancellable worker-thread wrapper.
A timeout is a denial, never "no match". Raw and normalized views are inspected;
normalization does not define execution semantics or a complete Bash interpreter.

Store reviewed runtime patterns in this list format:

```yaml
version: 1
learned_patterns:
  - pattern: 'example_forbidden_token'
    description: 'Explicit operator review'
suggestions: []
```

The older nested enabled/patterns format is read for migration. New writes are
atomic and cross-process locked. The learner only produces pending suggestions;
frequency percentages are not model confidence or approval. Invalid runtime
pattern state denies validation instead of silently losing protection.

## System One

`guardian/config/system_one.yaml` accepts only `off` or `shadow`. Endpoint,
concrete model identifier and a 0.05–1 second observer timeout are validated.
`SYSTEM_ONE_URL` can override the local endpoint for Compose. There is no runtime
auto-approval threshold. The bundled CPU service is quarantined; see
[System One](SYSTEM_ONE.md) for the security conflict and measured limits.

## Persistence, ports and resources

Compose uses `state/audit` and `state/learned`; preserve them and signing keys.
`LOCAL_UID`/`LOCAL_GID` must match the non-root owner of these bind mounts. UI has
no database mount; it reads the authenticated `/audit` endpoint.

Default published ports are loopback-only 5000 (Guardian), 5001 (Agent), 8081
(UI). Changing GUARDIAN_BIND_IP can expose the service beyond the host. Review
that change separately; do not use it to bypass an integration's network protections. The optional model profile publishes no port.
Its CPU runtime and model cache are separate from Guardian's 512 MiB limit.

In-memory rate limiting and semaphores are per worker. Configure a shared
RATE_LIMIT_STORAGE_URI for cross-worker rate enforcement; do not assume the
memory backend provides cluster-wide limits.
