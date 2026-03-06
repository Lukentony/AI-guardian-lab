# Contributing to AI Guardian Lab

I'm glad you're interested in contributing! This is a personal project, and I'm always looking for ways to make it more secure and robust. To keep the project manageable and focused on its core philosophy, I have a few rules for contributions.

## How to Contribute

1.  **Open an issue first**: Before you write any code, please open an issue to discuss your proposed change. This ensures your work aligns with my security-first philosophy and avoids wasted effort.
2.  **Structuring Commit Messages**: I use clear, concise commit messages. Please follow this style:
    - `feat: [description]` for new features.
    - `fix: [description]` for bug fixes.
    - `docs: [description]` for documentation changes.
    - `chore: [description]` for maintenance/cleanup.
3.  **No Cloud Bloat**: I prioritize local execution. I will not accept contributions that add mandatory cloud dependencies without a robust, local fallback (like Ollama).

## Development and Testing

I won't merge any pull requests that break the existing test suite. Before submitting your PR, make sure all tests pass:

```bash
# From the project root
docker exec lab-guardian python3 -m pytest tests/ -v
```

If you add a new feature, you **must** include corresponding unit tests in the `tests/` directory.

## Security Disclosures

If you find a security vulnerability, please do **NOT** open a public issue. Email me directly or fix it in a private fork and notify me. I take security seriously and want to coordinate a fix before disclosing any flaws.

---

*"Security first. Because you can't control the randomness of an LLM with another random LLM."*
