#!/bin/bash
echo "LAB" > /opt/ai-lab/.mode
echo "[LAB MODE] Activating total isolation..."

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

# Gateway Server (required for routing)
iptables -A OUTPUT -d <gateway-ip> -j ACCEPT
iptables -A INPUT -s <gateway-ip> -j ACCEPT

# DNS (required for Docker)
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A INPUT -p udp --sport 53 -m state --state ESTABLISHED -j ACCEPT

# Ollama via gateway
iptables -A OUTPUT -d <ollama-ip> -p tcp --dport 11434 -j ACCEPT
iptables -A INPUT -s <ollama-ip> -p tcp --sport 11434 -m state --state ESTABLISHED,RELATED -j ACCEPT

# SSH from Gateway
iptables -A INPUT -s <gateway-ip> -p tcp --dport 22 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A OUTPUT -d <gateway-ip> -p tcp --sport 22 -m state --state ESTABLISHED -j ACCEPT

# Block logging
iptables -A INPUT -j LOG --log-prefix "[FW-BLOCK-IN] "
iptables -A OUTPUT -j LOG --log-prefix "[FW-BLOCK-OUT] "

cd /opt/ai-lab && docker-compose up -d

echo "[LAB MODE] Active. Sandbox isolated, Ollama reachable via gateway."
