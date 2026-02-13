#!/bin/bash
set -e

echo "=== AI Guardian Lab - Configuration Validator ==="
echo ""

source .env 2>/dev/null || { echo "ERROR: .env not found"; exit 1; }

echo "[1/5] Checking LLM Provider Configuration..."
if [ -z "$LLM_PROVIDER" ]; then
    echo "  ERROR: LLM_PROVIDER not set"
    exit 1
fi
echo "  OK: Provider = $LLM_PROVIDER"

echo ""
echo "[2/5] Validating Provider-Specific Config..."
case $LLM_PROVIDER in
    ollama)
        [ -z "$OLLAMA_HOST" ] && echo "  ERROR: OLLAMA_HOST not set" && exit 1
        echo "  Testing Ollama connection: $OLLAMA_HOST"
        curl -s "$OLLAMA_HOST/api/tags" > /dev/null || { echo "  ERROR: Cannot reach Ollama"; exit 1; }
        echo "  OK: Ollama reachable"
        ;;
    openai)
        [ -z "$OPENAI_API_KEY" ] && echo "  ERROR: OPENAI_API_KEY not set" && exit 1
        echo "  OK: OpenAI API key present"
        ;;
    anthropic)
        [ -z "$ANTHROPIC_API_KEY" ] && echo "  ERROR: ANTHROPIC_API_KEY not set" && exit 1
        echo "  OK: Anthropic API key present"
        ;;
    deepseek)
        [ -z "$DEEPSEEK_API_KEY" ] && echo "  ERROR: DEEPSEEK_API_KEY not set" && exit 1
        echo "  OK: DeepSeek API key present"
        ;;
    gemini)
        [ -z "$GEMINI_API_KEY" ] && echo "  ERROR: GEMINI_API_KEY not set" && exit 1
        echo "  OK: Gemini API key present"
        ;;
esac

echo ""
echo "[3/5] Checking Port Availability..."
for port in 5000 5001 8080; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "  WARNING: Port $port already in use"
    else
        echo "  OK: Port $port available"
    fi
done

echo ""
echo "[4/5] Validating Pattern Files..."
[ -f "guardian/config/patterns.yaml" ] && echo "  OK: patterns.yaml found" || echo "  WARNING: patterns.yaml missing"
[ -f "guardian/config/learned_patterns.yaml" ] && echo "  OK: learned_patterns.yaml found" || echo "  WARNING: learned_patterns.yaml missing"

echo ""
echo "[5/5] Docker Health Check..."
docker ps --filter "name=lab-" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "  INFO: Containers not running (run docker-compose up -d)"

echo ""
echo "=== Validation Complete ==="
