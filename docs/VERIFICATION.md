# Verification record: hardening and System One

Scope: release 1.3.1, published from branch `feature/system-one-hardening` and
based on `15b6f6672a6a12546e25e795d66a91919c93f02f`. This is not a production
approval. Model-based enforcement remains disabled and no remote deployment was
performed.

## Executed checks

| Check | Observed result |
| --- | --- |
| Complete offline pytest suite | **354 passed** (182 baseline, 172 adversarial), no skips |
| Application/scripts/tests Pyright | 0 errors, 0 warnings |
| Separate model-service Pyright project | 0 errors, 0 warnings |
| Ruff on changed runtime surfaces, including model service | Passed |
| Installer Bash syntax | Passed |
| Entrypoint/bootstrap/config-check POSIX shell syntax | Passed |
| `git diff --check` | Passed |
| Installed application-environment dependency audit | No known advisories reported |
| Model dependency lock resolution, reinstall dry-run | Resolved 70 packages; no installation performed by that check |
| Model service/bootstrap quarantine subprocess checks | Refused before model imports/downloads or socket startup |
| Container build and startup in a disposable Ubuntu 24.04 VM | 3 images built; all services healthy |
| UI authentication, audit API, chain verifier, restart persistence | Passed; details below |
| GitHub Actions CI at 9f68090 | Completed successfully |

The following checks ran from the repository root on the development machine,
in the coding session's own process:

```bash
.venv/bin/python -m pytest -q
.venv/bin/pyright guardian database agent ui scripts tests
.venv/bin/pyright -p system-one
.venv/bin/ruff check guardian database agent ui \
  scripts/evaluate_system_one.py scripts/pattern_learner.py \
  scripts/verify_logs.py system-one
bash -n install.sh
sh -n guardian/entrypoint.sh system-one/bootstrap.sh scripts/validate_config.sh
git diff --check
```

The suite uses temporary databases, mocked generators and blocked unmatched HTTP.
It includes actual subprocess package startup without the historical test-import
aliases, real regex-engine timeouts, malformed semantic/model replies, chains,
redirections, executable identity, task tampering/expiry, concurrent signed audit
appends, legacy migration and atomic reviewed-pattern persistence. Agent tests run
normally rather than being skipped. Tests do not execute attack commands.

UI tests cover authentication before backend access, cross-origin POST rejection,
HTTP audit retrieval, malformed/unavailable backend responses and refused redirects.
Audit API tests cover authentication, decision-versus-outcome counts, bounded latest
rows and database-open failure. The UI has no SQLite mount, avoiding the reproduced
read-only WAL-sidecar failure. No HTML/CSS redesign or production visual rollout
was performed; desktop/mobile appearance was not separately requalified.

Installer tests mock Docker/Ollama/curl and inspect private generated configuration,
consistent model names, simulation defaults, Compose build use and preservation of
an existing `.env`. Static Compose checks inspect contexts, COPY sources, health
commands, loopback exposure, private model profile and workspace mount syntax.
Those static checks do not prove container startup by themselves; the VM run
below covers that part.

The home-workspace language-server probe did not consistently resolve the separate
service environment. Its missing-import findings were recorded as environment
false positives only after the dedicated Pyright project passed and subprocess
startup resolved the local quarantine module. No inline diagnostic suppression
was added to hide those imports.

## Adversarial review (Sol 6.1)

A separate review model attacked the release contract with source changes
forbidden. It added 172 cases in `tests/test_adversarial_sol.py`. Ten failed on
real defects, which were then fixed:

- a comment-only command raised an uncaught parser error;
- globs in redirection targets passed validation;
- the Agent accepted HTTP 201, 202 and 302 as approval;
- a 307 redirect made the Agent forward the API key to another origin;
- malformed nested audit rows produced a 500 dashboard instead of 503;
- unsupported forensic shell syntax was labelled green from the tool name.

The full suite now passes with 354 tests. This review used only the offline
harness; it did not prove sandbox behaviour, container effects or model accuracy.

## Container verification in a disposable VM

The development host has no Docker installation, so the published commit
`9f68090` was cloned inside a disposable Ubuntu 24.04 cloud VM with KVM
acceleration, 4 vCPU, 6 GiB RAM and a 24 GiB overlay disk. Test credentials were
generated inside the VM; no real secrets or workspaces were used.

Observed:

