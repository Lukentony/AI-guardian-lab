# Security

AI Guardian Lab validates commands for cooperating executors. It is a research
project, not a sandbox. Keep real execution disabled for untrusted workloads.

## Reporting a vulnerability

Do not include credentials, private tasks or working exploit details in a public
issue. Use GitHub's private vulnerability reporting for this repository if it is
enabled. Otherwise, contact the maintainer privately to agree on a channel before
sending sensitive material. This checkout does not establish which private
reporting channel is currently available.

Include the affected revision and a minimal reproduction in an isolated
environment. State whether the command was merely validated or actually executed.

## Controls in this revision

- Guardian and Agent authenticate API requests; only health checks are public.
  Task registration and pattern approval need a separate operator credential.
- The shell parser rejects unsupported syntax. The allowlist checks every
  executable, and regex timeouts deny rather than silently dropping a pattern.
- Task mapping accounts for chains and redirections. Required semantic review
  rejects missing, malformed or uncertain replies.
- Audit decisions are signed in a transactional HMAC chain. Approval and execution
  outcomes are recorded separately.
- Compose restricts host exposure to loopback by default. The UI authenticates
  users and holds its backend credential server-side.

Implementation details are in [Architecture](../ARCHITETTURA.md). Results are in
[Verification](VERIFICATION.md); configured controls should not be mistaken for
container checks that have already run.

## Known limits

An executor can bypass Guardian if it has independent OS access. Integrations
need a pre-execution hook, not a prompt asking the model to call the API. Command
and task classification do not provide complete filesystem or network isolation.

A model's willingness to refuse a dangerous prompt is not a security boundary.
System One is shadow-only. Its bundled Kev candidate is quarantined because of
PyTorch advisories and an incompatible dependency constraint; it also failed the
CPU latency qualification. See [System One](SYSTEM_ONE.md).

Signing does not encrypt the database or protect a stolen key. Detecting deletion
of a valid log suffix requires a trusted external checkpoint. Outcome reporting
assumes an honest executor and does not guarantee exactly-once execution.

## Operating precautions

Keep secrets out of task text and logs. Preserve the audit signing key with a
consistent database backup; rotating it without a migration plan prevents old
signatures from verifying. Review learned patterns before promotion. Use a shared
rate-limit store if limits must apply across workers.

Do not expose APIs to bypass another framework's SSRF protection. Review remote
access, hosted-model privacy and an OS-level sandbox separately before deployment.
