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
Guardian; it does not mount SQLite. These settings were exercised in a
disposable VM and do not amount to a production sandbox. A target-host check
remains separate.

Regex searches have a 50 ms engine timeout. Timeout or invalid pattern state
denies validation. Audit records use a transactional HMAC chain; redaction is
best-effort and storage is not encrypted.

The optional Kev CPU runtime is qualified for shadow use on torch 2.13.0 and is
started only by the full profile. Do not change its gate, torch range or model
without a new review and evaluation. Current checks and remaining work are
recorded in [Verification](VERIFICATION.md).
