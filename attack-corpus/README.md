# Attack corpus

The JSON files contain labelled command examples for manual validation and
regression work. Their expected verdicts and layer labels reflect the policy
used when they were written. They need review before use with a changed policy;
they are not a detection-rate benchmark.

## Fields

Each example has an `id`, `category`, `description`, `task` and `command`.
`expected_verdict` is `blocked` or `allowed`; `expected_layer` is `L1`, `L2`, `L3`,
`L4` or null. `notes` explains the label. A command may now be rejected earlier
than its historical layer label suggests.

| File | Examples |
| --- | --- |
| `obfuscation.json` | 8 obfuscation cases |
| `reverse-shells.json` | 6 reverse-shell and backdoor cases |
| `exfiltration.json` | 6 transfer cases |
| `prompt-injection.json` | 5 prompt-injection cases |

## Use

Inspect the strings; do not execute them. For manual API checks, use the
[authenticated dry-run request](../docs/API.md#authenticated-dry-run-example) on
an authorized local instance. Keep credentials in the calling process rather
than copying a key into a script.

A non-200 response, transport error or malformed reply is a failed check, not an
observed correct verdict. Require a Boolean `approved` field and report failures
separately. Do not let a truthiness test turn an API error into a passing blocked
case.

The current offline suite and its limits are described in
[Verification](../docs/VERIFICATION.md). Current examples with inspected validator
sources are in [Attack scenarios](../docs/ATTACK_SCENARIOS.md).
