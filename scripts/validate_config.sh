#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Docker Compose is required.' >&2; exit 1; }
# Do not source .env as executable shell code or print expanded secrets.
docker compose config --quiet
printf '%s\n' 'Compose configuration accepted. Policy and model schemas are checked at Guardian startup.'
