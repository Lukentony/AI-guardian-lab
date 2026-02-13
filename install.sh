#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════╗
║   AI Guardian Lab - Universal Installer  ║
║   Portable Security for LLM Commands     ║
╚═══════════════════════════════════════════╝
EOF
echo -e "${NC}"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

check_command() {
    command -v $1 &> /dev/null
}

test_ollama_connection() {
    local host=$1
    if curl -s --max-time 5 "$host/api/tags" &> /dev/null; then
        return 0
    fi
    return 1
}

test_api_key() {
    local provider=$1
    local key=$2
    
    case $provider in
        openai)
            curl -s --max-time 10 https://api.openai.com/v1/models \
                -H "Authorization: Bearer $key" | grep -q "id" && return 0
            ;;
        anthropic)
            curl -s --max-time 10 https://api.anthropic.com/v1/messages \
                -H "x-api-key: $key" \
                -H "anthropic-version: 2023-06-01" \
                -H "Content-Type: application/json" \
                -d '{"model":"claude-3-5-haiku-20241022","max_tokens":1,"messages":[{"role":"user","content":"test"}]}' \
                | grep -q "id" && return 0
            ;;
        groq)
            curl -s --max-time 10 https://api.groq.com/openai/v1/models \
                -H "Authorization: Bearer $key" | grep -q "id" && return 0
            ;;
    esac
    return 1
}

log_info "Step 1/8: Checking prerequisites..."

if ! check_command docker; then
    log_error "Docker not found. Install: https://docs.docker.com/get-docker/"
fi

if ! docker info &> /dev/null; then
    log_error "Docker daemon not running. Start with: sudo systemctl start docker"
fi

log_success "Docker is installed and running"

if check_command docker-compose; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

log_info "Step 2/8: LLM Provider Detection & Configuration"
echo ""

OLLAMA_DETECTED=false
OLLAMA_LOCAL=false
OLLAMA_REMOTE=false

if check_command ollama; then
    if test_ollama_connection "http://localhost:11434"; then
        log_success "Ollama detected on localhost:11434"
        OLLAMA_DETECTED=true
        OLLAMA_LOCAL=true
    fi
fi

if [ "$OLLAMA_DETECTED" = false ]; then
    read -p "Do you have Ollama running on a remote server? (y/n): " has_remote
    if [ "$has_remote" = "y" ]; then
        read -p "Enter Ollama host (e.g., http://192.168.1.100:11434): " remote_host
        if test_ollama_connection "$remote_host"; then
            log_success "Connected to Ollama at $remote_host"
            OLLAMA_DETECTED=true
            OLLAMA_REMOTE=true
            OLLAMA_HOST="$remote_host"
        else
            log_warn "Cannot connect to $remote_host"
        fi
    fi
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo -e "${CYAN}LLM Provider Selection${NC}"
echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo ""

if [ "$OLLAMA_DETECTED" = true ]; then
    echo -e "${GREEN}✓ Ollama Available${NC} (Recommended for privacy)"
fi

echo "Cloud Providers (require API key):"
echo "  - OpenAI (GPT-4, best quality, ~\$0.01/command)"
echo "  - Anthropic Claude (smart, safe, ~\$0.015/command)"
echo "  - Groq (FREE tier, fast inference, rate limits)"
echo "  - DeepSeek (cheapest, ~\$0.001/command)"
echo "  - Google Gemini"
echo ""

PRIMARY_PROVIDER=""
FALLBACK_PROVIDERS=()

