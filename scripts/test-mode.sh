#!/bin/bash
echo "TEST" > /opt/ai-lab/.mode
echo "[TEST MODE] Attivazione ambiente di sviluppo..."

iptables -F
iptables -X
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT
iptables -P FORWARD ACCEPT

# Riavvia Docker per ricreare chain
systemctl restart docker
sleep 2

cd /opt/ai-lab && docker-compose up -d

echo "[TEST MODE] Attivo. Firewall permissivo, logging abilitato."
