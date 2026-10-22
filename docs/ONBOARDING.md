# Onboarding: from download to a working demo

This path exists for someone who has never seen the project. The goal is a
working demonstration in minutes, without reading the architecture first and
without downloading a language model.

The demo validates commands. It never executes them.

## Requirements

- Linux on x86_64, or macOS with Docker Desktop for the experimental path.
- Docker Engine and the Compose v2 plugin, with `--wait` support.
- A non-root account allowed to use Docker.
- Ports 5000, 5001 and 8081 free on loopback.
- `curl` and Python 3 for the local launcher.

The release images are published for `linux/amd64`. ARM64 is not published yet.

## From a release archive

Download `ai-guardian-lab-<version>.tar.gz` and its `.sha256` file from the
GitHub release page. Verify the archive before unpacking:

```bash
sha256sum -c ai-guardian-lab-<version>.tar.gz.sha256
tar -xzf ai-guardian-lab-<version>.tar.gz
cd ai-guardian-lab-<version>
./guardian-lab setup --profile demo
./guardian-lab doctor
./guardian-lab demo
```

`setup` writes a private `.env` with fresh, distinct credentials, creates
`state/audit` and `state/learned`, and starts the published images. The first
run pulls the images; it does not build anything locally.

`demo` prints five decisions, the audit delta and the chain result. Open
`http://127.0.0.1:8081` and use the username and password from `.env`. Both
dashboards and the forensics page work with the rows created by the demo.

## From the repository

The same commands work from a checkout. Compose builds the images locally, so
the first run takes longer:

```bash
git clone https://github.com/Lukentony/AI-guardian-lab.git
cd AI-guardian-lab
./guardian-lab setup --profile demo
./guardian-lab demo
```

The older interactive `install.sh` is legacy; the supported full profile uses `guardian-lab`.
`guardian-lab` is the shorter and stricter path for a first test.

## What the demo proves

| Case | Command | Expected | Why |
| --- | --- | --- | --- |
| allowed listing | `ls /tmp` | allow | Read-only command consistent with the task |
| red-zone binary | `rm LICENSE` | block | Executable outside the allowlist |
| undeclared write | `cat README.md > /tmp/readme-copy` | block | The redirection conflicts with a read-only task |
| glob in redirect | `echo ok > /tmp/?` | block | The parser rejects globs in redirection targets |
| comment-only input | `# comment only` | block | Unsupported or malformed shell syntax |

The demo then checks that five decisions were appended to the signed audit and
that the UI rejects anonymous access. It fails with a non-zero exit code if any
expected decision changes.

The default demo does not prove model generation, semantic review quality,
command execution, sandbox isolation or real detection accuracy. The full
profile exercises the model and observer paths, but its small models are not a
quality benchmark and nothing is executed.

## Browser interface

Open `http://127.0.0.1:8081` after the demo. The dashboard shows the signed
decisions and links to:

- **Control room**: a live decision trace with six scenes, observer evidence
  and the signed receipt, using the same authenticated path as the API.
- **Demo**: the same five cases as the CLI, with a short cooldown and no
  execution. Each click appends five records.
- **Forensics**: paste or upload an OpenHands or SWE-agent transcript.
- **Status**: Guardian, Agent and audit reachability. It does not check Docker,
  llama.cpp or the signing key; use `guardian-lab doctor` for those.

The interface is read-only apart from the demo and forensics POSTs. It has no
command execution, no Docker socket and no database mount.

## Profiles

- `demo` keeps `EXECUTE_COMMANDS=false` and requires no model. Ambiguous commands
  are denied because semantic review is unavailable. This is the intended first
  experience.
- `local-models` is retained for an externally managed OpenAI-compatible
  endpoint; it is not the supported full profile.
- `full` starts Guardian, Agent, UI, llama.cpp and System One. It uses one
  pinned `qwen2.5-3b-instruct` GGUF for semantic review, forensics and command
  generation. It needs about 16 GB of RAM, 8 CPU cores and 15 GB of free disk for
  images and the model. Commands are still never executed.

The full profile is local-only. A remote OpenAI-compatible endpoint can be
configured explicitly with `LLM_API_BASE` and `LLM_API_KEY`, but it sends task
and command text outside the host and is not a supported demo profile.

## Full profile

```bash
./guardian-lab setup --profile full
./guardian-lab models
./guardian-lab doctor
./guardian-lab demo --full
```

