#!/bin/bash
set -e

# Ensure database directory exist with correct permissions
mkdir -p /app/database

# Initialize database if it doesn't exist
if [ ! -f /app/database/audit.db ]; then
    echo "Initializing database..."
    sqlite3 /app/database/audit.db < /app/schema.sql
fi

# Ensure the unprivileged user can write to the database
# Note: Docker volumes might reset permissions, so we do it at boot
chown -R guardian:guardian /app/database

# Run with Gunicorn (SEC-04)
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 main:app
