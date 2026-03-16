#!/bin/bash

set -e

mkdir -p /app/database

if [ ! -f /app/database/audit.db ]; then

    echo "Initializing database..."

    sqlite3 /app/database/audit.db < /app/schema.sql

fi

exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 main:app