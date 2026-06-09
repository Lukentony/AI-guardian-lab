# API Reference

## Guardian (Port 5000)

The Guardian service runs the validation pipeline. Every endpoint requires the `X-API-Key` header.

### POST /validate

Validates a command against the security pipeline.

Request:
```json
{"command": "rm -rf /tmp", "task": "clean up temp files"}
```

Response — blocked by regex:
```json
{"approved": false, "reason": "Blocked by pattern: rm\\s+-rf\\s+/", "intent_source": "regex"}
```

Response — blocked by intent conflict:
```json
{"approved": false, "reason": "Intent conflict: task intent is read, command intent is delete", "intent_source": "mapping"}
```

Response — allowed:
```json
{"approved": true, "reason": null, "intent_source": "skip"}
```

Response — under load:
```json
{"approved": false, "reason": "Blocked: Guardian system under load, retry later", "intent_source": "system_load"}
```

### POST /report

Log a command execution to the audit database.

Request:
```json
{"command": "df -h", "approved": true, "intent_source": "skip"}
```

Response:
```json
{"status": "logged"}
```

### GET /health

Liveness check.

Response:
```json
{"status": "healthy"}
```

## Agent (Port 5001)

The agent generates and optionally executes commands via Guardian. Every endpoint requires the `X-API-Key` header.

### POST /execute

Generate a command from a task description, validate it through Guardian, and optionally execute in a sandbox.

Request:
```json
{"task": "show disk usage"}
```

Response — executed:
```json
{"status": "executed", "command": "df -h", "output": "Filesystem     1K-blocks      Used Available Use% Mounted on\n/dev/sda1       ..."}
```

Response — simulated (dry-run, `EXECUTE_COMMANDS` is not `true`):
```json
{"status": "simulated", "command": "df -h", "output": "[DRY-RUN] Command 'df -h' would be executed. Enable EXECUTE_COMMANDS=true for real action."}
```

Response — rejected by Guardian:
```json
{"status": "rejected", "command": "rm -rf /", "reason": "Intent conflict: task intent is read, command intent is delete"}
```

Response — error:
```json
{"status": "error", "reason": "Guardian auth failed"}
```

### GET /health

Liveness check.

Response:
```json
{"status": "healthy"}
```

## UI (Port 8081)

Web dashboard at `http://localhost:8081`.

Interactive form to send commands, browse audit history, and test attack scenarios.

## Examples

```bash
curl -s -X POST http://localhost:5000/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"command": "df -h", "task": "check disk space"}'
```

```bash
curl -s -X POST http://localhost:5001/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"task": "show disk usage"}'
```

```python
import requests

response = requests.post(
    "http://localhost:5000/validate",
    json={"command": "ls /tmp", "task": "list temp files"},
    headers={"X-API-Key": "your-api-key"}
)
print(response.json())
```
