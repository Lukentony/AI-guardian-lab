# Cleanup Notes

*To be reviewed and addressed after merging feat/intent-coherence.*

- **Environment Config (.env)**: There are residual configurations for Groq (`GROQ_API_KEY`, `LLM_PROVIDER=groq`, `LLM_MODEL_CODER=groq/llama-...`) which are unused since NUC2 does not have direct internet access.
- **Unused variables**: Consider cleaning up any references to other cloud providers in `.env.example` and `docker-compose.yml` if the project is strictly offline via Tailscale.
