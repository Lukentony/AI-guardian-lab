"""Offline checks for the pinned GGUF downloader."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tools.onboarding.model import ModelSpec, download_model


def _spec(payload: bytes, source: Path, *, sha256: str | None = None) -> ModelSpec:
    return ModelSpec(
        filename="fixture.gguf",
        url=source.as_uri(),
        sha256=sha256 or hashlib.sha256(payload).hexdigest(),
        size=len(payload),
    )


def test_download_verifies_and_reuses_the_artifact(tmp_path, monkeypatch) -> None:
    payload = b"fake-gguf" * 1024
    source = tmp_path / "fixture.gguf"
    source.write_bytes(payload)
    spec = _spec(payload, source)
    messages: list[str] = []
    assert download_model(tmp_path, messages.append, spec=spec) == 0
    target = tmp_path / "state" / "models" / spec.filename
    assert target.read_bytes() == payload
    assert download_model(tmp_path, messages.append, spec=spec) == 0
    assert "already present" in messages[-1]


def test_download_removes_a_corrupt_artifact(tmp_path, monkeypatch) -> None:
    payload = b"wrong"
    source = tmp_path / "fixture.gguf"
    source.write_bytes(payload)
    spec = _spec(payload, source, sha256="0" * 64)
    assert download_model(tmp_path, lambda _: None, spec=spec) == 1
    assert not (tmp_path / "state" / "models" / spec.filename).exists()
