# AI Guardian Lab - Database Integration & Maintenance Guide

This document describes the structure of the auditing database, how to directly query and modify its contents, and how to expose it to other external AI agents or services.

---

## 📊 Database Overview

AI Guardian Lab logs all validation results to a SQLite database (`audit.db`).
By default, the database is mounted on the host machine in the `./database` folder. Inside the `guardian` and `ui` containers, it is accessed at `/app/database/audit.db`.

### Database Schema

The primary table is `command_log`.

```sql
CREATE TABLE IF NOT EXISTS command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,          -- ISO 8601 UTC timestamp
    task TEXT NOT NULL,               -- The described task intent (Layer 3/4 input)
    command TEXT NOT NULL,            -- The actual executed shell command
    status TEXT NOT NULL,             -- "approved" or "denied"
    llm_provider TEXT,                -- LLM provider used (e.g. ollama, openai, groq)
    guardian_reason TEXT,             -- Rejection explanation or approval context
    intent_source TEXT DEFAULT NULL   -- Validation layer: "mapping", "llm", "skip", etc.
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON command_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_status ON command_log(status);
```

---

## 🛠️ Direct Database Modification

Since SQLite is a local file-based database, you can manipulate it directly from either the host machine or from inside the Docker container.

### Method 1: Directly from the Host (Simplest)
If you are on the host server (e.g., `srv1` / `NUC2`), you can use the `sqlite3` CLI directly on the mounted volume file:

```bash
# Query the last 10 validation logs
sqlite3 ./database/audit.db "SELECT * FROM command_log ORDER BY id DESC LIMIT 10;"

# Manually approve a blocked command (override)
sqlite3 ./database/audit.db "UPDATE command_log SET status = 'approved', guardian_reason = 'Manual admin override' WHERE id = <LOG_ID>;"

# Delete logs older than 30 days
sqlite3 ./database/audit.db "DELETE FROM command_log WHERE timestamp < date('now', '-30 days');"

# Defragment and optimize file size
sqlite3 ./database/audit.db "VACUUM;"
```

### Method 2: Running SQLite inside the Container
If you do not have `sqlite3` installed on the host, you can invoke the utility inside the running `lab-guardian` container (which has `sqlite3` pre-installed):

```bash
# Interactive SQLite shell
docker exec -it lab-guardian sqlite3 /app/database/audit.db

# Direct query execution
docker exec -it lab-guardian sqlite3 /app/database/audit.db "SELECT id, timestamp, status, command FROM command_log ORDER BY id DESC LIMIT 5;"
```

---

## 🤖 Sharing the Database with Other Agents

To allow other autonomous agents (e.g. Claude, OpenClaw, homeassistant, or custom cron scripts) to inspect the audit log or learn from historical validations, you can expose the database in two ways:

### 1. Volume Sharing (Read-Only)
For agents running in separate Docker containers on the same host, the safest approach is to mount the `./database` folder as a **read-only** volume. This prevents external agents from corrupting the logs.

Add this volume mapping to the other agent's service in `docker-compose.yml`:

```yaml
services:
  external-agent:
    image: custom-agent:latest
    volumes:
      - ./database:/app/database:ro  # Mounted as Read-Only (ro)
    environment:
      - GUARDIAN_DB_PATH=/app/database/audit.db
```

The external agent can then query the database locally using any standard SQLite library (e.g. Python's `sqlite3` or Node.js `sqlite3`):

```python
import sqlite3

def get_recent_blocks():
    conn = sqlite3.connect('/app/database/audit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT command, task FROM command_log WHERE status = 'denied' ORDER BY id DESC LIMIT 10")
    blocks = cursor.fetchall()
    conn.close()
    return blocks
```

### 2. API-Based Sharing (Network Access)
If the other agents run on different servers (e.g. over Tailscale) or cannot access the host filesystem, they can retrieve audits using the HTTP report endpoint.

- **Endpoint**: `POST /report` (Authenticated via `X-API-Key`)
- **Querying Reports**: While `/report` is write-only, you can inspect the SQLite state via the dashboard UI or create a custom read-only endpoint in `main.py` if needed.

---

## 🧹 Database Maintenance & Backup

- **Backup**: To safely back up the database without locking writes, use the SQLite backup API:
  ```bash
  sqlite3 ./database/audit.db ".backup ./database/audit_backup.db"
  ```
- **Integrity Check**:
  ```bash
  sqlite3 ./database/audit.db "PRAGMA integrity_check;"
  ```
