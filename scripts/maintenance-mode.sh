#!/bin/bash
echo "MAINTENANCE" > /opt/ai-lab/.mode
echo "[MAINTENANCE] Fermata sandbox per manutenzione..."

cd /opt/ai-lab && docker-compose down

iptables -F
iptables -X
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT
iptables -P FORWARD ACCEPT

systemctl restart docker

echo "[MAINTENANCE] Docker fermato, accesso completo abilitato."
