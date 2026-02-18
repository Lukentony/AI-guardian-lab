# AI Guardian Lab - Security Audit Report

**Date**: 2026-02-13 (original) | **Updated**: 2026-02-18
**Status**: 5/6 Issues Fixed ✅

## Vulnerabilities Matrix

| ID | Issue | Severity | CVSS | Status |
|---|---|---|---|---|
| SEC-01 | API Authentication Missing | CRITICAL | 9.8 | ✅ **FIXED** (2026-02-18) |
| SEC-02 | Rate Limiting Absent | HIGH | 7.5 | ✅ **FIXED** (2026-02-18) |
| SEC-03 | Pattern Bypass (Encoding) | HIGH | 8.1 | ✅ **FIXED** (2026-02-18) |
| SEC-04 | Secrets Exposure in Logs | MEDIUM | 6.5 | ✅ **FIXED** (2026-02-18) |
| SEC-05 | Privilege Escalation (sudo) | MEDIUM | 7.2 | ✅ **FIXED** (2026-02-18) |
| SEC-06 | Command Injection (LLM) | LOW | 5.3 | ⚠️ OPEN |

---

## SEC-01: API Authentication — ✅ FIXED

**Fix applied**: `check_auth()` is now **fail-closed** in both `agent/main.py` and `guardian/main.py`. When `API_KEY` is not configured, all requests are rejected with 401. Authentication uses `hmac.compare_digest()` for constant-time comparison (timing-attack resistance).

**Residual risk**: API key is a shared secret (not per-user JWT). Acceptable for this lab project.

---

## SEC-02: Rate Limiting — ✅ FIXED

**Fix applied**: In-memory rate limiter added to Guardian (`/validate`, `/report`): 30 req/min per IP. Agent already had 60 req/min on `/execute`. Both use sliding-window counters with automatic garbage collection.

**Residual risk**: In-memory counters reset on container restart. Acceptable for non-production use.

---

## SEC-03: Pattern Bypass via Encoding — ✅ FIXED

**Fix applied**:
- `normalize_command()` now decodes **hex payloads** (`echo <hex> | xxd -r -p`) in addition to base64.
- **Subshell expansion**: `$(...)` and backtick wrappers are stripped, exposing inner commands to pattern matching.
- **IFS variants**: `$'\t'` and `$'\n'` are normalized.
- **15+ new patterns** added to `patterns.yaml`: subshell detection, pipe-to-netcat, sensitive file reads (`/etc/shadow`, `/etc/passwd`), `printenv`.

**Residual risk**: Exotic encodings (e.g., `printf '\x72\x6d'`) are not decoded. Deep encoding chains remain a theoretical risk.

---

## SEC-04: Secrets Exposure in Logs — ✅ FIXED

**Fix applied**: `mask_secrets()` is now applied in both `guardian/main.py` (`log_to_db()`) and `database/audit_logger.py` (`log_command()`). API keys (sk-..., gsk_...), tokens, and passwords are replaced with `***MASKED***` before database writes.

**Additional fix**: Removed debug `print()` in `agent/main.py` that leaked the first 4 characters of `API_KEY` to stdout.

---

## SEC-05: Privilege Escalation (sudo) — ✅ FIXED

**Fix applied**:
- Removed `^` anchor from sudo patterns—now catches `sudo` mid-command (e.g., `&& sudo rm -rf /`).
- Added patterns for: `sudo rm`, `sudo cat /etc/shadow`, `sudo chmod`, `sudo chown`, `sudo dd`, `pkexec`, `su -c`, `chown root`.
- Broader `chmod` detection: `chmod 4xx/7xx` numeric patterns.

---

## SEC-06: Command Injection via LLM — ⚠️ OPEN

**Risk**: If Guardian pattern matching fails to catch a malicious command, there is no final sanitization layer before the command string is returned to the user.

**Mitigation already in place**: The agent does **not** execute commands directly—it returns them in the API response. Actual execution is the caller's responsibility.

**Recommended future fix**: Add a final sanitizer that blocks or warns on chained commands (`;`, `&&`, `||`, `|`) unless explicitly allowed.

---

## Additional Findings (2026-02-18)

| Finding | Severity | Status |
|---|---|---|
| Debug print leaking API_KEY prefix in agent | LOW | ✅ Fixed |
| No CORS policy on Flask endpoints | INFO | Acceptable (internal Docker network) |
| SQLite has no encryption at rest | INFO | Acceptable for lab use |
| No TLS between containers | INFO | Acceptable (Docker bridge network) |

---

## Hardening Roadmap

### ✅ Phase 1: Critical Fixes (COMPLETED)
- SEC-01: Fail-closed API authentication
- SEC-03: Pattern bypass detection

### ✅ Phase 2: High Priority (COMPLETED)
- SEC-02: Rate limiting on all endpoints
- SEC-05: Comprehensive sudo/privilege escalation policy

### ✅ Phase 3: Medium Priority (COMPLETED)
- SEC-04: Secrets masking in all logging paths

### ⏳ Phase 4: Future Improvements
- SEC-06: Final command sanitizer (chain detection)
- Per-user JWT authentication
- SQLite encryption at rest (SQLCipher)
- TLS between containers (mTLS)
- CORS policy for production deployment
