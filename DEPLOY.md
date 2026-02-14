# Deployment Guide

## Prerequisites
- **Ubuntu 24.04** (Recommended)
- **Docker + Docker Compose**
- **Python 3.11+**
- **Accessible Ollama Server**

## Installation

```bash
# 1. Clone the project
cd /opt/ai-lab

# 2. Create Docker network
docker network create --subnet=172.30.0.0/16 agent-net

# 3. Build images
cd guardian && docker build -t guardian-mvp:latest .
cd ../agent && docker build -t agent-mvp:latest .

# 4. Start the stack
cd /opt/ai-lab && docker-compose up -d

# 5. Verify deployment
docker-compose ps
curl http://localhost:5000/health
curl http://localhost:5001/health
```

## Ollama Configuration
The Agent requires `OLLAMA_URL` to be configured in `docker-compose.yml`:

```yaml
environment:
  - OLLAMA_URL=http://<your-ollama-ip>:11434
```

## Operational Modes

```bash
# TEST MODE (Development)
/opt/ai-lab/scripts/test-mode.sh

# MAINTENANCE MODE (Updates)
/opt/ai-lab/scripts/maintenance-mode.sh

# Check Current Mode
/opt/ai-lab/scripts/check-mode.sh
```

## Troubleshooting

### Containers won't start after iptables flush:
```bash
systemctl restart docker
docker-compose up -d
```

### Network `agent-net` not found:
```bash
docker network create --subnet=172.30.0.0/16 agent-net
```

### Ollama timeout:
```bash
/opt/ai-lab/scripts/wait-ollama.sh
```
