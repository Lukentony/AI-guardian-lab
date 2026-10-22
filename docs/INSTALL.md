# Installation and upgrade

Installation starts services on the chosen host. Use it for local research, not
as a production sandbox. These instructions do not use sudo, change the firewall
or deploy to a remote machine.

## Fast path for a first test

For a demo, do not start with this document. Use [Onboarding](ONBOARDING.md):

```bash
./guardian-lab setup --profile demo
./guardian-lab doctor
./guardian-lab demo
```

That path needs Docker and no model, writes a private `.env` and asserts five
deterministic decisions. The rest of this page covers the interactive provider
wizard, upgrades, manual builds and data migration.

## Interactive installation

On the machine chosen to run the lab, open a dedicated terminal in the repository
root. Prerequisites are Docker with Compose v2 (`--wait` support), Python 3, curl
and a non-root account authorized to use Docker. GPU support is not required for
the baseline; the optional model service needs separate memory and model storage.

```bash
./install.sh
```

The interactive wizard creates a private `.env` with separate API, operator, audit,
UI and model keys. It sets the host UID/GID, uses `LLM_MODEL_CODER` consistently
and leaves `EXECUTE_COMMANDS=false`. Keys are not printed. An existing `.env` or
legacy audit database stops installation rather than being overwritten or migrated.
The installer does not start the System One profile. For the shorter demo path,
use `guardian-lab setup --profile demo`; for the full local profile, use
`guardian-lab setup --profile full`, then `guardian-lab models`.

Configure a local Ollama service explicitly. Compose uses
`http://host.docker.internal:11434` by default; both Guardian and Agent have the
Linux host-gateway mapping. The generator and semantic reviewer need their
selected models installed. Missing semantic inference denies ambiguous commands.
There is no automatic cloud fallback. Choosing a hosted generator shares task
data with that provider.

Compose owns build contexts. Guardian builds from the repository root; Agent
and UI build from their service directories. Health checks use Python's standard
library, not an undeclared curl binary. UI uses Gunicorn and Basic authentication,
and retrieves audit data through Guardian without any database mount.

## Existing configuration or data

Do not rerun the installer over existing settings: it deliberately stops rather
than rotating a signing key. Back up `.env` privately and preserve the old audit
key. Review `.env.example` for new names: `LLM_MODEL_CODER`, `EXECUTE_COMMANDS`,
`TASK_API_KEY`, UI credentials and optional System One settings.

Current Compose data paths are `state/audit` and `state/learned`; application code
is not mounted writable as a data directory. Match `LOCAL_UID`/`LOCAL_GID` to the
non-root host owner of these directories. Do not solve permissions with chmod 777.

If an older checkout contains `database/audit.db`, stop its writers using its own
Compose project first. On that same host, from that checkout's repository root,
use SQLite's backup API to obtain a consistent snapshot (including committed WAL
content), rather than copying only a live `.db` file:

```bash
python3 - <<'PY'
import sqlite3
from pathlib import Path
source = Path('database/audit.db')
target = Path('state/audit/audit.db')
if not source.is_file() or target.exists():
    raise SystemExit('Source missing or destination already exists; stop and inspect')
target.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as old:
    with sqlite3.connect(target) as new:
        old.backup(new)
print('Snapshot copied; original database preserved')
PY
```

Keep the original and private configuration backup. On first startup the shared
audit module adds missing columns transactionally without rewriting old records.
Unsigned history remains explicitly unverifiable; it is not silently signed as
if it had always been authentic. The verifier reports that distinction.

Review historical learned patterns before importing them. The old nested format
is readable, but statistical suggestions must not become reviewed policy merely
because a token occurred frequently. Active reviewed patterns belong under
`state/learned/learned_patterns.yaml`, not the read-only config mount.

After reviewing changes on the target host, use Compose directly instead of the
first-install wizard. The deployment owner is responsible for the actual build,
health checks, backups and rollback. Local development without Docker does not
prove image startup or bind-mount permissions.

## Development checks without Docker

On the development machine, open a dedicated terminal at the repository root.
With uv available, prepare the environment and run the tests:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest
```

Tests use temporary databases, block unmatched HTTP and mock semantic inference.
Agent tests are enabled. A subprocess test imports real package paths without
the legacy test aliases. The optional CPU service has a separate environment:
see [System One](SYSTEM_ONE.md).

## Recovery and operational limits

- Preserve state directories and signing keys when rebuilding images.
- Never claim a valid audit prefix proves that no valid suffix was deleted;
  trusted external checkpoints are still needed.
- After an uncertain execution/report timeout, inspect the validation identity
  and executor state. There is no durable exactly-once execution guarantee.
- Keep real execution disabled until an appropriate OS-level sandbox is supplied.
- Do not expose the UI or APIs remotely merely to bypass an integration's SSRF
  policy; use an explicitly authorized authenticated integration.
