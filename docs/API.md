# API Reference

## Agent API (Port 5001)

### POST /execute
Execute bash task via LLM with Guardian validation

Request:
{"task": "check disk usage"}

Response (Approved):
{"status": "executed", "command": "df -h", "llm_provider": "ollama"}

Response (Rejected):
{"status": "rejected", "command": "rm -rf /", "reason": "Blocked by pattern: rm\\s+-rf\\s+/", "explanation": "..."}

## Guardian API (Port 5000)

### POST /validate
Validate command safety

Request:
{"command": "df -h"}

Response:
{"approved": true}

Response (Blocked):
{"approved": false, "reason": "Blocked by pattern: mkfs\\."}

### POST /explain
Generate explanation for dangerous command

Request:
{"command": "rm -rf /", "reason": "Blocked by pattern"}

Response:
{"explanation": "This command recursively deletes all files..."}

## UI (Port 8080)

Web dashboard with interactive form and command history

## Examples

cURL:
curl -X POST http://localhost:5001/execute -H "Content-Type: application/json" -d '{"task": "show processes"}'

Python:
import requests
r = requests.post('http://localhost:5001/execute', json={'task': 'list files'})
print(r.json())
