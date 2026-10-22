# API reference

Guardian/Agent require `X-API-Key`, except public `GET /health` liveness checks.
Never paste actual keys into examples or logs. The examples below reference keys
already supplied securely to the calling process; `.env` is loaded by Compose,
not automatically exported to your host shell.

## Guardian

### POST /validate

Use an explicit task for a research/dry-run request:

```json
{"command":"df -h","task":"check disk usage"}
```

Or bind to operator-owned task context:

```json
{"command":"ls /workspace","task_id":"<registered-task-id>"}
```

If both task and task_id are supplied, the task must match the stored original.
An optional `untrusted_tool_output` string is bounded to 8,192 characters and
never becomes a trusted instruction. Command length is 1,024 characters; task
length is 4,096. Unsupported shell grammar is denied rather than guessed.

A successful authorization response (HTTP 200) contains:

```json
{
  "approved": true,
  "reason": "Approved",
  "intent_source": "mapping",
  "validation_id": "<validation-uuid>",
  "system_one": {
    "mode": "shadow",
    "status": "unavailable",
    "decision_unchanged": true
  }
}
```

`approved` is always a Boolean, not a truthy string. Possible sources include
`input`, `shell`, `allowlist`, `regex`, `regex_error`, `mapping`, `llm`,
`llm_error` and `system_load`. A model result never reverses a previous block.
When `system_one.status=unavailable`, the baseline checks still decide whether
to authorize the command. An unavailable observation is not a favorable assessment.

Invalid JSON/types return 400, unauthorized access 401, invalid/expired/stale task
context 409, and unavailable audit 503 with `approved=false`. Consumers must
reject non-200, invalid schemas, missing identity and uncertain transport results.
See [response schema](schemas/validate_response.json).

### GET /audit

Authenticated, rate-limited read API for the UI. Returns `stats` with `total`
(validation decisions, not terminal outcomes), `executed` and `rejected`, plus
at most 20 latest `commands` containing timestamp, task, command, status,
`intent_source`, llm_provider and guardian_reason. Audit access failure returns
503. UI receives this through its server-side credential and never mounts the
SQLite directory.

### POST /tasks

Requires `X-API-Key` **and** `X-Task-Key`. `TASK_API_KEY` must differ from the Agent
API key; never install it in the Agent or model container.

```json
{
  "task": "List project files only",
  "workspace": "/workspace",
  "allowed_destinations": [],
  "ttl_seconds": 3600
}
```

Returns HTTP 201 with task_id, original task, policy version and expiry. Lifetime
must be 60–86,400 seconds. Common credential-like task content is rejected;
this is not a comprehensive secret detector or encrypted storage.

### GET /tasks/<task_id>

Returns registered context after authentication. Invalid or expired context
returns 404. Only the operator can register a task.

### POST /report

Report one terminal outcome for an approved validation:

```json
{
  "validation_id": "<validation-uuid>",
  "command": "df -h",
  "status": "simulated"
}
```

Statuses: `simulated`, `executed`, `execution_error`. The command digest must
match the approval. Identical repeats are idempotent; conflicting reports return
409. An authenticated Agent is trusted to report its outcome honestly. Validation
alone logs `approved`, never `executed`.

### POST /learn

Requires the same two operator headers as `/tasks`. Submit a bounded pattern and
optional description. Success (201) means persistence succeeded. Failed persistence
returns 503 without changing policy in just one worker. Pattern mining only
proposes candidates; it cannot approve them.

### POST /forensics/analyze

Authenticated request with a JSONL string and optional session_id. At most 500
line breaks and 1 MiB, also subject to the HTTP body limit. OpenHands and SWE-agent
arguments are preserved for annotation; OpenClaw remains explicitly unsupported.
This endpoint analyzes supplied session data; it does not execute its commands.
Forensic LLM availability affects completeness, not runtime authorization.

## Agent

### POST /execute

Task-only requests remain available for dry-run research:

```json
{"task":"show disk usage"}
```

Real execution is disabled unless `EXECUTE_COMMANDS=true`, and additionally
requires a registered task_id whose workspace matches `/workspace`:

```json
{"task_id":"<registered-task-id>"}
```

The Agent fetches the original task, generates one command, consumes a strict
Guardian approval and reports the outcome. Child execution does not inherit API
keys, BASH_ENV or a caller-controlled PATH. This is still a research executor,
not an OS sandbox. Timeout may leave side effects; do not assume rollback.

Responses include `simulated`, `rejected`, `executed`, `execution_error` or
`outcome_unreported`. The last is HTTP 503 and includes
`execution_may_have_occurred`: inspect the validation identity and executor state
before any retry. Exactly-once execution is not provided.

## UI and optional model service

UI uses Basic authentication (`UI_USERNAME`, `UI_PASSWORD`) on loopback port
8081; `/health` alone is public. It does not expose the backend API credential.
The optional model service uses a dedicated bearer key for `/v1/systemone` and
publishes no host port in Compose. Its Kev runtime is qualified for shadow use on
torch 2.13.0 and starts only in the full profile; see
[System One](SYSTEM_ONE.md).

## Authenticated dry-run example

From the repository root on the host running the services, in an existing shell
with API_KEY already available securely:

```bash
curl --fail-with-body http://127.0.0.1:5000/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  --data '{"command":"df -h","task":"check disk usage"}'
```

This checks a command; it does not execute it. Do not use `curl -v`, shell tracing
or logs that expose the header.

When `EXECUTOR_HMAC_KEY` is configured, an approved response also contains an
`execution_token`. The token is bound to that exact command and validation
identity, expires after 60 seconds and can be used once by the optional executor.
It is not a general credential: changing the command invalidates it. The executor
has no public host port and the UI is its only client.
