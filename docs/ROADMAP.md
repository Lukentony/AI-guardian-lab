# Roadmap

Version 1.6 adds a full local profile and qualifies the System One observer for
shadow use. It remains a research lab. See [Verification](VERIFICATION.md) for
measured results rather than treating this roadmap as a completion record.

## Completed in 1.6

- Full profile with llama.cpp, System One, `guardian-lab models` and
  `guardian-lab demo --full`.
- Kev on CPU torch 2.13.0, audited; the torch 2.8 quarantine is removed.
- Observer timeout configurable up to 5 seconds; full profile uses 2 seconds.
- Native full-stack and Docker VM verification: semantic review, System One
  observation, forensics, dry-run Agent and a valid audit chain.

## Completed in 1.5

- Dashboard with summary metrics, search, status filtering and source badges.
- Deterministic demo page and endpoint, with no execution path.
- Read-only status page for Guardian, Agent and the audit API.
- Restyled forensics report with visible incomplete-analysis state.

## Completed in 1.4

- `guardian-lab setup`, `doctor` and `demo` for the first test.
- A checksummed archive and prebuilt `linux/amd64` images.
- Incomplete forensic analysis is no longer reported as clean.

## Next work

- Run the onboarding path on Debian, macOS Docker Desktop and WSL2, then decide
  which targets are supported rather than experimental.
- Verify persistent-state recovery on a long-lived host with backups.
- Publish multi-architecture images and pin them by digest after qualification.
- The 0.8B observer still misses the default 500 ms budget; the full profile uses
  2 seconds. Evaluate a faster backend or hardware before claiming the default.
- Evaluate the observer on independent workloads and hold out the test split.
- Add OS-level isolation before executing untrusted commands.
- Define recovery for uncertain execution outcomes; the executor does not provide
  durable exactly-once execution.

## Later options

A web setup wizard should stay assistive and must never receive the Docker socket
or operator keys. Shared rate-limit storage would be needed across workers.
Finer permissions and additional forensic views are follow-up work, not
implemented guarantees. Pattern promotion remains an operator decision.
