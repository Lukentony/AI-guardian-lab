# Runtime security policy

This page summarizes the current configuration. The actual rules live in
`guardian/config/policy.yaml` and the validator; this document does not override
them. See [Security](SECURITY.md) for reporting and known limits.

## Authorization

Guardian checks the restricted shell grammar, every executable, patterns and task
effects. Required semantic review must return a valid affirmative assessment.
A model cannot reverse a deterministic rejection. System One accepts only `off`
or `shadow` and has no authorization role.

Guardian and Agent require an API key outside their public health endpoints.
Registering a task or approving a learned pattern also requires the separate
operator key. Simulation is the default; real execution needs a registered task
and a matching workspace.

## Deployment boundaries

Compose configures non-root processes, resource limits and loopback-only host
ports. The UI requires Basic authentication and retrieves audit data through
Guardian; it does not mount SQLite. These settings still need Docker verification
on the target host and do not amount to a production sandbox.

Regex searches have a 50 ms engine timeout. Timeout or invalid pattern state
denies validation. Audit records use a transactional HMAC chain; redaction is
best-effort and storage is not encrypted.

The optional Kev CPU runtime is quarantined. Do not clear its startup gate until
a compatible patched dependency set has passed review and evaluation. Current
checks and remaining work are recorded in [Verification](VERIFICATION.md).
