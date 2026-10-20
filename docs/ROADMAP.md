# Roadmap

Version 1.5 rebuilds the browser interface around the decision trail. It
remains a research lab. See [Verification](VERIFICATION.md) for measured results
rather than treating this roadmap as a completion record.

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
- Find a compatible patched model runtime. The current Kev candidate requires a
  vulnerable PyTorch range and is quarantined.
- Evaluate a reviewed replacement on independent workloads. The measured CPU
  candidate missed the 500 ms budget on every calibration case.
- Add OS-level isolation before executing untrusted commands.
- Define recovery for uncertain execution outcomes; the executor does not provide
  durable exactly-once execution.

## Later options

A web setup wizard should stay assistive and must never receive the Docker socket
or operator keys. Shared rate-limit storage would be needed across workers.
Finer permissions and additional forensic views are follow-up work, not
implemented guarantees. Pattern promotion remains an operator decision.
