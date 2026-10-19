# Deployment

The lab is for local research. Real execution still needs an OS-level sandbox;
the supplied containers do not provide one. The optional Kev model service is
quarantined because of a dependency security conflict.

Use [Install](INSTALL.md) for first installation or upgrade. It covers credentials,
Compose build contexts, state-directory ownership and audit migration. Follow it
on the chosen host from a dedicated terminal at the repository root. Do not rerun
the installer over an existing `.env`.

## Before starting services

- Back up existing configuration, audit state and its signing key.
- Match `LOCAL_UID` and `LOCAL_GID` to the owner of the state directories.
- Keep the published ports on loopback. Remote access needs a separately reviewed
  authenticated TLS endpoint.
- Leave `EXECUTE_COMMANDS=false` unless execution and isolation have been approved.

Compose manages the `agent-net` network. Do not create a separate network by hand
to work around a failed startup. Inspect the error and correct its cause.

## Verification and recovery

The ordinary-service stack was built and started in a disposable Ubuntu 24.04 VM
with Docker 29.1.3 and Compose 2.40.3. All health checks passed, the UI returned
401 without credentials, the audit chain verified and state survived a restart.
A target-host check is still required before deployment.

[Verification](VERIFICATION.md) records what has actually passed.
[Architecture](../ARCHITETTURA.md) describes network boundaries and recovery limits.
