#!/bin/sh
set -eu
cd "$(dirname "$0")"
# Stop before downloads while the pinned candidate is quarantined.
python3 qualification.py
command -v uv >/dev/null || { echo 'Install uv first; no sudo is used.' >&2; exit 1; }
if [ ! -x .venv/bin/python ]; then
    uv venv --python 3.13 .venv
fi
# Downloads public packages/weights only; inference remains local.
uv pip install --python .venv/bin/python -r requirements.lock
printf '%s\n' 'Model environment ready. See docs/SYSTEM_ONE.md before serving.'
