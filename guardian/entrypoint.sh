#!/bin/sh
set -eu
# The shared Python audit module owns both fresh schema and legacy migration.
# Its BEGIN IMMEDIATE lock also serializes startup across Gunicorn workers.
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 \
    guardian.guardian.main:app
