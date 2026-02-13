
Architettura Sistema
Network Topology
text
LAN 192.168.0.0/24
├─ NUC1 (192.168.0.90) - Gateway
├─ PC Ollama (192.168.0.50) - LLM
└─ NUC2 (10.10.10.2) - Sandbox
   ├─ lab-guardian (172.30.0.3:5000)
   └─ lab-agent (172.30.0.2:5001)
Data Flow
User → Agent: POST /execute {"task": "..."}

Agent → Ollama: Genera comando bash

Agent → Guardian: POST /validate {"command": "..."}

Guardian: Pattern matching

Agent: Execute se approvato / Reject se bloccato

Agent → Guardian: POST /report (log)

Endpoints
Guardian (5000)
GET /health

POST /validate

POST /report

Agent (5001)
GET /health

POST /execute

Pattern Bloccati
rm -rf, sudo, passwd, mkfs, dd, chmod 777, iptables, shutdown, reboot, kill -9