if [ "$OLLAMA_DETECTED" = true ]; then
    read -p "Use Ollama as primary provider? (y/n) [y]: " use_ollama
    use_ollama="${use_ollama:-y}"
    
    if [ "$use_ollama" = "y" ]; then
        PRIMARY_PROVIDER="ollama"
        
        if [ "$OLLAMA_LOCAL" = true ]; then
            OLLAMA_HOST="http://host.docker.internal:11434"
            # For local queries from this script (outside docker), use localhost
            QUERY_HOST="http://localhost:11434"
        else
            QUERY_HOST="$OLLAMA_HOST"
        fi

        log_info "Querying available models from $QUERY_HOST..."
        
        # Fetch models JSON
        MODELS_JSON=$(curl -s --max-time 5 "$QUERY_HOST/api/tags" || echo "")
        
        # Extract model names using grep/sed (avoiding jq dependency)
        # 1. Grab names inside "name": "..." 
        # 2. Clean up quotes and keys
        MODEL_LIST=$(echo "$MODELS_JSON" | grep -oP '(?<="name":")[^"]*' 2>/dev/null || echo "$MODELS_JSON" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g')
        
        # Convert to array
        IFS=$'\n' read -rd '' -a ALL_MODELS <<< "$MODEL_LIST"

        if [ ${#ALL_MODELS[@]} -gt 0 ]; then
            echo ""
            echo -e "${CYAN}Available Ollama Models:${NC}"
            i=1
            for m in "${ALL_MODELS[@]}"; do
                echo "  $i) $m"
                ((i++))
            done
            echo "  0) Other (enter manually)"
            echo ""
            
            # Select Coder Model
            while true; do
                read -p "Select CODER model number [1]: " coder_choice
                coder_choice="${coder_choice:-1}"
                
                if [ "$coder_choice" -eq 0 ]; then
                    read -p "Enter manual model name: " OLLAMA_MODEL_CODER
                    break
                elif [ "$coder_choice" -ge 1 ] && [ "$coder_choice" -le "${#ALL_MODELS[@]}" ]; then
                    OLLAMA_MODEL_CODER="${ALL_MODELS[$((coder_choice-1))]}"
                    break
                else
                    echo -e "${RED}Invalid selection.${NC}"
                fi
            done
            
            # Select Explain Model (Optional: reuse logic or just ask)
            echo ""
            while true; do
                read -p "Select EXPLAIN model number [same as CODER]: " explain_choice
                
                if [ -z "$explain_choice" ]; then
                    OLLAMA_MODEL_EXPLAIN="$OLLAMA_MODEL_CODER"
                    break
                elif [ "$explain_choice" -eq 0 ]; then
                    read -p "Enter manual model name: " OLLAMA_MODEL_EXPLAIN
                     break
                elif [ "$explain_choice" -ge 1 ] && [ "$explain_choice" -le "${#ALL_MODELS[@]}" ]; then
                     OLLAMA_MODEL_EXPLAIN="${ALL_MODELS[$((explain_choice-1))]}"
                     break
                else
                     echo -e "${RED}Invalid selection.${NC}"
                fi
            done
            
            log_success "Selected: Coder=$OLLAMA_MODEL_CODER, Explain=$OLLAMA_MODEL_EXPLAIN"
            
        else
            log_warn "Could not list models automatically."
            read -p "Coder model [qwen2.5-coder:7b]: " coder_model
            OLLAMA_MODEL_CODER="${coder_model:-qwen2.5-coder:7b}"
            
            read -p "Explain model [llama3.2:3b-instruct-q4_K_M]: " explain_model
            OLLAMA_MODEL_EXPLAIN="${explain_model:-llama3.2:3b-instruct-q4_K_M}"
        fi
        
        # Only pull if not present (simple check: if we selected from list, it's present. If manual, maybe not)
        # But safest is to try pull anyway to update or ensure it exists
        if [[ ! " ${ALL_MODELS[*]} " =~ " ${OLLAMA_MODEL_CODER} " ]]; then
             log_info "Pulling model $OLLAMA_MODEL_CODER..."
             ollama pull "$OLLAMA_MODEL_CODER" 2>/dev/null || log_warn "Failed to pull/verify $OLLAMA_MODEL_CODER"
        fi
        
        read -p "Configure cloud fallback provider? (y/n) [n]: " add_fallback
    fi
else
    log_warn "Ollama not detected. You must configure a cloud provider."
    add_fallback="y"
fi

if [ "$add_fallback" = "y" ] || [ -z "$PRIMARY_PROVIDER" ]; then
    echo ""
    echo "Select cloud provider:"
    echo "  1) Groq (FREE tier, fast)"
    echo "  2) OpenAI (GPT-4)"
    echo "  3) Anthropic Claude"
    echo "  4) DeepSeek (cheapest)"
    echo "  5) Google Gemini"
    echo "  6) Skip (manual config later)"
    echo ""
    read -p "Enter choice [1-6]: " cloud_choice
    
    case $cloud_choice in
        1)
            read -p "Enter Groq API key (from https://console.groq.com): " GROQ_API_KEY
            if [ -n "$GROQ_API_KEY" ]; then
                log_info "Testing Groq connection..."
                if test_api_key "groq" "$GROQ_API_KEY"; then
                    log_success "Groq API key valid"
                    [ -z "$PRIMARY_PROVIDER" ] && PRIMARY_PROVIDER="groq"
                    LLM_MODEL_CODER="groq/llama-3.3-70b-versatile"
                    LLM_MODEL_EXPLAIN="groq/llama-3.1-8b-instant"
                else
                    log_warn "Groq API key validation failed. Continuing anyway..."
                    [ -z "$PRIMARY_PROVIDER" ] && PRIMARY_PROVIDER="groq"
                    LLM_MODEL_CODER="groq/llama-3.3-70b-versatile"
                    LLM_MODEL_EXPLAIN="groq/llama-3.1-8b-instant"
                fi
            else
                log_error "Groq API key is required"
            fi
            ;;
        2)
            read -p "Enter OpenAI API key: " OPENAI_API_KEY
            if [ -n "$OPENAI_API_KEY" ]; then
                log_info "Testing OpenAI connection..."
                if test_api_key "openai" "$OPENAI_API_KEY"; then
                    log_success "OpenAI API key valid"
                    [ -z "$PRIMARY_PROVIDER" ] && PRIMARY_PROVIDER="openai"
                    LLM_MODEL_CODER="gpt-4o"
                    LLM_MODEL_EXPLAIN="gpt-4o-mini"
                else
                    log_warn "OpenAI API key validation failed"
                    [ -z "$PRIMARY_PROVIDER" ] && PRIMARY_PROVIDER="openai"
                    LLM_MODEL_CODER="gpt-4o"
                    LLM_MODEL_EXPLAIN="gpt-4o-mini"
                fi
            else
                log_error "OpenAI API key is required"
            fi
            ;;
        3)
            read -p "Enter Anthropic API key: " ANTHROPIC_API_KEY
            if [ -n "$ANTHROPIC_API_KEY" ]; then
                log_info "Testing Anthropic connection..."
                if test_api_key "anthropic" "$ANTHROPIC_API_KEY"; then
                    log_success "Anthropic API key valid"
                    [ -z "$PRIMARY_PROVIDER" ] && PRIMARY_PROVIDER="anthropic"
                    LLM_MODEL_CODER="claude-3-5-sonnet-20241022"
                    LLM_MODEL_EXPLAIN="claude-3-5-haiku-20241022"
                else
                    log_warn "Anthropic API key validation failed"
                    [ -z "$PRIMARY_PROVIDER" ] && PRIMARY_PROVIDER="anthropic"
                    LLM_MODEL_CODER="claude-3-5-sonnet-20241022"
                    LLM_MODEL_EXPLAIN="claude-3-5-haiku-20241022"
                fi
            else
                log_error "Anthropic API key is required"
            fi
            ;;
        4)
            read -p "Enter DeepSeek API key: " DEEPSEEK_API_KEY
            if [ -n "$DEEPSEEK_API_KEY" ]; then
                log_info "DeepSeek key configured (no validation test available)"
                [ -z "$PRIMARY_PROVIDER" ] && PRIMARY_PROVIDER="deepseek"
                LLM_MODEL_CODER="deepseek-coder"
                LLM_MODEL_EXPLAIN="deepseek-chat"
            else
                log_error "DeepSeek API key is required"
            fi
            ;;
        5)
            read -p "Enter Gemini API key: " GEMINI_API_KEY
            if [ -n "$GEMINI_API_KEY" ]; then
                log_info "Gemini key configured (no validation test available)"
                [ -z "$PRIMARY_PROVIDER" ] && PRIMARY_PROVIDER="gemini"
                LLM_MODEL_CODER="gemini-1.5-pro"
                LLM_MODEL_EXPLAIN="gemini-1.5-flash"
            else
                log_error "Gemini API key is required"
            fi
            ;;
        6)
            log_warn "No provider configured. You must edit .env manually."
            PRIMARY_PROVIDER="ollama"
            ;;
    esac
