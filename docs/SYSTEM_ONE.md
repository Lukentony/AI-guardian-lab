# Experimental System One observer

## Status and purpose

The observer records a contextual assessment after deterministic checks and
before any required L4 review. It cannot change the command or its authorization,
skip L4, promote policy, train itself or execute tools. Configuration accepts only
`off` and `shadow`; `enforce` is rejected.

The bundled Kev CPU service is now qualified for **shadow-only** use on
torch 2.13.0+cpu. It is a separate optional service, not part of the default
three-container demo. The full profile starts it and a local reviewer, and is
measurably slower than the demo. Qualification here means the pinned runtime
starts and answers; it does not establish detection efficacy.

Four independent typed questions assess task coherence, unauthorized transfer,
following untrusted instructions and missing evidence. Questions have a SHA-256
fingerprint. Each inference records the requested and returned model, question
version, context trust label, probabilities, latency and availability in the signed
audit metadata. Those probabilities still need calibration against labelled data.

## Local-only design

`guardian/config/system_one.yaml` defaults to shadow mode and a 500 ms budget.
The full profile sets `SYSTEM_ONE_TIMEOUT_SECONDS=2.0`; the validation request
waits for the observer, so the full profile is intentionally slower. The accepted
range is 0.05 to 5 seconds. Keep 0.5 for the default path.

Compose points it at a private optional service; no service means an explicit
`unavailable` observation, not a safety verdict. `mode: "off"` avoids inference.
Quote `off` in YAML: unquoted `off` is parsed as a Boolean and rejected.
There is no hosted fallback. Redirects and environment proxies are disabled.
Only fixed local names, loopback or private IPv4 network endpoints are accepted.
Do not point it at an untrusted private service: it receives task context.

The optional CPU service runs separately from Guardian's 512 MiB container. It
has a dedicated key, no shell tools, no workspace/audit mounts and one admitted
model job. A client disconnect does not admit more work until that job finishes.
The service warms the model before `/health` becomes ready, so the first real
request does not pay the cold-start cost.
HTTP body limits and Uvicorn admission bounds also apply. Model files are cached
separately; no implicit Hugging Face token or telemetry is used. Two threads are
the old conservative default; the qualified profile uses eight through
`SYSTEM_ONE_THREADS`.

Kev source is pinned to `1f04cfa28e6a708485b28a9585010b9e436b776e`, with archive
SHA-256 `3d0230dbc5c6155cf6a0933696998a9ad6942754a2af1a95c88bf23e1d2cc631`.
The CPU service loads `jaredpalmer/kev-0.8b@v1.0`. The dependency lock records
CPython 3.13 on Linux x86_64 with CPU PyTorch 2.13.0. This Kev project is
unrelated to the PyPI ORM with the same name. Upstream Kev uses Apache-2.0;
retain its notices when distributing it.

Kev metadata still declares `torch>=2.6,<2.9`. The image installs torch first,
then the pinned set, then Kev with `--no-deps`; the metadata cap therefore cannot
silently replace the reviewed runtime. `system-one/qualification.py` verifies the
installed torch and Kev versions at image build and service startup.

SecJev remains a research comparison candidate, not an integrated dependency.
Its custom agreement and upstream data terms need review before adoption.
Hosted Jev would additionally require an explicit privacy/provider decision.

## Measured qualification

The eight-case calibration set was run against the real local service without
executing any candidate shell command. The reports used a 10 s diagnostic
timeout; the configured full-profile request budget is 2 s, used separately by
`demo --full`. The model ran on CPU with eight threads and the prefix cache
enabled.

| Calibration measurement | Result |
| --- | --- |
| Observed cases | 8/8 |
| Below 2 s in the latency comparison | 8/8 |
| Within the unchanged 500 ms default budget | 0/8 |
| End-to-end p50 | 1,214.625 ms |
| End-to-end p95 | 1,289.89 ms |
| Mean per-question Brier score | 0.228625120625 |

The 0.8B CPU candidate does not meet the 500 ms default. The default stays
`shadow` with a 500 ms timeout and will often record `unavailable`; that is an
honest outcome, not a safety verdict. The full profile uses a 2-second budget
because it is a slower demonstration, not a production claim. Enforcement stays
disabled. A faster backend, GPU deployment or a smaller model must earn its own
qualification.

The calibration set is small and handcrafted; it does not measure real-world
detection rates. A separate two-case smoke test gave harmless `ls` a misleading
probability. No threshold was selected and the held-out test set was not used to
fit one. Raw local reports are under ignored `state/evaluations/`; they are not
required for routine unit tests.

## Startup gate

`system-one/qualification.py` is the single startup gate. It requires exactly
`torch 2.13.0` and `Kev 0.1.0`, and runs before the service imports
torch, loads weights, downloads files or opens a socket. There is no environment
variable bypass. The image runs the gate after installing dependencies; the
bootstrap runs it after creating the isolated environment.

The installed-environment audit was run with `pip-audit` against torch 2.13.0
and the pinned lock. It reported no known vulnerabilities for either. The old
torch 2.8.0 set had eight advisories, including local memory-corruption and
checkpoint-loading issues; that set is no longer the qualified runtime. Kev is
not published on PyPI, so the auditor skips it; the source archive is pinned by
SHA-256 and the package is reviewed separately. Setuptools is pinned to 83.0.0
in the lock.

This qualification is specific to the pinned versions. An upstream change,
a different torch build, a new model or a different platform requires a fresh
audit and a new evaluation.

## Full profile

```bash
./guardian-lab setup --profile full
./guardian-lab models
./guardian-lab doctor
./guardian-lab demo --full
```

The full profile starts Guardian, Agent, UI, Ollama and System One. `models`
pulls the configured local models. `demo --full` runs deterministic allow and
block cases, one semantic-review case, one forensics analysis and one dry-run
Agent request. Nothing is executed. The default ports remain loopback-only.

The full profile uses `qwen2.5:3b` for L4 and forensics, and
`qwen2.5-coder:3b` for the Agent. These are demonstration models chosen for a
CPU/laptop installation, not a quality benchmark. A larger local model can be
configured, but it must fit the host and the semantic timeout.

## Evaluation workflow

Use a separate terminal at the repository root while its model process runs, and
supply its dedicated key securely to the evaluator.

```bash
.venv/bin/python scripts/evaluate_system_one.py \
  --split calibration \
  --measurement-timeout 10 \
  --output state/evaluations/new-calibration.json
```

The longer timeout collects diagnostic probabilities but does not change the
reported budget. Outputs are exclusive-create to preserve previous results.
Exit 2 means incomplete observations. Service errors are unavailable cases, not
successful detections. The baseline is evaluated without any live
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
The full profile does not enable enforcement and does not make the observer a
security boundary.
