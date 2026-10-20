# AI Guardian Lab architecture

This document describes release 1.5.0, based on v1.2.0, including the
System One observer and the onboarding CLI. The lab does not provide a production
sandbox.

## Context and boundaries

An authenticated client asks the Agent to generate a shell command. Guardian
validates the exact proposed command before the cooperating Agent simulates it
or, only after explicit opt-in, executes it. Other agent frameworks need a real
pre-tool hook: merely asking a model to call Guardian does not enforce anything.
A malicious executor with independent OS access can bypass this HTTP service.

A model cannot override an executable, syntax or pattern block. The generative
review can approve only cases the deterministic checks pass for review. System
One only records observations: it supports `off` and `shadow`, and rejects `enforce`.

## Components

| Component | Responsibility | Runtime |
| --- | --- | --- |
| Guardian | Policy, task registry, validation, audit, forensics API | Python 3.11, Flask/Gunicorn |
| Agent | Command generation, strict approval consumer, simulation/outcome reporting | Python 3.11, Flask/Gunicorn |
| UI | Authenticated dashboard, deterministic demo, status and forensic form | Python 3.11, Flask/Gunicorn |
| Optional System One | Local typed inference, one admitted job, no execution | Python 3.13, Kev/PyTorch CPU, FastAPI/Uvicorn |
| Onboarding CLI | Private configuration, read-only diagnostics and a non-executing demo | Python 3.11, standard library |
| Shared audit module | Schema migration, redaction, transactional HMAC append and verification | `database/audit_logger.py` |

## Validation flow

1. Authenticate `X-API-Key`; validate JSON shape, lengths and task context.
2. Parse the **raw** command with the restricted `bashlex` grammar. Accept simple
   commands, `;`, `&&`, `||`, pipelines and selected file redirections. Reject
   substitutions, assignments, background jobs, compound syntax, globs and
   unsupported/malformed forms. This is intentionally not full Bash support.
3. L1 checks every executable. Basenames do not authorize arbitrary executable
   paths: only bare names and exact `/bin/name` or `/usr/bin/name` are accepted.
   The execution image and these directories must remain trusted.
4. L2 scans raw and heuristic-normalized views using the `regex` engine's actual
   timeout. A timeout, malformed learned file or evaluation error denies access.
   Altered/decoded text is never the command used for parsing or execution.
5. L3 evaluates all command effects, including output redirection and command
   chains. It shares its operation taxonomy with forensic annotation. Mixed or
   unknown task intentions require semantic review; the first keyword is not enough.
6. After deterministic checks, System One may observe the command, bounded recent
   task history and explicitly untrusted tool output. Its return value is ignored
   by authorization. Failure means **unavailable**, not safe. A concrete model,
   question fingerprint, probabilities and latency are retained in audit metadata.
7. When L3 requires L4, obtain one bounded generative review with no retries. Its
   response must satisfy strict field types/ranges. Missing, malformed, negative
   or insufficiently confident output denies execution. The model's confidence
   is not a measured security guarantee.
8. Append `approved` or `rejected` to audit. Audit failure withholds approval.
9. Agent accepts only HTTP 200, Boolean `approved` and a validation identity.
   It defaults to simulation and reports a separate terminal outcome. A lost
   report is an uncertain outcome, never an instruction to retry execution.

The concurrency semaphore is per Guardian worker (10 each), not a cluster-wide
limit. Default in-memory rate limiting is also per worker; shared enforcement
needs a separately configured store. Client validation timeout is five seconds.

## Interface

The UI is server-rendered Flask/Jinja with a local stylesheet and small vanilla
scripts. It has no execution path and no database mount.

- `/` reads the authenticated audit API through Guardian and renders summary
  metrics, recent decisions, source badges and a client-side filter.
- `/demo` sends the five fixed CLI cases to `/validate` through a server-side
  credential. It has a short cooldown, requires a same-origin POST and never
  calls an executor. Every click appends five signed decisions.
- `/status` probes Guardian, Agent and the audit API over loopback. It does not
  inspect Docker, the model service or the signing key; `guardian-lab doctor`
  remains authoritative for those checks.
- `/forensics` accepts a bounded transcript and displays the report, including an
  explicit incomplete state when a model check did not answer.

