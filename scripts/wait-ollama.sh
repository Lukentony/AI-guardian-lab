#!/bin/bash
OLLAMA_URL="${OLLAMA_URL:-http://<ollama-ip>:11434}"
MAX_RETRIES=30
RETRY_DELAY=2

echo "[OLLAMA-CHECK] Verifica connessione a $OLLAMA_URL..."

for i in $(seq 1 $MAX_RETRIES); do
    if curl -s --connect-timeout 2 "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        echo "[OLLAMA-CHECK] ✓ Ollama raggiungibile (tentativo $i/$MAX_RETRIES)"
        exit 0
    fi
    echo "[OLLAMA-CHECK] Tentativo $i/$MAX_RETRIES fallito, attendo ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
done

echo "[OLLAMA-CHECK] ✗ Ollama non raggiungibile dopo $MAX_RETRIES tentativi"
exit 1
