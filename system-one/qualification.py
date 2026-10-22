"""Startup gate for the optional inference runtime.

Qualification record for the 2026-10 revision:

- Kev pinned at ``1f04cfa28e6a708485b28a9585010b9e436b776e``;
- CPU PyTorch 2.13.0+cpu, outside the vulnerable 2.8 range;
- Kev imports and loads the 0.8B checkpoint on that runtime;
- the observer remains shadow-only and cannot change a decision.

This gate verifies the runtime that was actually reviewed. It is deliberately
narrow: changing the torch range, the Kev archive or the model requires a new
qualification and a new review. It does not turn on enforcement; configuration
still accepts only ``off`` and ``shadow``.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

TORCH_MIN = (2, 9)
TORCH_MAX_EXCLUSIVE = (2, 14)
KEV_MIN = "0.1.0"
BLOCK_REASON = (
    "Optional Kev service is not qualified for this runtime. It requires a "
    "reviewed torch>=2.9,<2.14 installation and the pinned Kev archive; "
    "see docs/SYSTEM_ONE.md. Guardian baseline operation is unaffected."
)


def _release_tuple(raw: str) -> tuple[int, int, int]:
    parts = raw.split("+", 1)[0].split(".")
    if len(parts) < 2:
        raise ValueError(f"invalid version {raw!r}")
    numbers = []
    for part in parts[:3]:
        digits = "".join(char for char in part if char.isdigit())
        numbers.append(int(digits or "0"))
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers[:3])


def require_qualified_runtime() -> None:
    try:
        installed_torch = version("torch")
    except PackageNotFoundError as exc:
        raise RuntimeError("PyTorch is not installed for the optional service") from exc
    if not TORCH_MIN <= _release_tuple(installed_torch)[:2] < TORCH_MAX_EXCLUSIVE:
        raise RuntimeError(f"Unsupported torch {installed_torch}; {BLOCK_REASON}")
    try:
        installed_kev = version("kev")
    except PackageNotFoundError as exc:
        raise RuntimeError("The pinned Kev package is not installed") from exc
    if _release_tuple(installed_kev) < _release_tuple(KEV_MIN):
        raise RuntimeError(f"Unsupported kev {installed_kev}; {BLOCK_REASON}")


if __name__ == "__main__":
    try:
        require_qualified_runtime()
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
    print(f"Optional inference runtime qualified: torch {version('torch')}, kev {version('kev')}")
