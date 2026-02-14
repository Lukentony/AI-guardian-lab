# AI LAB SECURITY POLICY

## CURRENT STATUS: DEVELOPMENT MODE

### Active Permissions
✅ Access to Ollama server
   - Reason: Agent MVP testing and development
   - Risk: LOW - Ollama is isolated and contains no personal data

✅ Firewall configured for Docker debugging
   - Reason: Easy container debugging during development
   - Risk: LOW - Sandbox is already isolated from the primary network

⚠️ Agent Container on network with LAN access
   - Reason: Requires Ollama access while maintaining basic isolation
   - Solution: Implement routing through host or dedicated bridge

---

## PRODUCTION MODE (Sandbox)

### Security Rules to Activate
🔒 Total Isolation of Sandbox from LAN
🔒 Ollama access through dedicated Gateway/Proxy
🔒 Strict Firewall Rules
🔒 Container Network: Internal-only "agent-net"

---

**TRANSITION CHECKLIST**: Guardian tested, Agent tested, Docker Compose verified, E2E functional tests, Backup performed, Rollback scripts ready.

Last Update: 2026-02-14
Current Mode: DEVELOPMENT MODE