The UI reads `AGENT_URL` and `APP_VERSION` from its environment. Static assets
are copied into the image; no CDN, external font or frontend build step is used.

## Trust and task context

`POST /tasks` requires both the Agent API key and a distinct operator-only
`X-Task-Key` (`TASK_API_KEY`). The operator registers the original task, workspace,
allowed destinations and expiry. SQLite stores that context with an HMAC.
Agents can retrieve a registered task but cannot create one with their key alone.
`task_id` validation refuses tampering, expiry, policy-version changes and task
substitution. Real execution requires a registered task and the configured
workspace. Legacy task-only requests remain available for dry-run research and
are clearly marked `caller_supplied` to the observer, never registered authority.

Workspace/destination descriptions are contextual evidence, not OS capabilities.
The present shell argument policy is not a complete filesystem/network sandbox.
Tool-output provenance is labelled, not cryptographically established by the
Agent. An authenticated reporter is assumed to report outcomes honestly.

## Data and recovery

- Canonical schema: `database/schema.sql`; no second Guardian SQL schema.
- Compose audit data: `state/audit/audit.db`, with WAL sidecars in that directory.
- Reviewed patterns: `state/learned/learned_patterns.yaml`, atomic replacement
  under a cross-process file lock. Each request reads persisted authority.
- Pattern mining creates pending suggestions only; an operator approves patterns.
- Registry context is signed and persistent, but is not encrypted at rest. Do not
  place credentials in tasks. Redaction is best-effort, not a secrets detector.
- New audit records use canonical-JSON HMAC-SHA256 over all decision metadata,
  predecessor and identity. Read-last and append share `BEGIN IMMEDIATE` to avoid
  concurrent chain forks. Duplicate terminal outcomes are constrained in SQLite.
- Old unsigned rows are preserved and reported as **unverifiable**. The first new
  signature anchors their complete migrated representation, not their historical
  authenticity. Historical v1 HMAC signatures remain verifiable with the old key.
- Preserve signing keys. A consistent SQLite backup and corresponding key are
  both required for recovery. Do not rotate keys or fabricate old signatures.
- A trusted external checkpoint is needed to detect valid suffix deletion or
  whole-database rollback. Host/key compromise is outside the HMAC guarantee.
- A validation can be approved without an execution outcome if a client crashes.
  Inspect state; the lab does not implement durable exactly-once execution.

## Network and deployment

Compose publishes Guardian 5000, Agent 5001 and UI 8081 on loopback by default.
UI requires HTTP Basic authentication and rejects cross-origin browser POSTs.
It reads the authenticated Guardian audit API and has no database mount. Only
backend code holds the Guardian credential; browsers never receive it.
Use TLS and an authenticated reverse proxy before any deliberate remote exposure.

The optional System One profile has no published port, no workspace or audit
mount, no execution tools and a separate key. Its current Kev/PyTorch candidate is
quarantined: one source gate, `system-one/qualification.py`, blocks bootstrap,
image dependency installation and service startup until the upstream dependency
security conflict and qualification failures have been resolved.

The client accepts only loopback, fixed local-service names or private-network
inference URLs; redirects,
environment proxies and automatic retries are disabled. No hosted-model fallback
is implemented. The local service admits one synchronous model job, so client
cancellation cannot release admission while inference is still running.

Python 3.11 application requirements and the separate Python 3.13 CPU inference
lock are isolated. Kev code is pinned to a Git commit and source-archive SHA-256;
its model release is pinned by the serving configuration. Dependencies and base
images still need regular vulnerability review. Non-root UIDs/GIDs must match
ownership of bind-mounted state directories.

## Build, verification and rollout

See [installation](docs/INSTALL.md), [onboarding](docs/ONBOARDING.md),
[API](docs/API.md), [System One qualification](docs/SYSTEM_ONE.md) and
[verification](docs/VERIFICATION.md). The release workflow publishes images and
an archive only for a tag; the CI workflow runs offline regression, type, lint
and Compose smoke tests. The onboarding job starts the stack, runs `doctor` and
asserts the five demo decisions without executing a command.

The current CPU candidate failed the observer's 500 ms latency budget in local
calibration. Its PyTorch dependency also conflicts with security updates.
Before a replacement can enforce decisions, it needs reviewed hardware and model
choices, calibration, held-out evaluation and explicit rollout approval.
