# System Architecture

## Network Topology
```text
Sandbox Host (Production Hardened)
├─ Networks: internal bridge "agent-net" (No direct WAN for containers)
├─ lab-guardian (Port 5000, Python 3.11-slim, Gunicorn, User: guardian)
├─ lab-agent    (Port 5001, Python 3.11-slim, Gunicorn, User: agent)
└─ lab-ui       (Port 8080, Python 3.11-slim, User: ui)
```

## Security Stack (Defense-in-Depth)
1. **L1: Sandbox Isolation**: Non-privileged users and resource limits (cgroups).
2. **L2: Zonal Enforcement**: Fail-closed binary allowlisting via `policy.yaml`.
3. **L3: Content Analysis**: Dual-path regex matching with ReDoS-safe timeouts.
4. **L4: Audit & Redaction**: WAL-enabled logging with real-time secret masking.

## Data Flow
1. **User → Agent**: Request execution of a task.
2. **Agent → LLM**: Prompt engineering for command generation.
3. **Agent → Guardian**: Validation request for the generated command.
4. **Guardian**: 
   - Check Binary Allowlist (Zones).
   - Normalize and check Regex Patterns (Dual-Path).
5. **Agent**: Execute in unprivileged shell if approved.
6. **Agent/Guardian**: Log to encrypted-ready SQLite audit log.

## Endpoints

### Guardian (Port 5000)
- `GET /health`
- `POST /validate` - Command security check.
- `POST /report` - Audit logging.
- `POST /learn`  - [New] Authenticated feedback loop for pattern injection.

### Agent (Port 5001)
- `POST /execute` - Main task entrypoint.
- `GET /health`

---
*"Security and stability over feature bloat."*
