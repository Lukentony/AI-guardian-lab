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

The older interactive `install.sh` remains available for the provider wizard.
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

It does not prove model generation, semantic review quality, command execution,
sandbox isolation or real detection accuracy.

## Profiles

- `demo` keeps `EXECUTE_COMMANDS=false` and requires no model. Ambiguous commands
  are denied because semantic review is unavailable. This is the intended first
  experience.
- `local-models` uses the same stack but treats the Ollama endpoint and the
  configured reviewer model as required checks in `guardian-lab doctor`.
  `setup` never downloads a model automatically.

To connect a local Ollama instance, edit `OLLAMA_URL`, `LLM_MODEL_CODER` and
`INTENT_LLM_MODEL` in `.env`, then run:

```bash
./guardian-lab doctor --probe-models
```

The probe checks that the Guardian container can reach the endpoint and that the
configured reviewer model is present. It does not send a generation request.

## Diagnostics

`guardian-lab doctor` checks configuration values, Docker, Compose `--wait`,
ports, state directories, the three services, UI authentication, the audit API
and the signature chain. `--json` prints the same checks with stable keys for
scripts. Failures that block the demo return exit code 1; configuration errors
return 2.

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
| Host with limited RAM | Demo only | Three services fit the declared limits; Ollama is separate |

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