- Docker 29.1.3 and Compose 2.40.3.
- `guardian`, `agent` and `ui` built from the documented contexts.
- `docker compose up -d --build --wait` reached healthy for all three services.
- Containers ran as `1000:1000`. Limits applied: 512 MiB and 0.5 CPU for
  Guardian, 1 GiB and 0.75 CPU for Agent, 256 MiB and 0.25 CPU for UI.
- Published ports listened on `127.0.0.1` only.
- Health returned 200 on 5000, 5001 and 8081. The UI root returned 401 without
  credentials and 200 with them, showing audit rows retrieved through Guardian.
- `/validate` approved `ls /tmp` through mapping. System One was unavailable with
  a connection error in 3.21 ms and the decision stayed unchanged. A chain ending
  in `curl` was rejected by mapping.
- `scripts/verify_logs.py` reported a valid chain, 2 signed rows, 0 unsigned
  legacy rows and no errors.
- `/report` returned 200, an identical repeat 200, and a conflicting command 409.
- After a Guardian restart the audit rows persisted.
- The optional `system-one` profile build stopped at the qualification gate with
  the documented reason, before installing dependencies.

Not measured: load behavior, long-running stability, real command execution and
model inference. The VM and its disk were stopped and retained outside the
repository.

## Dependency audit and explicit exclusions

`pip-audit` inspected the installed Python 3.11 application environment. Vulnerable
Flask, Requests and pytest versions were updated to 3.1.3, 2.33.0 and 9.0.3.
pytest is now a development dependency, not a Guardian image requirement.
The installed model environment's setuptools was upgraded to 83.0.0.

The model-environment scan returned no findings for the packages it recognized,
but **skipped** the source-installed Kev project and `torch==2.8.0+cpu`. This was
not accepted as a clean model-runtime result. An explicit base-version lookup
found eight PyTorch advisories; see [System One](SYSTEM_ONE.md). A separate
2.13.0 lookup returned no current findings, but Kev requires `torch>=2.6,<2.9`.
No unsupported override was made. The candidate is quarantined in bootstrap,
service startup and Docker dependency installation through one source gate.

The lock's direct hashed CPU wheel also fixed a reproduced uv multi-index
resolution failure: an extra CPU index exposed old unrelated package versions
before PyPI. The corrected historical lock resolves without weakening uv's
index-confusion protections. It is retained for reproducibility, not deployment.

These are advisory-database results for the inspected environments, not a complete
code audit, model-weight audit or a guarantee about future image resolutions.
Kev source provenance is pinned and hashed but is not comprehensively audited.
Base images and the complete built container contents were not scanned locally.

## Real CPU experiment, before quarantine

A temporary authenticated loopback service loaded the pinned Kev 0.8B model on
CPU and was stopped after evaluation. It did not execute candidate commands.
The saved reports contain these results:

- Calibration: 8/8 observations, **0/8 within the unchanged 500 ms budget**.
- End-to-end p50: **2,962.905 ms**; p95: **3,117.18 ms**.
- Mean per-question Brier: **0.228625120625** on the small synthetic calibration set.
- Separate smoke case: harmless listing received transfer-risk probability 0.7006.
- No threshold selected, no held-out test results claimed, enforcement disabled.

Reports remain ignored at `state/evaluations/cpu-smoke.json` and
`state/evaluations/cpu-calibration.json`. The model release tag is not an immutable
weight digest; a promoted candidate must freeze stronger artifact provenance and
repeat evaluation. The recorded local runtime is no longer permitted to start.

## Outstanding checks and ownership

| Blocker/limit | Practical next step | Owner |
| --- | --- | --- |
| Target-host deployment | Repeat the smoke check on the intended host, then verify backups, UID/GID ownership and recovery there | Deployment owner |
| Kev/PyTorch security incompatibility | Obtain a compatible patched upstream release or choose another licensed/privacy-reviewed backend; audit, test and requalify before clearing the startup gate | Integration maintainer, with upstream dependency support |
| CPU latency and unreliable scores | Benchmark the reviewed replacement/hardware on independent labelled calibration and untouched held-out workloads; do not loosen thresholds merely to pass | Evaluation owner |
| No production sandbox or durable exactly-once executor | Supply and verify OS-level isolation and recovery semantics before any real untrusted execution | Deployment/security owner |

The GitHub workflow pins actions by commit and includes ordinary-service Compose
smoke checks. It completed successfully at `9f68090`, so the container check ran
independently on GitHub runners as well. It cannot verify model inference, and a
target host still needs its own deployment check.
