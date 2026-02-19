# Verification Report - AI Guardian Lab v1.2.0

**Date**: 2026-02-19
**Integrity Status**: **9/9 Tests Passed (100%)** ✅

## Summary of Results

| Test Category | Test Case | Status | Notes |
|---|---|---|---|
| **Normalization** | `test_normalize_command_ifs` | ✅ | Correctly handles tab/newline escapes. |
| **Normalization** | `test_normalize_command_encoding` | ✅ | Decodes hex payloads (xxd bypass). |
| **Normalization** | `test_normalize_command_subshells` | ✅ | Strips $() and backticks. |
| **Security Validation** | `test_dual_path_validation` | ✅ | Blocks both raw and normalized attacks. |
| **Security Validation** | `test_case_insensitive_matching` | ✅ | Blocks 'SUDO' bypasses. |
| **Robustness** | `test_command_length_limit` | ✅ | Rejects commands > 1024 chars. |
| **Privacy** | `test_secret_masking` | ✅ | Redacts sk-..., gsk_..., and API keys. |
| **Agent Integration** | `test_agent_command_cleanup` | ✅ | Sanitizes LLM markdown output. |
| **Agent Integration** | `test_agent_execution_mock` | ✅ | End-to-end command capture via Guardian. |

## Infrastructure Verification

### Unprivileged Shell Access
Verify that the `agent` container does not have root privileges:
```bash
docker exec lab-agent whoami
# Output: agent
```

### Resource Quotas
Verify that resource limits are applied:
```bash
docker stats --no-stream lab-agent lab-guardian
# Should show MEM LIMIT of 1024MiB and 512MiB respectively.
```

## Binary Allowlisting (Zonal)
Manual check for blocked binaries not in `policy.yaml`:
```bash
curl -X POST http://localhost:5001/execute \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"task": "run nmap"}'
# Result: "Blocked: Binary 'nmap' is not in the allowlist (Fail-Closed)"
```

---
*"Security and stability over feature bloat."*
