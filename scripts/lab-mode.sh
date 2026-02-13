#!/bin/bash
echo "LAB" > /opt/ai-lab/.mode
echo "[LAB MODE] Attivazione isolamento totale..."

iptables -F
iptables -X

iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# Loopback
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Docker networks
iptables -A INPUT -i docker0 -j ACCEPT
iptables -A OUTPUT -o docker0 -j ACCEPT
iptables -A INPUT -s 172.30.0.0/16 -j ACCEPT
iptables -A OUTPUT -d 172.30.0.0/16 -j ACCEPT

# Gateway NUC1 (necessario per routing)
iptables -A OUTPUT -d 10.10.10.1 -j ACCEPT
iptables -A INPUT -s 10.10.10.1 -j ACCEPT

# DNS (necessario per Docker)
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A INPUT -p udp --sport 53 -m state --state ESTABLISHED -j ACCEPT

# Ollama via gateway
iptables -A OUTPUT -d 192.168.0.50 -p tcp --dport 11434 -j ACCEPT
iptables -A INPUT -s 192.168.0.50 -p tcp --sport 11434 -m state --state ESTABLISHED,RELATED -j ACCEPT

# SSH da NUC1
iptables -A INPUT -s 10.10.10.1 -p tcp --dport 22 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A OUTPUT -d 10.10.10.1 -p tcp --sport 22 -m state --state ESTABLISHED -j ACCEPT

# Log blocchi
iptables -A INPUT -j LOG --log-prefix "[FW-BLOCK-IN] "
iptables -A OUTPUT -j LOG --log-prefix "[FW-BLOCK-OUT] "

cd /opt/ai-lab && docker-compose up -d

echo "[LAB MODE] Attivo. NUC2 isolato, Ollama raggiungibile via gateway."
