# AI Guardian Lab - Installation Guide

## Prerequisites

- **Docker** 20.10+ and **Docker Compose** 1.29+
- **4GB RAM** minimum (8GB recommended for local LLM)
- **Internet connection** for cloud providers or Ollama model download
- **Optional**: Ollama installed locally or accessible remotely

## Quick Start (Recommended)

### 1. Clone Repository

```bash
git clone <repository-url>
cd ai-lab
2. Run Interactive Installer
bash
chmod +x install.sh
./install.sh
The wizard will guide you through:

Step 1: Ollama Detection

Automatically detects local Ollama installation

Prompts for remote Ollama host if not found locally

Suggests cloud alternatives if Ollama unavailable

Step 2: LLM Provider Selection

Ollama (Local - Recommended for privacy)

Free, private, runs offline

Models: qwen2.5-coder, deepseek-coder, llama3.2

Groq (Cloud - FREE tier)

Fast inference, generous free quota

No credit card required

OpenAI (Cloud - Paid)

Best quality, GPT-4o

~$0.01-0.03 per command

Anthropic Claude (Cloud - Paid)

Smart reasoning, safety-focused

~$0.015 per command

DeepSeek (Cloud - Paid)

Most cost-effective

~$0.001 per command (100x cheaper than OpenAI)

Google Gemini (Cloud - Paid)

Step 3: API Key Configuration

Tests connectivity before proceeding

Validates API keys automatically

Supports multi-provider fallback setup

Step 4: Port Configuration

Default ports: 5000 (Guardian), 5001 (Agent), 8080 (UI)

Customizable if conflicts exist

Step 5-8: Automatic build and deployment

Generates .env file

Builds Docker images

Starts services with health checks

3. Verify Installation
After installation completes, test the system:

bash
# Test safe command (should execute)
curl -X POST http://localhost:5001/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "show disk usage"}'

# Test dangerous command (should be blocked)
curl -X POST http://localhost:5001/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "format disk with mkfs.ext4"}'
Access Web Dashboard: http://localhost:8080

Manual Installation
1. Clone Repository
bash
git clone <repository-url>
cd ai-lab
2. Configure Environment
bash
cp .env.example .env
nano .env
Minimum required configuration:

For Ollama (local):

text
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_CODER=qwen2.5-coder:7b
OLLAMA_MODEL_EXPLAIN=llama3.2:3b-instruct-q4_K_M
For Groq (cloud free):

text
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
LLM_MODEL_CODER=llama-3.3-70b-versatile
LLM_MODEL_EXPLAIN=llama-3.1-8b-instant
For OpenAI (cloud):

text
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
LLM_MODEL_CODER=gpt-4o
LLM_MODEL_EXPLAIN=gpt-4o-mini
See CONFIGURATION.md for all provider options.

3. Build Docker Images
bash
docker build -t guardian-mvp:latest -f guardian/Dockerfile guardian/
docker build -t agent-mvp:latest -f agent/Dockerfile agent/
docker build -t ui-mvp:latest -f ui/Dockerfile ui/
4. Start Services
bash
docker-compose up -d
5. Verify Health
bash
docker ps | grep lab-
docker logs lab-agent --tail 20
docker logs lab-guardian --tail 20
Installation Scenarios
Scenario 1: Local Machine with Ollama
Best for: Privacy, offline work, development

Install Ollama: https://ollama.ai/download

Pull models: ollama pull qwen2.5-coder:7b

Run installer: ./install.sh → Select Ollama

Result: Fully private, no API costs

Scenario 2: Cloud-Only (No Local LLM)
Best for: Quick testing, no GPU available

Get Groq API key (free): https://console.groq.com

Run installer: ./install.sh → Select Groq

Result: Fast inference, free tier limits

Scenario 3: Remote Ollama Server
Best for: Team setup, shared LLM infrastructure

Note your Ollama server IP (e.g., 192.168.x.x:11434)

Run installer: ./install.sh → Enter remote host

Result: Centralized LLM, multiple Guardian instances

Scenario 4: Hybrid Setup (Ollama + Cloud Fallback)
Best for: Production reliability

Configure Ollama as primary

Add Groq/OpenAI API key during wizard

LiteLLM automatically falls back on Ollama failure

Result: Local speed + cloud reliability

Ollama Setup
Install Ollama
Linux:

bash
curl -fsSL https://ollama.ai/install.sh | sh
macOS/Windows: Download from https://ollama.ai

Pull Recommended Models
bash
# Code generation (7GB)
ollama pull qwen2.5-coder:7b

# Alternative: DeepSeek Coder (4GB)
ollama pull deepseek-coder:6.7b

# Explanation (lighter, 2GB)
ollama pull llama3.2:3b-instruct-q4_K_M
Remote Ollama Access
If running Ollama on another machine:

bash
# On Ollama host, allow external connections
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# In Guardian .env, set remote host
OLLAMA_HOST=http://192.168.x.x:11434
Post-Installation
Validate Configuration
bash
./scripts/validate_config.sh
View Logs
bash
docker logs lab-agent -f
docker logs lab-guardian -f
docker logs lab-ui -f
Test Commands
bash
# Safe command (approved)
curl -X POST http://localhost:5001/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "list files in current directory"}'

# Dangerous command (blocked)
curl -X POST http://localhost:5001/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "delete all files with rm -rf"}'
Access Web UI
Open browser: http://localhost:8080

Troubleshooting
Port Already in Use
bash
docker-compose down
# Change ports in .env
nano .env
# Update: GUARDIAN_PORT=5010, AGENT_PORT=5011, UI_PORT=8888
docker-compose up -d
Ollama Connection Failed
bash
# Test Ollama directly
curl http://localhost:11434/api/tags

# If remote Ollama, check firewall
ping <ollama-host-ip>
telnet <ollama-host-ip> 11434
Guardian Blocks Everything
bash
# Check pattern loading
docker logs lab-guardian | grep "INIT"

# Expected output:
# [INIT] Loaded 12 static patterns from YAML
# [INIT] Loaded 6 learned patterns

# Review patterns
cat guardian/config/patterns.yaml
API Key Invalid
bash
# Test OpenAI key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"

# Test Groq key
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"

# Update in .env
nano .env
docker-compose restart
Container Won't Start
bash
# Check logs for errors
docker logs lab-agent
docker logs lab-guardian

# Common issues:
# - Missing requirements.txt (rebuild images)
# - Port conflicts (change ports in .env)
# - Network conflicts (docker network prune)
LLM Response Timeout
bash
# Increase timeout in agent/main.py or use faster model
# For Ollama: Use smaller models (llama3.2:3b vs 70b)
# For cloud: Use fast models (gpt-4o-mini, claude-haiku, groq)
Uninstall
bash
cd ai-lab
docker-compose down -v
docker rmi guardian-mvp:latest agent-mvp:latest ui-mvp:latest
rm -rf database/ workspace/
Next Steps
Read CONFIGURATION.md for advanced LLM setup

Review SECURITY.md for hardening production deployments

Check API.md for integration examples

Customize patterns in guardian/config/patterns.yaml

Support
Documentation: docs/ folder

Issues: GitHub Issues

Configuration help: CONFIGURATION.md

Security concerns: SECURITY.md