`setup` downloads and verifies the pinned GGUF before starting the stack; `models`
does the same explicitly and supports `--force`. The first download can take
several minutes. `doctor` then checks the GGUF, the llama.cpp endpoint and served
alias, the System One health endpoint, UI authentication, the audit API and the
chain.
`demo --full` runs deterministic allow and block cases, one semantic-review case,
one forensics analysis and one dry-run Agent request. It also verifies that the
observer recorded an actual observation rather than `unavailable`. The Agent
check accepts `simulated` or `rejected`: both prove the Agent-to-Guardian path,
but only `simulated` covers approval through simulation and outcome reporting.

The full profile uses a 2-second observer budget. The default 500 ms budget is
still too tight for the 0.8B CPU model, so the default demo records `unavailable`
instead of pretending the observer ran. The full profile is a demonstration, not
a production latency claim.

## Diagnostics

`guardian-lab doctor` checks configuration values, Docker, Compose `--wait`,
ports, state directories, the three services, UI authentication, the audit API
and the signature chain. In the full profile it also checks the pinned GGUF,
the llama.cpp endpoint and served alias, and the System One health endpoint.
`--json` prints the same checks with stable keys for scripts. Failures that block the demo return exit code 1;
configuration errors return 2.

`doctor` does not print secrets. Hints name the setting to fix, not its value.

## Connecting an executor

The integration contract is HTTP and small:

1. Send the exact command and an honest task description to `POST /validate`.
2. Treat only HTTP 200 with `"approved": true` as authorization.
3. Do not follow redirects with the API key.
4. Execute the same command that was validated, not a rewritten variant.
5. Report `simulated`, `executed` or `execution_error` to `POST /report` with the
   returned `validation_id`.
6. On an uncertain outcome, inspect before retrying. The lab does not provide
   exactly-once execution.

A pre-execution hook in the executor is the only useful integration. Asking a
model to call Guardian voluntarily is not enforcement.

## Support status

| Target | Status | Evidence or condition |
| --- | --- | --- |
| Ubuntu 24.04, Docker Engine | Supported for the lab | Container smoke test in a disposable VM |
| Debian with Docker Engine | Expected, verify first | Same userspace stack; no dedicated run yet |
| Fedora | Experimental | SELinux and bind-mount behaviour need a test |
| Arch | Best effort | Rolling packages increase variability |
| macOS with Docker Desktop | Experimental | File sharing, UID/GID and host networking differ |
| Windows with WSL2 | Experimental | Use a directory inside the Linux filesystem |
| ARM64 | Not published | No native image build or smoke test |
| Docker rootless | Experimental | UID mapping inside containers needs verification |
| Host with limited RAM | Demo only | Three services fit the declared limits; llama.cpp and the GGUF are separate |

Do not describe an untested target as supported. Docker Desktop runs a VM and
does not behave exactly like Docker Engine on the host.

## Troubleshooting

| Symptom | Check | What not to do |
| --- | --- | --- |
| `docker: command not found` | Install Docker Engine and the Compose plugin | Do not run the lab with sudo as a workaround |
| `port is occupied` | `ss -ltn` and stop the conflicting process | Do not move the API to `0.0.0.0` |
| `state/... not writable` | Compare `LOCAL_UID`/`LOCAL_GID` with `ls -ld state/audit state/learned` | Do not use `chmod 777` |
| UI returns 401 | Use the credentials in `.env` | Do not confuse the UI password with `API_KEY` |
| UI returns 503 | Check Guardian `/audit` and container logs | Do not mount SQLite into the UI |
| `doctor` says chain failed | Preserve the database and `LOG_HMAC_KEY`, then inspect | Do not regenerate the key or rewrite history |
| `doctor` says model missing | Pull the configured reviewer model or stay in `demo` | Do not enable a cloud fallback |
| `demo` reports a decision mismatch | Read the command, task and reason in the table | Do not weaken assertions or policy to make it pass |

Logs can contain command text. Review them before sharing.

## What "complete" means

On a supported host with Docker already installed, five people unfamiliar with
the project should each complete download, setup, doctor and demo in under fifteen
minutes, without assistance and without a local build. Record hardware and
network conditions; measure Docker installation separately. The model path is a
separate exercise with its own download time and requirements.

Current limits remain: no OS-level sandbox, no exactly-once execution, no
production multi-tenancy, and no measured real-world detection accuracy.
