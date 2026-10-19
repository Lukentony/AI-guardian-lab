# Verification record: hardening and System One

Scope: local branch `feature/system-one-hardening`, based on
`15b6f6672a6a12546e25e795d66a91919c93f02f`. This is not a production approval.
No GitHub publication, remote deployment or model-based enforcement was performed.

## Executed checks

| Check | Observed result |
| --- | --- |
| Complete offline pytest suite | **182 passed**, no skips or reported warnings |
| Application/scripts/tests Pyright | 0 errors, 0 warnings |
| Separate model-service Pyright project | 0 errors, 0 warnings |
| Ruff on changed runtime surfaces, including model service | Passed |
| Installer Bash syntax | Passed |
| Entrypoint/bootstrap/config-check POSIX shell syntax | Passed |
| `git diff --check` | Passed |
| Installed application-environment dependency audit | No known advisories reported |
| Model dependency lock resolution, reinstall dry-run | Resolved 70 packages; no installation performed by that check |
| Model service/bootstrap quarantine subprocess checks | Refused before model imports/downloads or socket startup |

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
These checks **do not** prove actual container startup or filesystem ownership.

The home-workspace language-server probe did not consistently resolve the separate
service environment. Its missing-import findings were recorded as environment
false positives only after the dedicated Pyright project passed and subprocess
startup resolved the local quarantine module. No inline diagnostic suppression
was added to hide those imports.

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
| Docker unavailable locally | On an authorized Docker-equipped test host, run the prepared ordinary-service Compose smoke workflow; verify image startup, UID/GID ownership, authenticated UI/API and persistent recovery | Deployment/test owner |
| Kev/PyTorch security incompatibility | Obtain a compatible patched upstream release or choose another licensed/privacy-reviewed backend; audit, test and requalify before clearing the startup gate | Integration maintainer, with upstream dependency support |
| CPU latency and unreliable scores | Benchmark the reviewed replacement/hardware on independent labelled calibration and untouched held-out workloads; do not loosen thresholds merely to pass | Evaluation owner |
| No production sandbox or durable exactly-once executor | Supply and verify OS-level isolation and recovery semantics before any real untrusted execution | Deployment/security owner |

The GitHub workflow now pins actions by commit and includes ordinary-service
Compose smoke checks. It has not run for this unpublished revision. Publishing
or deploying the branch still requires approval.
