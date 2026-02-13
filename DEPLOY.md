
Guida Deployment
Prerequisiti
Ubuntu 24.04

Docker + docker-compose

Python 3.11+

Ollama server accessibile

Installazione
bash
# 1. Clona progetto
cd /opt/ai-lab

# 2. Crea network Docker
docker network create --subnet=172.30.0.0/16 agent-net

# 3. Build immagini
cd guardian && docker build -t guardian-mvp:latest .
cd ../agent && docker build -t agent-mvp:latest .

# 4. Avvia stack
cd /opt/ai-lab && docker-compose up -d

# 5. Verifica
docker-compose ps
curl http://localhost:5000/health
curl http://localhost:5001/health
Configurazione Ollama
Agent richiede OLLAMA_URL configurato in docker-compose.yml:

text
environment:
  - OLLAMA_URL=http://192.168.0.50:11434
Modalità Operative
bash
# TEST (sviluppo)
/opt/ai-lab/scripts/test-mode.sh

# MAINTENANCE (aggiornamenti)
/opt/ai-lab/scripts/maintenance-mode.sh

# Verifica modalità
/opt/ai-lab/scripts/check-mode.sh
Troubleshooting
Container non partono dopo iptables flush:

bash
systemctl restart docker
docker-compose up -d
Network agent-net non trovata:

bash
docker network create --subnet=172.30.0.0/16 agent-net
Ollama timeout:

bash
/opt/ai-lab/scripts/wait-ollama.sh
