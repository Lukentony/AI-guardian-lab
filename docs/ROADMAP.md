# Roadmap

The hardening branch repairs the v1.2.0 validator and adds a shadow-mode System
One client. It remains a research lab. See [Verification](VERIFICATION.md) for
measured results rather than treating this roadmap as a completion record.

## Next work

- Verify the ordinary-service Compose build and persistent-state recovery on a
  Docker-equipped test host.
- Find a compatible patched model runtime. The current Kev candidate requires a
  vulnerable PyTorch range and is quarantined.
- Evaluate a reviewed replacement on independent workloads. The measured CPU
  candidate missed the 500 ms budget on every calibration case.
- Add OS-level isolation before executing untrusted commands.
- Define recovery for uncertain execution outcomes; the executor does not provide
  durable exactly-once execution.

## Later options

Shared rate-limit storage would be needed for deployment across multiple workers.
Finer permissions and additional forensic views are possible follow-up work, not
implemented guarantees. Additional model providers need their own license and
privacy review.

Pattern mining already produces suggestions. Automatic policy promotion is not
a goal: an operator must review a pattern before it becomes active.
