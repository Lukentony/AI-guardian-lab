#!/bin/sh
set -eu
cd "$(dirname "$0")"
command -v uv >/dev/null || { echo 'Install uv first; no sudo is used.' >&2; exit 1; }
if [ ! -x .venv/bin/python ]; then
    uv venv --python 3.13 .venv
fi
# Install the reviewed torch first, then the hashed set, then Kev without
# dependency resolution. Its metadata cap must not replace torch 2.13.
uv pip install --python .venv/bin/python \
    --index-url https://download.pytorch.org/whl/cpu \
    'torch==2.13.0+cpu'
uv pip install --python .venv/bin/python -r requirements.lock
uv pip install --python .venv/bin/python --no-deps \
    'kev @ https://github.com/jaredpalmer/kev/archive/1f04cfa28e6a708485b28a9585010b9e436b776e.tar.gz#sha256=3d0230dbc5c6155cf6a0933696998a9ad6942754a2af1a95c88bf23e1d2cc631'
# Download weights and keep inference local; no command is executed.
.venv/bin/python qualification.py
printf '%s\n' 'Model environment ready. See docs/SYSTEM_ONE.md before serving.'
