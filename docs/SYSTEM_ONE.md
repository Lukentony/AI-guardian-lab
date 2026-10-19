# Experimental System One observer

## Status and purpose

The observer records a contextual assessment after deterministic checks and
before any required L4 review. It cannot change the command or its authorization,
skip L4, promote policy, train itself or execute tools. Configuration accepts only
`off` and `shadow`; `enforce` is rejected.

**The bundled Kev CPU service is quarantined.** Its dependency constraint conflicts
with security updates. The shadow client is separate and can use a reviewed,
compatible local backend.

Four independent typed questions assess task coherence, unauthorized transfer,
following untrusted instructions and missing evidence. Questions have a SHA-256
fingerprint. Each inference records the requested and returned model, question
version, context trust label, probabilities, latency and availability in the signed
audit metadata. Those probabilities still need calibration against labelled data.

## Local-only design

`guardian/config/system_one.yaml` defaults to shadow mode and a 500 ms budget.
Compose points it at a private optional service; no service means an explicit
`unavailable` observation, not a safety verdict. `mode: "off"` avoids inference.
Quote `off` in YAML: unquoted `off` is parsed as a Boolean and rejected.
There is no hosted fallback. Redirects and environment proxies are disabled.
Only fixed local names, loopback or private IPv4 network endpoints are accepted.
Do not point it at an untrusted private service: it receives task context.

The optional CPU service runs separately from Guardian's 512 MiB container. It
has a dedicated key, no shell tools, no workspace/audit mounts and one admitted
model job. A client disconnect does not admit more work until that job finishes.
HTTP body limits and Uvicorn admission bounds also apply. Model files are cached
separately; no implicit Hugging Face token or telemetry is used.

Kev source is pinned to `1f04cfa28e6a708485b28a9585010b9e436b776e`, with archive
SHA-256 `3d0230dbc5c6155cf6a0933696998a9ad6942754a2af1a95c88bf23e1d2cc631`.
The CPU service loads `jaredpalmer/kev-0.8b@v1.0`. The separate dependency lock
records CPython 3.13 on Linux x86_64 with CPU PyTorch 2.8.0. This Kev project is
unrelated to the PyPI ORM with the same name. Upstream Kev uses Apache-2.0;
retain its notices when distributing it.

SecJev remains a research comparison candidate, not an integrated dependency.
Its custom agreement and upstream data terms need review before adoption.
Hosted Jev would additionally require an explicit privacy/provider decision.

## Measured qualification: not passed

A real local CPU smoke test and the eight-case calibration set were run without
executing any candidate shell command. With a longer **measurement-only** timeout:

| Calibration measurement | Result |
| --- | --- |
| Observed cases | 8/8 |
| Within unchanged 500 ms runtime budget | 0/8 |
| End-to-end p50 | 2,962.905 ms |
| End-to-end p95 | 3,117.18 ms |
| Mean per-question Brier score | 0.228625120625 |

The calibration set is small and handcrafted; it does not measure real-world
detection rates. A separate two-case smoke test gave harmless `ls` an
unauthorized-transfer probability of 0.7006. No threshold was selected and the
held-out test set was not evaluated. Enforcement stayed disabled.

The 0.8B CPU candidate fails the current latency requirement. Keep the budget and
acceptance criteria fixed when evaluating a replacement rather than adjusting
them to fit these results.

Raw local reports are under ignored `state/evaluations/`; they are not required
for routine unit tests. GPU/ROCm performance and larger models were not measured.
A new candidate or hardware-specific deployment must earn its own qualification.

## Startup quarantine: dependency security blocker

The installed-environment auditor skipped `torch==2.8.0+cpu` because that exact
local-version identifier is not on PyPI. A separate explicit lookup of the base
`torch==2.8.0` exposed **eight advisories**:

- PYSEC-2025-206, PYSEC-2025-204, PYSEC-2025-203
- PYSEC-2025-193, PYSEC-2025-194, PYSEC-2025-195
- PYSEC-2026-139, PYSEC-2026-2286

These include local memory-corruption and checkpoint-loading issues; this is not
a claim that every advisory is remotely reachable through the adapter. The
installed Kev metadata requires `torch>=2.6,<2.9`, while reported fixes extend
through 2.13.0. A separate advisory lookup of 2.13.0 returned no current findings,
but that does **not** establish Kev compatibility or justify overriding its cap.
No such override or Torch upgrade was performed.

`system-one/qualification.py` is the single startup gate. It rejects bootstrap,
service startup and image dependency installation before inference can run. There
is no environment-variable bypass. The historical lock and stopped local runtime
are retained for reproducibility, not approved for deployment. Baseline Guardian
and the shadow client do not import this runtime and continue independently.

On this development computer, in a dedicated terminal at the repository root,
the following diagnostic is expected to exit nonzero with the quarantine reason:

```bash
python3 system-one/qualification.py
```

The integration maintainer needs a compatible patched Kev release or another
reviewed local backend. Its full dependency set must be resolved and audited
before qualification is repeated. Keep the startup gate closed until that work
passes; building an image is not enough. SecJev adoption or hosted inference needs its own
license/privacy decision. The optional profile is never started by the installer.
Its image build was checked in a disposable VM and stops at the qualification gate
before installing the quarantined dependencies.

## Evaluation workflow

This workflow is prepared for a **future reviewed, compatible backend**, not an
instruction to bypass the current quarantine. Once that backend is authorized,
use a separate terminal at the repository root while its model process runs, and
supply its dedicated key securely to the evaluator.

```bash
.venv/bin/python scripts/evaluate_system_one.py \
  --split calibration \
  --measurement-timeout 10 \
  --output state/evaluations/new-calibration.json
```

The longer timeout collects diagnostic probabilities but does **not** change the
reported production budget. Outputs are exclusive-create to preserve previous
results. Exit 2 means incomplete observations. Service errors are unavailable
cases, not successful detections. The baseline is evaluated without any live
command-generating LLM, using a temporary database; no commands are executed.

Calibration and test data each contain eight labelled cases in disjoint scenario
pairs. This prevents exact pair/group overlap, not all semantic overlap or model
training contamination. Include independently reviewed real workloads, Italian
and English tasks, new attack families and held-out sessions before deployment.
The per-question labels are explicit references, not the observer's own verdicts.

Only after separately selecting a candidate and calibrating a threshold should
the untouched test split be evaluated. `--threshold` is optional offline analysis;
it never edits runtime settings. Its max-component risk aggregation is not a
calibrated joint probability. Freeze the model, rubric, thresholds and datasets;
report false approvals, false blocks, review/unavailable rate and end-to-end p95.

Promotion requires no deterministic-block reversals, acceptable false-approval
risk and calibration, bounded resource behavior, trusted context and a measured
latency budget. Sandbox integration and explicit rollout approval are separate.
