#!/bin/bash
echo "MAINTENANCE" > /opt/ai-lab/.mode
echo "[MAINTENANCE] Stopping sandbox for maintenance..."

cd /opt/ai-lab && docker-compose down

iptables -F
iptables -X
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT
iptables -P FORWARD ACCEPT

systemctl restart docker

echo "[MAINTENANCE] Docker stopped, full access enabled."
