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

- `LLM_PROVIDER`: runtime provider, fixed to `llama.cpp` in the supported full
  profile.
- `LLM_API_BASE`: OpenAI-compatible endpoint. The full profile uses
  `http://llama:8080/v1`; the demo does not start a model.
- `LLM_API_KEY`: dedicated bearer key used by Guardian, Agent and llama.cpp.
- `LLM_MODEL`: served alias, default `qwen2.5-3b-instruct`.
- `LLAMA_MODEL_FILE`: pinned GGUF filename under `state/models`.
- `LLM_MODEL_CODER`: generator alias used by the Agent.
- `LLM_MODEL_EXPLAIN`: forensic analysis alias, forwarded as
  `FORENSICS_LLM_MODEL`.
- `INTENT_LLM_MODEL`: LiteLLM selector for the bounded reviewer, default
  `openai/qwen2.5-3b-instruct`.
- `COMPOSE_PROFILES=full`: starts llama.cpp, System One and the executor.
- `EXECUTOR_URL`: UI-to-executor endpoint in the full profile.
- `EXECUTOR_HMAC_KEY`: shared HMAC key for short-lived, command-bound execution
  tokens. Keep it out of the browser.
- `GUARDIAN_TIMEOUT_SECONDS`: Agent-to-Guardian HTTP timeout; full profile uses 45.
- `EXECUTE_COMMANDS=false`: default simulation; setting true is not a sandbox.
  Real execution also requires an operator-registered task_id and workspace.
- `FAIL_CLOSED_ON_LLM_ERROR=false` no longer grants approval. Unavailable or
  malformed semantic review always denies; do not depend on the obsolete flag.

The default is local. There is no automatic cloud fallback. A remote
OpenAI-compatible endpoint can be configured explicitly, but it is not a
supported demo profile: task and command text leave the host, and the provider
policy, key handling, cost limits and data residency need their own approval.
System One accepts only local/private inference endpoints.

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
concrete model identifier and a 0.05–5 second observer timeout are validated.
`SYSTEM_ONE_URL` can override the local endpoint for Compose.
`SYSTEM_ONE_TIMEOUT_SECONDS` overrides the YAML timeout (default 0.5; full profile
2.0). `SYSTEM_ONE_THREADS` controls the CPU service, default 8. There is no
runtime auto-approval threshold. The service is qualified for shadow use on
torch 2.13; see [System One](SYSTEM_ONE.md) for the measurements and limits.

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
