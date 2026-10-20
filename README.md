# AI Guardian Lab

![Version](https://img.shields.io/badge/version-1.5.0-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)
![License](https://img.shields.io/badge/license-MIT-green)

AI Guardian Lab checks shell commands before a cooperating AI agent runs them.
The agent proposes a command; Guardian checks it against policy and the task.
The agent then simulates the action or, when explicitly enabled, executes it.

> **Research software.** Real execution is disabled by default. Enabling it runs
> `/bin/bash -c` without a complete OS-level sandbox. Do not give the executor
> sensitive workspaces or untrusted workloads on the assumption Docker is enough.

## Try it in five minutes

The demo needs Docker and no model. Download the release archive, or clone the
repository and run the same commands:

```bash
./guardian-lab setup --profile demo
./guardian-lab doctor
./guardian-lab demo
```

The demo validates five fixed commands and never executes them. It prints the
expected and actual decision, appends five signed audit records and checks that
the UI rejects anonymous access. Open `http://127.0.0.1:8081` and use the
credentials in `.env`. The dashboard links to the same demo, to a read-only
status page and to the forensics view. Release images are published for
`linux/amd64`; a checkout builds locally on first run. See
[Onboarding](docs/ONBOARDING.md) for the archive checksum, profiles, support
matrix and troubleshooting.

## What 1.5 adds

The browser interface is rebuilt around the decisions, not around the database:

- A dashboard with summary metrics, search, status filtering, source badges and
  truncated task or reason text with the full value on hover.
- A deterministic demo page and endpoint. It runs the same five cases as the CLI,
  writes five signed records, applies a short cooldown and never executes a
  command.
- A read-only status page for Guardian, Agent and the audit API. It does not
  inspect Docker, the model service or the signing key.
- A cleaner forensics report with a prominent incomplete-analysis state.
- A self-contained stylesheet and icons, with no CDN or external font.

The UI still has no execution path, no Docker socket and no database mount.

## What 1.4 adds

A first-run CLI replaces the long manual sequence with `setup`, `doctor` and
`demo`. The demo is deterministic, needs no model and asserts its expected
decisions instead of only printing them. Releases publish prebuilt images and a
checksummed archive. Forensic reports now mark an unavailable model as an
incomplete analysis instead of returning a clean summary.

## What 1.3 adds

Version 1.3 adds System One, an observer that asks a small local model four typed
questions about a command, its task and recent context: whether the action fits
the task, whether it moves data without authorization, whether it follows
untrusted instructions, and whether the recorded context is sufficient. The
answers are stored in the signed audit record of the decision.

It runs after the deterministic checks and before any required semantic review.
It has no authority: it cannot approve, block or rewrite a command, and a
favorable observation never skips L4. See [System One](docs/SYSTEM_ONE.md).

The bundled CPU candidate did not pass qualification. All eight calibration cases
missed the 500 ms budget, and it rated a harmless listing as high risk on data
transfer. Its PyTorch dependency also conflicts with security updates, so the
model service is quarantined before startup. The observer client, datasets and
evaluation script are included; enforcement is not.

## Command checks

The parser first rejects unsupported shell syntax. It inspects every command in
a chain and accounts for redirections. An executable such as `/tmp/ls` cannot
pass by sharing the name of an allowed system binary.

Guardian then applies four checks:

- **L1, allowlist:** reject executables outside the configured policy.
- **L2, patterns:** inspect raw and normalized text. A regex timeout or invalid
  pattern denies validation rather than silently dropping the check.
- **L3, intent:** compare the command's effects with the task, including network
  operations and writes through redirection.
- **L4, semantic review:** ask a model when the mapping needs review. Missing,
  malformed, negative or uncertain replies deny execution.

A model cannot reverse a deterministic rejection. The System One observer runs
in shadow mode after the deterministic checks and cannot change the decision.

```mermaid
flowchart LR
    A[Authenticated request] --> P[Restricted shell parser]
    P --> L1[Allowlist]
    L1 --> L2[Patterns and timeouts]
    L2 --> L3[Complete intent mapping]
    L3 --> S[Optional shadow observation]
    S --> L4[Required semantic review]
    L4 --> D[Signed authorization decision]
    D --> X[Default simulation or opted-in executor]
    X --> O[Separate terminal outcome]
```

A rejection goes straight to the audit decision. Approval is recorded separately
from execution: the executor reports a terminal outcome bound to the validation
identity and command digest. A lost report does not trigger an execution retry.

## System One status

The typed observer asks whether a command fits the task, transfers data without
authorization, follows untrusted instructions or lacks enough context. It uses
signed operator-owned task context when available. Agent-supplied text does not
become authorization. Inference must use a local or private endpoint; there is
no hosted fallback.

The bundled CPU candidate uses upstream Kev and `jaredpalmer/kev-0.8b@v1.0`.
Its eight calibration cases took about three seconds each and all missed the
500 ms budget. A smoke test also gave harmless `ls` a misleading high-risk score.
Kev's PyTorch constraint conflicts with security updates, so its service is now
**quarantined before installation or startup**. No enforcement threshold was set.
See [System One](docs/SYSTEM_ONE.md) for the measurements and replacement criteria.

## Running the lab

`guardian-lab` is the supported first-run path. Use [Onboarding](docs/ONBOARDING.md)
for the release archive, the demo and diagnostics. The older interactive
`install.sh` remains available for choosing a provider and a model; both paths
create a private `.env`.

Default host ports are loopback-only: Guardian 5000, Agent 5001 and UI 8081.
The UI requires Basic authentication and reads audit data through Guardian,
without a SQLite mount. Neither path starts the optional model service.

The [authenticated dry-run example](docs/API.md#authenticated-dry-run-example)
validates a command without executing it. Real execution also requires a
registered task and matching workspace.

## Audit and forensics

Audit records use a transactional HMAC-SHA256 chain with one schema and logger.
Legacy unsigned rows remain unverifiable. A trusted external checkpoint is needed
to detect deletion of a valid suffix or full database rollback. Signing cannot
protect a compromised host or stolen key.

The forensic API reads OpenHands and SWE-agent logs, retaining tool arguments for
annotation. It looks for escalation, intent drift and prompt-injection signals
after a session. Pattern mining produces suggestions; an operator must approve
them before they become policy.

## Checks and remaining work

[Verification](docs/VERIFICATION.md) records the passing tests, the dependency
audit, the failed CPU experiment and the container checks run in a disposable
Ubuntu 24.04 VM. GitHub CI also passed at the release commit. Synthetic fixtures
cover regressions; they do not measure real-world detection accuracy.

Every executor needs a pre-execution hook. Asking a model to call Guardian is not
enforcement. The task policy is not a complete filesystem or network sandbox,
and outcome reporting assumes an honest executor. Durable exactly-once execution
and production deployment remain outside the current implementation.

## Documentation

[Architecture](ARCHITETTURA.md) describes the components and trust boundaries.
Start with [Onboarding](docs/ONBOARDING.md), then use
[Configuration](docs/CONFIGURATION.md) and [API](docs/API.md) for setup and
integration. Read [Security](docs/SECURITY.md) before reporting a vulnerability.

## License

Project code is [MIT licensed](LICENSE). Dependencies retain their own licenses;
upstream Kev is Apache-2.0. SecJev has not been adopted.
