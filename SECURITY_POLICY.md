# AI LAB SECURITY POLICY

## CURRENT STATUS: STABLE / HARDENED

### Active Permissions (Zero-Trust)
✅ **Mandatory Binary Allowlist**: Binary execution is restricted to the `green` and `yellow` zones in `policy.yaml`.
✅ **Resource Quotas**: CPU and Memory limits are enforced per service to prevent Local DoS.
✅ **Non-Privileged Execution**: All services run as unprivileged Linux users (`agent`, `guardian`, `ui`).
✅ **Network Isolation**: Containers communicate within a private `agent-net` bridge with no exposed ports except for UI and Agent API.

### Hardened Configuration
🔒 **Fail-Closed Auth**: No `API_KEY` = No access.
🔒 **ReDoS Protection**: Mandatory 1.0s timeout on all security regex evaluations.
🔒 **Data Privacy**: Automatic masking of 10+ types of credentials in all audit logs.

---

## PRODUCTION MODE (Sandbox Ready)
The environment is now ready for autonomous agent experimentation. While not a "bulletproof fortress," it provides a robust defense-in-depth shield against common agent failures and prompt-injection-driven destructive commands.

---
**TRANSITION CHECKLIST**: 
- [x] Guardian tested (9/9)
- [x] Agent tested
- [x] Docker Compose resource limits verified
- [x] Unprivileged execution verified
- [x] Binary Allowlist verified

Last Update: 2026-02-19
Current Mode: **HARDENED**

---
*"Security and stability over feature bloat."*
