# Project Roadmap

This document outlines the current status, planned features, and architectural evolution of **AI Guardian Lab**.

---

## 🚀 Status: v1.2.0 (Stable Demo)
The core multi-layer defense pipeline is implemented and verified through synthetic datasets.

### Current Features
- **L1 Binary Allowlist:** Prevents unauthorized binaries from executing in the shell.
- **L2 Regex Engine:** Detects obfuscation patterns (e.g., base64 in bash) and dangerous flags.
- **L3 Intent Coherence:** Cross-references the high-level task intent with the actual shell command actions.
- **L4 LLM Semantic Check:** Deep analysis of ambiguous commands for final validation.
- **Forensics API:** Detailed audit logging for post-incident analysis and pattern learning.

---

## 🛠️ Planned Improvements

### High Priority
- [ ] **Sandboxing (gVisor/Firejail):** Add a proper isolation layer for the agent container to prevent container escapes.
- [ ] **Advanced Pattern Learning:** Automated generation of regex patterns from blocked malicious attempts.
- [ ] **Fine-grained RBAC:** Implement Role-Based Access Control for the Guardian API.

### Medium Priority
- [ ] **Redis Backend for Rate Limiting:** Move from memory-based to persistent rate limiting for distributed deployments.
- [ ] **Interactive Dashboard (V2):** Enhanced visualizations of threat trends and decision reasoning.
- [ ] **Support for more LLM Providers:** Native integration for Anthropic and Azure OpenAI.

---

## 📈 Long-term Vision
Transform AI Guardian Lab from a demonstration middleware into a production-ready **Safety and Governance layer** for enterprise-grade AI agents, focusing on deterministic security with LLM-assisted oversight.
