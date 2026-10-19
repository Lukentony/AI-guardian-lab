# Contributing

AI Guardian Lab is a personal project by Luca Rivoiro
([Lukentony](https://github.com/Lukentony)). Open an issue before starting a
substantial change so its scope can be agreed first. Report vulnerabilities
privately, as described in [Security](SECURITY.md).

## Changes and attribution

Keep changes small enough to review and include tests for changed behavior.
Local use must not acquire a mandatory cloud dependency. Any hosted inference
needs an explicit configuration and privacy decision.

For Luca's tool-assisted work, use his Git identity. AI assistants and automation
are tools, not project co-authors; do not add assistant or bot `Co-authored-by`
trailers. This does not authorize attributing another person's work to Luca.
Preserve dependency licenses and required third-party notices.

Use a short commit message with a `fix:`, `feat:`, `docs:` or `chore:` prefix.
Explain the change rather than adding a slogan or a generated summary.

## Tests

On your development machine, open a dedicated terminal at the repository root.
Prepare the Python environment using [Install](INSTALL.md#development-checks-without-docker),
then run:

```bash
.venv/bin/python -m pytest
```

Tests must pass before a change is merged. The suite uses temporary state and
mocked model calls; do not replace them with live services in routine tests.
See [Verification](VERIFICATION.md) for type checks and the remaining Docker checks.
