"""Model artifact for the llama.cpp full profile.

The GGUF file is downloaded explicitly; it is not stored in the repository.
"""

from __future__ import annotations

import hashlib
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ModelSpec:
    filename: str
    url: str
    sha256: str
    size: int


MODEL = ModelSpec(
    filename="qwen2.5-3b-instruct-q4_k_m.gguf",
    url=(
        "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/"
        "qwen2.5-3b-instruct-q4_k_m.gguf"
    ),
    sha256="626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d",
    size=2104932768,
)


def model_path(root: Path) -> Path:
    return root / "state" / "models" / MODEL.filename


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(
    root: Path,
    out: Callable[[str], None] = print,
    *,
    spec: ModelSpec = MODEL,
    force: bool = False,
) -> int:
    """Download and verify the GGUF. Existing verified files are reused."""
    target = root / "state" / "models" / spec.filename
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.is_file() and not force:
        if target.stat().st_size == spec.size and _sha256(target) == spec.sha256:
            target.chmod(0o644)
            target.parent.chmod(0o755)
            out(f"Model already present and verified: {target}")
            return 0
        out(f"Existing model does not match the pinned artifact: {target}")
        return 1

    temporary = target.with_name(target.name + ".part")
    temporary.unlink(missing_ok=True)
    out(f"Downloading {spec.filename} ({spec.size / (1024**3):.2f} GiB) ...")
    digest = hashlib.sha256()
    received = 0
    try:
        request = urllib.request.Request(spec.url, headers={"User-Agent": "ai-guardian-lab/1.6"})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as stream:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                stream.write(chunk)
                digest.update(chunk)
                received += len(chunk)
        if received != spec.size or digest.hexdigest() != spec.sha256:
            temporary.unlink(missing_ok=True)
            out("Downloaded model did not match size or SHA-256; removed.")
            return 1
        os.replace(temporary, target)
        target.chmod(0o644)
        target.parent.chmod(0o755)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        temporary.unlink(missing_ok=True)
        out(f"Model download failed: {type(exc).__name__}")
        return 1

    out(f"Verified model: {target}")
    return 0
