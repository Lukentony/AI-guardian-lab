"""One reviewed startup gate for the optional inference runtime.

Do not bypass upstream dependency constraints or waive advisories merely to start
an observer. Clearing this gate requires a compatible patched runtime, a renewed
security review and fresh model qualification. It never controls Guardian policy.
"""

QUALIFIED = False
BLOCK_REASON = (
    "Optional Kev CPU service is quarantined: Kev requires torch>=2.6,<2.9, "
    "but the measured torch 2.8.0 CPU runtime has known security advisories. "
    "A compatible patched dependency set and renewed evaluation are required. "
    "See docs/SYSTEM_ONE.md. Guardian baseline/shadow-client operation is unaffected."
)


def require_qualified_runtime():
    if not QUALIFIED:
        raise RuntimeError(BLOCK_REASON)


if __name__ == "__main__":
    try:
        require_qualified_runtime()
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
