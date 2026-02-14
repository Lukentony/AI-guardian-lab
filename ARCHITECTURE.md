# System Architecture

## Network Topology
```text
Local LAN (e.g., 192.168.1.0/24)
├─ Gateway Server (Local IP A)
├─ LLM Server (Local IP B) - Running Ollama/vLLM
└─ Sandbox Host (Local IP C) - Security Perimeter
   ├─ lab-guardian (Container IP: 172.30.0.3)
   └─ lab-agent (Container IP: 172.30.0.2)
```

## Data Flow
1. **User → Agent**: POST /execute {"task": "..."}
2. **Agent → LLM**: Generate bash command
3. **Agent → Guardian**: POST /validate {"command": "..."}
4. **Guardian**: Pattern matching & security validation
5. **Agent**: Execute if approved / Reject if blocked
6. **Agent → Guardian**: POST /report (logging)

## Endpoints

### Guardian (Port 5000)
- `GET /health`
- `POST /validate`
- `POST /report`

### Agent (Port 5001)
- `GET /health`
- `POST /execute`

## Blocked Patterns
`rm -rf`, `sudo`, `passwd`, `mkfs`, `dd`, `chmod 777`, `iptables`, `shutdown`, `reboot`, `kill -9`