fi

if [ -z "$PRIMARY_PROVIDER" ]; then
    log_error "No valid provider configured. Installation aborted."
fi

log_info "Step 3/8: Port Configuration"
read -p "Guardian API port [5000]: " guardian_port
GUARDIAN_PORT="${guardian_port:-5000}"
read -p "Agent API port [5001]: " agent_port
AGENT_PORT="${agent_port:-5001}"
read -p "Web UI port [8080]: " ui_port
UI_PORT="${ui_port:-8080}"

log_info "Step 4/8: Generating .env configuration..."
cat > .env << EOF
# Generated by install.sh on $(date)
# Primary Provider: $PRIMARY_PROVIDER

LLM_PROVIDER=$PRIMARY_PROVIDER

# Ollama Configuration
OLLAMA_HOST=${OLLAMA_HOST:-http://host.docker.internal:11434}
OLLAMA_MODEL_CODER=${OLLAMA_MODEL_CODER:-qwen2.5-coder:7b}
OLLAMA_MODEL_EXPLAIN=${OLLAMA_MODEL_EXPLAIN:-llama3.2:3b-instruct-q4_K_M}

# Cloud Provider Keys
OPENAI_API_KEY=${OPENAI_API_KEY:-}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
GEMINI_API_KEY=${GEMINI_API_KEY:-}
GROQ_API_KEY=${GROQ_API_KEY:-}

# Model Configuration (used by non-Ollama providers)
LLM_MODEL_CODER=${LLM_MODEL_CODER:-gpt-4o}
LLM_MODEL_EXPLAIN=${LLM_MODEL_EXPLAIN:-gpt-4o-mini}

# Service URLs
GUARDIAN_URL=http://guardian:5000
GUARDIAN_PORT=$GUARDIAN_PORT
AGENT_PORT=$AGENT_PORT
UI_PORT=$UI_PORT

# Database
DB_PATH=/app/database/audit.db

# Security
WORKSPACE_DIR=./workspace
EXEC_UID=1000
EXEC_GID=1000
SANDBOX_MODE=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text

# Pattern Learning
PATTERN_CONFIDENCE_THRESHOLD=30
PATTERN_LEARNING_SAMPLE_SIZE=100
EOF

log_success ".env file created"

log_info "Step 5/8: Initializing directories..."
mkdir -p database workspace guardian/config
chmod 755 database workspace

log_info "Step 6/8: Building Docker images..."
log_info "Building Guardian..."
docker build -t guardian-mvp:latest -f guardian/Dockerfile guardian/ || log_error "Guardian build failed"

log_info "Building Agent..."
docker build -t agent-mvp:latest -f agent/Dockerfile agent/ || log_error "Agent build failed"

log_info "Building UI..."
docker build -t ui-mvp:latest -f ui/Dockerfile ui/ || log_error "UI build failed"

log_success "All images built successfully"

log_info "Step 7/8: Starting services..."
$COMPOSE_CMD up -d || log_error "Failed to start services"

log_info "Step 8/8: Health checks (waiting 10 seconds)..."
sleep 10

AGENT_HEALTH=false
GUARDIAN_HEALTH=false
UI_HEALTH=false

if curl -s --max-time 5 http://localhost:$AGENT_PORT/health &> /dev/null; then
    log_success "Agent running on port $AGENT_PORT"
    AGENT_HEALTH=true
else
    log_warn "Agent health check failed (check: docker logs lab-agent)"
fi

if curl -s --max-time 5 http://localhost:$GUARDIAN_PORT/health &> /dev/null; then
    log_success "Guardian running on port $GUARDIAN_PORT"
    GUARDIAN_HEALTH=true
else
    log_warn "Guardian health check failed (check: docker logs lab-guardian)"
fi

if curl -s --max-time 5 http://localhost:$UI_PORT &> /dev/null; then
    log_success "Web UI running on port $UI_PORT"
    UI_HEALTH=true
else
    log_warn "Web UI health check failed (check: docker logs lab-ui)"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Installation Complete!              ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Configuration Summary:${NC}"
echo "  Primary Provider: $PRIMARY_PROVIDER"
if [ "$OLLAMA_DETECTED" = true ]; then
    echo "  Ollama: $OLLAMA_HOST"
fi
echo "  Agent API: http://localhost:$AGENT_PORT"
echo "  Guardian API: http://localhost:$GUARDIAN_PORT"
echo "  Web Dashboard: http://localhost:$UI_PORT"
echo ""
echo -e "${CYAN}Quick Test:${NC}"
echo '  curl -X POST http://localhost:'$AGENT_PORT'/execute -H "Content-Type: application/json" -d '"'"'{"task": "show disk usage"}'"'"
echo ""
echo -e "${CYAN}View Logs:${NC}"
echo "  docker logs lab-agent -f"
echo "  docker logs lab-guardian -f"
echo ""
echo -e "${CYAN}Documentation:${NC}"
echo "  README.md - Project overview"
echo "  docs/INSTALL.md - Installation guide"
echo "  docs/CONFIGURATION.md - LLM provider setup"
echo "  docs/API.md - API reference"
echo ""

if [ "$AGENT_HEALTH" = true ] && [ "$GUARDIAN_HEALTH" = true ]; then
    echo -e "${GREEN}System is operational!${NC}"
else
    echo -e "${YELLOW}Some services failed health checks. Check logs for details.${NC}"
fi
