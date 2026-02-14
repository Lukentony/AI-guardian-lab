#!/bin/bash
echo "TEST" > /opt/ai-lab/.mode
echo "[TEST MODE] Activating development environment..."

iptables -F
iptables -X
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT
iptables -P FORWARD ACCEPT

# Restart Docker to recreate chains
systemctl restart docker
sleep 2

cd /opt/ai-lab && docker-compose up -d

echo "[TEST MODE] Active. Permissive firewall, logging enabled."
