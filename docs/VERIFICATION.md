# Verification record: hardening, onboarding and interface

## 1.6.0 full-profile verification

Scope: branch `feature/full-stack`, based on `7f3a2d6`. This is not a production
approval. Model-based enforcement remains disabled and no remote deployment was
performed.

| Check | Observed result |
| --- | --- |
| Complete offline pytest suite | **391 passed**, no skips |
| Application/scripts/tests/onboarding Pyright | 0 errors, 0 warnings |
| Separate model-service Pyright project | 0 errors, 0 warnings |
| Ruff on runtime surfaces, onboarding and tests | Passed |
| System One runtime | Kev 0.8B on CPU torch 2.13.0, eight threads, prefix cache |
| Calibration at the full-profile 2 s budget | 8/8 observed; p50 **1,214.625 ms**; p95 **1,289.89 ms** |
| Calibration at the unchanged 500 ms default | 0/8 |
| Mean per-question Brier score | **0.228625120625** on the handcrafted set |
| `pip-audit` against torch 2.13.0 and the hashed lock | No known vulnerabilities |
| Native full stack: Guardian, Agent, UI, Ollama, System One | All health checks passed |
| Three `/validate` cases | Allow, block and semantic review all matched; System One was `observed` on the two non-baseline cases |
| Agent dry-run | `simulated`; no command executed |
| Forensics | `analysis_complete=true` with the local model |
| Audit after the three cases | +3 decisions; chain verifier reported 15 signed rows and no errors |
| UI authentication | 401 without credentials, 200 with credentials |
| `guardian-lab demo --full` orchestration | PASS against the native stack and PASS again in the Docker VM |
| Full-profile Docker build and VM run | PASS in the disposable Ubuntu 24.04 VM; five services healthy, models present, demo 3/3 |
| System One container runtime | Python 3.13.17, torch **2.13.0+cpu**, Kev health observable |

The native stack used `qwen2.5:3b` for semantic review and forensics and
`qwen2.5-coder:3b` for the Agent, with System One on the pinned Kev checkpoint.
The full demo's `check_models` and `check_system_one` functions were replaced by
successful checks for that native run; the underlying HTTP services and model
calls were exercised directly.

The same source tree was then copied to the disposable Ubuntu 24.04 VM. Docker
29.1.3 and Compose 2.40.3 built the System One image (torch 2.13.0+cpu, Kev
pinned), pulled `ollama/ollama:0.40.8`, and reached healthy for Guardian, Agent,
UI, Ollama and System One. `guardian-lab models` pulled both 3B models;
`guardian-lab doctor` reported every check ok, including the observer endpoint;
`guardian-lab demo --full` passed 3/3 cases with a valid chain. The Agent ran in
dry-run and the audit showed no `executed` rows.

The first Docker run exposed two integration defects:

1. `doctor` defaulted to the demo profile and skipped models and System One even
   when `.env` said `full`. It now reads `GUARDIAN_PROFILE` unless the flag
   overrides it.
2. Compose hard-coded `INTENT_LLM_TIMEOUT_SECONDS=2`, overriding the full-profile
   value of 30. The semantic case therefore failed as `llm_error`. Compose now
   interpolates the setting.
3. The CLI demo's validation POST used a 15 s client timeout. On the CPU-only VM
   the semantic case exceeded it and appeared as `Guardian is unreachable`. The
   validation request now uses a bounded 120 s timeout; Guardian itself keeps
   its own 30 s semantic timeout.

All fixes were applied and the full demo was rerun successfully. The published
1.6.0 release archive and GHCR release images were not built in this session;
the source build above is the verified path.

The historical 1.5.0 record follows. It is retained for context; its quarantine
statements describe the previous torch 2.8 candidate, not this release.

Scope: release 1.5.0, published from branch `feature/system-one-hardening` and
based on `15b6f6672a6a12546e25e795d66a91919c93f02f`. This is not a production
approval. Model-based enforcement remains disabled and no remote deployment was
performed.

## Executed checks

