# AI Guardian Lab - Security Guide

## Fixed Vulnerabilities (v1.1.0)

### ✅ SEC-01: API Authentication (CRITICAL - FIXED)
**Status**: Resolved in v1.1.0

All endpoints now require `X-API-Key` header for authentication.

**Implementation**:
- API key auto-generated during installation
- Guardian and Agent validate key on every request
- 401 Unauthorized returned for missing/invalid keys

**Usage**:
```bash
API_KEY=$(grep "^API_KEY=" .env | cut -d'=' -f2)
curl -X POST http://localhost:5001/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "show disk usage"}'
✅ SEC-03: Pattern Bypass Prevention (CRITICAL - FIXED)
Status: Resolved in v1.1.0

Command normalization prevents obfuscated attacks.

Techniques Blocked:

Backslash escaping: r\m -rf / → normalized to rm -rf / → BLOCKED

Variable substitution: rm${IFS}-rf → normalized to rm -rf → BLOCKED

Base64 encoding: echo cm0gLXJm | base64 -d → decoded → BLOCKED

Whitespace manipulation: rm -rf → normalized → BLOCKED

Test Results:

rm -rf / → ❌ BLOCKED

r\m -rf /home → ❌ BLOCKED (after normalization)

mk\fs.ext4 /dev/sda → ❌ BLOCKED (after normalization)

df -h → ✅ APPROVED

Active Vulnerabilities
HIGH
SEC-02: Input Sanitization
Agent accepts raw natural language without pre-validation.

Mitigation: Use firewall to restrict API access.

SEC-04: Audit Log Tampering
SQLite database not encrypted or signed.

Mitigation: Run containers as non-root, mount database read-only from host.

MEDIUM
SEC-05: LLM Prompt Injection
Malicious task descriptions might manipulate LLM output.

Mitigation: Modern LLMs (Ollama qwen2.5-coder, GPT-4) have built-in safety filters. Test showed LLM refused to generate rm -rf commands.

SEC-06: Container Escape
Containers run without user namespace isolation.

Mitigation: Use LAB mode with firewall restrictions. Avoid exposing ports to public internet.

Best Practices
Deployment
✅ Use firewall to limit API access (only trusted IPs)

✅ Never expose Agent port (5001) to public internet

✅ Rotate API key periodically

✅ Monitor audit.db for suspicious patterns

✅ Keep patterns.yaml updated with new threats

Configuration
✅ Use Ollama local for privacy-sensitive environments

✅ Use cloud providers (Groq, OpenAI) with API rate limiting

✅ Enable audit logging to track all commands

✅ Review learned patterns before enabling (confidence >80%)

Monitoring
✅ Check docker logs lab-guardian for blocked commands

✅ Query audit.db weekly: SELECT * FROM command_history WHERE guardian_approved=0

✅ Alert on repeated pattern matches (potential attack)

Hardening Roadmap
Phase 1: Core Security (COMPLETED ✅)
✅ API Authentication

✅ Command normalization

✅ Pattern-based blocking

Phase 2: Enhanced Protection (Planned)
⏳ JWT-based authentication with expiry

⏳ Rate limiting per API key

⏳ Audit log encryption (SQLCipher)

⏳ Input validation before LLM call

Phase 3: Advanced Detection (Planned)
⏳ ML-based anomaly detection

⏳ Behavioral analysis (repeated suspicious tasks)

⏳ Real-time security dashboard

⏳ Webhook alerts for critical blocks

Reporting Security Issues
Report vulnerabilities via GitHub Issues with label security.

DO NOT disclose exploits publicly before fix is available.

Last Updated: 2026-02-13
Version: 1.1.0 (Security Hardened)
