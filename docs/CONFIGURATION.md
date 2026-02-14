# AI Guardian Lab - Configuration Guide

## Overview

AI Guardian Lab uses **LiteLLM** for universal LLM provider support. You can configure:
- **Primary provider**: Main LLM for command generation
- **Fallback providers**: Automatic backup if primary fails
- **Model selection**: Different models for code generation vs explanation
- **Network settings**: Ports and Docker configuration

## Quick Configuration

### Minimal Setup (Ollama Local)

```env
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_CODER=qwen2.5-coder:7b
OLLAMA_MODEL_EXPLAIN=llama3.2:3b-instruct-q4_K_M
Minimal Setup (Cloud - Groq Free)
text
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
LLM_MODEL_CODER=llama-3.3-70b-versatile
LLM_MODEL_EXPLAIN=llama-3.1-8b-instant
LLM Provider Configuration
Ollama (Local/Remote)
Use Case: Privacy, offline work, no API costs

Local Installation:

text
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_CODER=qwen2.5-coder:7b
OLLAMA_MODEL_EXPLAIN=llama3.2:3b-instruct-q4_K_M
Remote Ollama Server:

text
LLM_PROVIDER=ollama
OLLAMA_HOST=http://<your-ollama-host-ip>:11434
OLLAMA_MODEL_CODER=deepseek-coder:6.7b
OLLAMA_MODEL_EXPLAIN=llama3.2:3b-instruct-q4_K_M
Docker Compose Access (from containers):

text
OLLAMA_HOST=http://host.docker.internal:11434
Recommended Models:

Code Generation: qwen2.5-coder:7b, deepseek-coder:6.7b, codellama:7b

Explanation: llama3.2:3b-instruct-q4_K_M, mistral:7b

General: llama3.1:8b, gemma2:9b

Pull Models:

bash
ollama pull qwen2.5-coder:7b
ollama pull llama3.2:3b-instruct-q4_K_M
OpenAI
Use Case: Best quality, production-grade, complex tasks

Configuration:

text
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
LLM_MODEL_CODER=gpt-4o
LLM_MODEL_EXPLAIN=gpt-4o-mini
Alternative Models:

Premium: gpt-4o (~$0.03/command)

Balanced: gpt-4o-mini (~$0.005/command)

Legacy: gpt-3.5-turbo (~$0.002/command)

Get API Key: https://platform.openai.com/api-keys

Anthropic Claude
Use Case: Smart reasoning, long context, safety-critical

Configuration:

text
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
LLM_MODEL_CODER=claude-3-5-sonnet-20241022
LLM_MODEL_EXPLAIN=claude-3-5-haiku-20241022
Available Models:

Premium: claude-3-5-sonnet-20241022 (~$0.015/command)

Fast: claude-3-5-haiku-20241022 (~$0.004/command)

Legacy: claude-3-opus-20240229 (~$0.075/command)

Get API Key: https://console.anthropic.com

DeepSeek
Use Case: Most cost-effective, high volume, budget-conscious

Configuration:

text
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
LLM_MODEL_CODER=deepseek-coder
LLM_MODEL_EXPLAIN=deepseek-chat
Cost: ~$0.001 per command (100x cheaper than OpenAI)

Get API Key: https://platform.deepseek.com

Google Gemini
Use Case: Multimodal tasks, Google ecosystem integration

Configuration:

text
LLM_PROVIDER=gemini
GEMINI_API_KEY=xxxxxxxxxxxxx
LLM_MODEL_CODER=gemini-1.5-pro
LLM_MODEL_EXPLAIN=gemini-1.5-flash
Available Models:

Premium: gemini-1.5-pro (long context)

Fast: gemini-1.5-flash (low latency)

Get API Key: https://makersuite.google.com/app/apikey

Groq
Use Case: FREE tier, fast inference, testing

Configuration:

text
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
LLM_MODEL_CODER=llama-3.3-70b-versatile
LLM_MODEL_EXPLAIN=llama-3.1-8b-instant
Available Models:

Large: llama-3.3-70b-versatile (best quality)

Fast: llama-3.1-8b-instant (low latency)

Mixtral: mixtral-8x7b-32768 (long context)

Free Tier: 30 requests/minute, no credit card required

Get API Key: https://console.groq.com

Azure OpenAI (Enterprise)
Use Case: Corporate deployments, compliance requirements

Configuration:

text
LLM_PROVIDER=azure
AZURE_API_KEY=xxxxxxxxxxxxx
AZURE_API_BASE=https://your-resource.openai.azure.com
AZURE_API_VERSION=2024-02-15-preview
LLM_MODEL_CODER=gpt-4
LLM_MODEL_EXPLAIN=gpt-35-turbo
LM Studio (Local GUI)
Use Case: Local models with user-friendly interface

Configuration:

text
LLM_PROVIDER=openai
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_API_KEY=lm-studio
LLM_MODEL_CODER=local-model
LLM_MODEL_EXPLAIN=local-model
Setup: Download from https://lmstudio.ai, load model, start server

Multi-Provider Fallback Setup
LiteLLM supports automatic fallback when primary provider fails.

Example 1: Ollama Primary + Groq Fallback
Use Case: Local speed, cloud reliability

text
# Primary: Ollama (fast, free, private)
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_CODER=qwen2.5-coder:7b
OLLAMA_MODEL_EXPLAIN=llama3.2:3b-instruct-q4_K_M

# Fallback: Groq (free tier)
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
How it works: LiteLLM tries Ollama first. If timeout/error, automatically uses Groq.

Example 2: Groq Primary + OpenAI Fallback
Use Case: Free tier daily use, paid backup for critical tasks

text
# Primary: Groq (free, fast)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
LLM_MODEL_CODER=llama-3.3-70b-versatile
LLM_MODEL_EXPLAIN=llama-3.1-8b-instant

# Fallback: OpenAI (paid, premium quality)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
Example 3: Multi-Cloud Redundancy
Use Case: Production high availability

text
# Primary: Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
LLM_MODEL_CODER=claude-3-5-sonnet-20241022
LLM_MODEL_EXPLAIN=claude-3-5-haiku-20241022

# Fallback 1: OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx

# Fallback 2: DeepSeek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
LiteLLM fallback order: anthropic → openai → deepseek

Model Selection Strategy
Code Generation Models (LLM_MODEL_CODER)
Requirements: Accurate bash/shell syntax, security awareness

Recommended:

Best Quality: gpt-4o, claude-3-5-sonnet-20241022

Balanced: qwen2.5-coder:7b (Ollama), llama-3.3-70b-versatile (Groq)

Fast/Cheap: deepseek-coder, gpt-4o-mini

Explanation Models (LLM_MODEL_EXPLAIN)
Requirements: Clear language, safety analysis

Recommended:

Best Quality: gpt-4o-mini, claude-3-5-haiku-20241022

Balanced: llama3.2:3b-instruct-q4_K_M (Ollama)

Fast/Cheap: llama-3.1-8b-instant (Groq), gemini-1.5-flash

Same Model for Both
You can use one model for both tasks:

text
LLM_MODEL_CODER=gpt-4o
LLM_MODEL_EXPLAIN=gpt-4o
Or separate for cost optimization:

text
LLM_MODEL_CODER=gpt-4o        # Premium for accuracy
LLM_MODEL_EXPLAIN=gpt-4o-mini # Cheaper for explanations
Network Configuration
Dynamic Network (Default)
AI Guardian Lab uses Docker DNS for container communication:

text
networks:
  agent-net:
    driver: bridge

services:
  guardian:
    networks:
      - agent-net
Container communication:

Agent → Guardian: http://guardian:5000

UI → Agent: http://agent:5001

Host → Services: http://localhost:5000, http://localhost:5001, http://localhost:8080

Custom Ports
Change ports in .env if conflicts exist:

text
GUARDIAN_PORT=5010
AGENT_PORT=5011
UI_PORT=8888
Then update docker-compose.yml:

text
services:
  guardian:
    ports:
      - "${GUARDIAN_PORT}:5000"
  agent:
    ports:
      - "${AGENT_PORT}:5001"
  ui:
    ports:
      - "${UI_PORT}:8080"
Static IPs (Advanced)
If you need predictable IPs:

text
networks:
  agent-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/24

services:
  guardian:
    networks:
      agent-net:
        ipv4_address: 172.30.0.3
Not recommended: Breaks portability across environments.

Security Pattern Configuration
Static Patterns
File: guardian/config/patterns.yaml

Contains hardcoded dangerous command patterns:

text
patterns:
  filesystem_destruction:
    - pattern: 'rm\s+-rf\s+/'
      severity: critical
      description: "Recursive delete from root"
    - pattern: 'mkfs\.'
      severity: critical
      description: "Format filesystem"

  privilege_escalation:
    - pattern: 'sudo\s+su\s+-'
      severity: high
      description: "Root shell access"
    - pattern: 'chmod\s+-R\s+777'
      severity: high
      description: "Insecure permissions"
Edit carefully: False positives can block legitimate commands.

Learned Patterns
File: guardian/config/learned_patterns.yaml

Dynamically updated when Guardian blocks commands:

text
- pattern: '\bdev\b'
  confidence: 45
  examples: ["/dev/sda", "format /dev/sdb"]
- pattern: '\bmkfs\b'
  confidence: 80
  examples: ["mkfs.ext4 /dev/sda1"]
Automatic updates: Guardian learns from rejected commands.

Policy Configuration
File: guardian/config/policy.yaml

Controls validation behavior:

text
auto_approve_threshold: 95
require_explanation: true
block_on_pattern_match: true
enable_pattern_learning: true
Settings:

auto_approve_threshold: Confidence % to skip user confirmation

require_explanation: Force LLM to explain dangerous commands

block_on_pattern_match: Immediately reject pattern matches

enable_pattern_learning: Update learned_patterns.yaml

Environment Variables Reference
Required
text
LLM_PROVIDER=ollama                    # Provider: ollama, openai, anthropic, etc.
GUARDIAN_URL=http://guardian:5000      # Guardian API endpoint
LLM Provider Keys (one required)
text
OLLAMA_HOST=http://localhost:11434     # Ollama server URL
OPENAI_API_KEY=sk-proj-xxx             # OpenAI API key
ANTHROPIC_API_KEY=sk-ant-xxx           # Anthropic API key
DEEPSEEK_API_KEY=sk-xxx                # DeepSeek API key
GEMINI_API_KEY=xxx                     # Google Gemini API key
GROQ_API_KEY=gsk_xxx                   # Groq API key
Model Selection
text
OLLAMA_MODEL_CODER=qwen2.5-coder:7b           # Ollama code model
OLLAMA_MODEL_EXPLAIN=llama3.2:3b-instruct     # Ollama explain model
LLM_MODEL_CODER=gpt-4o                        # Non-Ollama code model
LLM_MODEL_EXPLAIN=gpt-4o-mini                 # Non-Ollama explain model
Ports
text
GUARDIAN_PORT=5000                     # Guardian API port
AGENT_PORT=5001                        # Agent API port
UI_PORT=8080                           # Web dashboard port
Database
text
DB_PATH=/app/database/audit.db         # Audit log database path
Security
text
WORKSPACE_DIR=./workspace              # Command execution directory
EXEC_UID=1000                          # User ID for command execution
EXEC_GID=1000                          # Group ID for command execution
SANDBOX_MODE=false                     # Enable sandboxing (experimental)
Logging
text
LOG_LEVEL=INFO                         # DEBUG, INFO, WARN, ERROR
LOG_FORMAT=text                        # text or json
Pattern Learning
text
PATTERN_CONFIDENCE_THRESHOLD=30        # Min % to add learned pattern
PATTERN_LEARNING_SAMPLE_SIZE=100       # Max blocked commands to analyze
Testing Configuration
Validate Config
bash
./scripts/validate_config.sh
Checks:

.env file exists and valid

Required variables present

LLM provider accessible

Docker containers healthy

Test LLM Connection
Ollama:

bash
curl http://localhost:11434/api/tags
OpenAI:

bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
Groq:

bash
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY"
Test Command Generation
bash
curl -X POST http://localhost:5001/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "list files in current directory"}'
Expected response:

json
{
  "command": "ls -la",
  "status": "executed",
  "llm_provider": "ollama",
  "reason": ""
}
Troubleshooting
LLM Connection Timeout
Ollama: Check server running and accessible

bash
curl http://localhost:11434/api/tags
ollama list
Cloud Provider: Verify API key

bash
# Test key manually (see Testing section above)
# Check API quota/billing
Pattern Too Restrictive
Edit guardian/config/patterns.yaml, remove or modify pattern:

text
# Before (blocks ALL chmod)
- pattern: 'chmod'

# After (blocks only recursive 777)
- pattern: 'chmod\s+-R\s+777'
Restart Guardian:

bash
docker-compose restart guardian
Wrong Model Used
Check .env model names match provider:

Ollama: Use model names from ollama list
OpenAI: Use official model IDs (gpt-4o, not gpt4)
Anthropic: Use full model names (claude-3-5-sonnet-20241022)

Fallback Not Working
LiteLLM requires all provider keys configured. Add missing keys:

text
# Primary
LLM_PROVIDER=ollama

# Fallback keys (even if not primary)
GROQ_API_KEY=gsk_xxx
OPENAI_API_KEY=sk-xxx
Advanced Configuration
Custom LLM Endpoint
For self-hosted LLMs with OpenAI-compatible API:

text
LLM_PROVIDER=openai
OPENAI_API_BASE=http://your-llm-server:8000/v1
OPENAI_API_KEY=custom-key
LLM_MODEL_CODER=your-model-name
Load Balancing Multiple Ollama Instances
Use reverse proxy (nginx/traefik) in front of Ollama servers:

text
OLLAMA_HOST=http://ollama-lb.local:11434
Environment-Specific Configs
Use separate .env files:

bash
cp .env.example .env.production
cp .env.example .env.development

# Production: OpenAI
echo "LLM_PROVIDER=openai" > .env.production
echo "OPENAI_API_KEY=sk-xxx" >> .env.production

# Development: Ollama
echo "LLM_PROVIDER=ollama" > .env.development
echo "OLLAMA_HOST=http://localhost:11434" >> .env.development

# Use specific config
docker-compose --env-file .env.production up -d
Next Steps
Review SECURITY.md for production hardening

Check API.md for integration examples

Read INSTALL.md for deployment scenarios