| Check | Observed result |
| --- | --- |
| Complete offline pytest suite | **381 passed** (354 prior, 27 onboarding/forensics/audit/UI regression), no skips |
| Application/scripts/tests/onboarding Pyright | 0 errors, 0 warnings |
| Separate model-service Pyright project | 0 errors, 0 warnings |
| Ruff on runtime surfaces, onboarding and model service | Passed |
| Installer and release-package Bash syntax | Passed |
| Headless UI review at 1440 and 390 | Dashboard, demo, status and forensics inspected |
| Entrypoint/bootstrap/config-check POSIX shell syntax | Passed |
| `git diff --check` | Passed |
| Installed application-environment dependency audit | No known advisories reported |
| Model dependency lock resolution, reinstall dry-run | Resolved 70 packages; no installation performed by that check |
| Model service/bootstrap quarantine subprocess checks | Refused before model imports/downloads or socket startup |
| Container build and startup in a disposable Ubuntu 24.04 VM | 3 images built; all services healthy |
| UI authentication, audit API, chain verifier, restart persistence | Passed; details below |
| GitHub Actions CI at 9f68090 (1.3.1) | Completed successfully |
| GitHub Actions CI at 80a5325 (PR #4) | Test and onboarding jobs passed |
| GitHub Actions CI at 8333c01 (PR #5) | Test and onboarding jobs passed |
| GitHub Actions CI at 995a1eb (main) | Passed |
| Release workflow v1.5.0 | Test, three images and bundle passed |

The following checks ran from the repository root on the development machine,
in the coding session's own process:

```bash
.venv/bin/python -m pytest -q
.venv/bin/pyright guardian database agent ui scripts tests tools
.venv/bin/pyright -p system-one
.venv/bin/ruff check guardian database agent ui tools \
  scripts/evaluate_system_one.py scripts/pattern_learner.py \
  scripts/verify_logs.py system-one
bash -n install.sh scripts/package_release.sh
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

Onboarding tests cover .env parsing and duplicate rejection, distinct credential
validation, private atomic writes without printing secrets, port occupancy, the
five-case demo contract against a fake Guardian, image-only Compose handling and
the audit concurrency regression. The audit tests reproduce concurrent startup on
a fresh database and a transient exclusive lock.

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

## 1.4.0 onboarding verification

The first-run path was tested from a clean clone at `ae8a8fa` in the same
disposable VM. `setup` created a private `.env`; the first `demo` built and
started the three services. That run exposed a real startup race: two Gunicorn
workers enabled WAL on a fresh database at the same time and one failed with
`database is locked`, so Compose declared Guardian unhealthy. `init_db` now
retries the journal-mode switch, with concurrent-startup and transient-lock
regression tests.

The repeated run passed: five of five decisions, +5 audit rows, a valid 5-row
chain and UI 401/200. `doctor` reported every check ok. A second
`demo --no-start` passed and grew the chain to 10 signed rows. Containers ran as
`1000:1000`; ports were loopback-only. `doctor --probe-models` reported the
missing Ollama endpoint as a warning in the demo profile. The release Compose
file passed `docker compose config --quiet`. The release archive built locally,
its `SHA256SUMS` verified, and the packaged CLI started; GHCR publication and the
archive upload happen in the tag workflow and were not exercised locally.
Incomplete forensic analysis now yields `analysis_complete=false`, an
UNAVAILABLE card and a summary that does not claim a clean session.

The pull-request CI result passed on PR #4 at `80a5325`: both the offline test job
and the onboarding job (setup, image build, doctor, demo) completed. The local
suite, Pyright and Ruff commands above passed before that run.

## 1.5.0 interface verification

The browser interface was rebuilt and checked with the Flask test client and
headless Chromium.

- Dashboard, demo, status and forensics require Basic authentication; `/health`
  remains public.
- The demo endpoint runs the five fixed cases through a mocked Guardian, adds five
  audit rows, rejects cross-origin POSTs and has no executor call. The UI cases
  are compared with the CLI cases by a regression test.
- The status page renders both healthy and unavailable backends without failing
  the page itself. It reports only what the UI can reach; Docker and model checks
  remain in `guardian-lab doctor`.
- The dashboard accepts the new `intent_source` field and still rejects malformed
  nested rows with 503.
- The layout was inspected at 1440x1100 and 390x844. The mobile decisions table
  stays inside its horizontal scroller; the page itself does not overflow.
- The stylesheet and icons are local. No CDN, external font or new frontend
  framework is used.
- No visual-regression tool was used; the review is manual and does not replace a
  usability test with external users.
- GitHub Actions CI passed on PR #5 at `8333c01`, including the onboarding job
  that builds the new UI image.

## 1.5.0 release archive verification

The published archive was downloaded in the disposable Ubuntu 24.04 VM and run
with the published images:

- the outer SHA-256 and the internal `SHA256SUMS` both verified;
- `setup` and `demo` pulled the 1.5.0 images and returned 5/5, +5 audit rows and
  a valid 5-row chain;
- `/`, `/demo`, `/status`, `/forensics` and `/static/app.css` returned 200 with
  Basic authentication and displayed `v1.5.0`;
- the UI demo endpoint returned 5/5 and +5 audit rows; `doctor` then reported 10
  signed rows;
- containers ran as `1000:1000` with loopback-only ports.

This check used the published archive, not the source checkout. It did not run
real commands, model inference or a browser accessibility audit.

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

At that point the full suite passed with 354 tests; the current suite adds
onboarding, concurrency and incomplete-analysis cases. This review used only the
offline harness; it did not prove sandbox behaviour, container effects or model
accuracy.

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
| Full-profile Docker build and VM run | Build the System One image, start the full profile, pull the models and repeat `demo --full` in a disposable Docker host | Integration maintainer |
| CPU latency and unreliable scores | The 2 s full-profile budget is qualified for shadow use; the 500 ms default still fails. Benchmark on independent labelled calibration and untouched held-out workloads; do not loosen thresholds merely to pass | Evaluation owner |
| No production sandbox or durable exactly-once executor | Supply and verify OS-level isolation and recovery semantics before any real untrusted execution | Deployment/security owner |

The GitHub workflow pins actions by commit and includes ordinary-service Compose
smoke checks. It completed successfully at `9f68090`, so the container check ran
independently on GitHub runners as well; the 1.4.0 onboarding job also passed at
`80a5325`. It cannot verify model inference, and a target host still needs its
own deployment check.
