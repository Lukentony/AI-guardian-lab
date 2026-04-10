# AI Guardian Lab — TODO / Ripresa Lavori

> Generato il 2026-04-10. Contiene tutto il necessario per riprendere senza rileggere la cronologia.

---

## Contesto rapido

Progetto di sicurezza per agent AI: intercetta comandi shell generati da LLM prima dell'esecuzione.
Pipeline L1 (binary allowlist) → L2 (regex) → L3 (intent coherence) → L4 (LLM).

**Repo:**
- GitHub: `https://github.com/Lukentony/AI-guardian-lab.git` (username: `Lukentony`)
- Gitea: `http://100.64.0.3:3001/Luca/AI-guardian-lab.git` (srv1, Tailscale)
- Deploy attivo: `/opt/ai-guardian-lab/` su srv1 (`100.64.0.3`)

**Ultimo commit pushato su entrambi i remote:** `bf03b2d`

**Fix già applicati (non rifare):**
- `docker-compose.yml`: port binding → `${GUARDIAN_BIND_IP:-127.0.0.1}:5000:5000`, healthcheck → `curl`
- `.env.example` + `install.sh`: `OLLAMA_HOST` → `OLLAMA_URL`
- `guardian/forensics/analyzer.py`: IP hardcoded rimosso, legge `OLLAMA_URL` da env; `json.loads` con try/except separato
- `README.md`: badge 100% precision/recall rimossi, nota metodologica aggiunta
- `.gitattributes`: normalizzazione LF
- `.gitignore`: backup db, file scratch locali

---

## PROBLEMI DA FIXARE (ordinati per priorità)

---

### CRITICO-1 — Nessun sandboxing per comandi eseguiti dall'agent

**Impatto:** L'agent esegue comandi LLM-generati direttamente in bash nel container. Nessuna protezione reale.

**File:** `agent/agent/main.py`, righe 57-79
```python
# ATTUALE (pericoloso):
result = subprocess.run(
    ["/bin/bash", "-c", command],   # comando arbitrario da LLM
    capture_output=True, text=True, timeout=30
)
```

**Fix minimo (documentazione — 10 min):**
In `agent/agent/main.py` sopra `run_command()` aggiungere:
```python
# WARNING: This executes LLM-generated commands directly in the container.
# DEMO/RESEARCH ONLY. Do NOT use in production without a proper sandbox
# (gVisor, Firejail, nsjail, or ephemeral VM).
```
In `README.md` aggiungere sezione subito dopo i badge:
```markdown
## Warning

This project is for research and demonstration purposes only.
The agent executes LLM-generated shell commands directly inside a container.
Do not run in production without a proper sandbox layer.
```

**Fix completo (docker-compose.yml, sotto `agent:`):**
```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
read_only: true
```

**Commit suggerito:** `docs: add sandbox warning to agent and README`

---

### CRITICO-2 — LLM failure fa fail-open (contraddice il principio del progetto)

**Impatto:** Se Ollama è down, il layer L4 approva tutto automaticamente.
Il README dichiara "fail-closed by default" ma il codice fa il contrario.

**File:** `guardian/guardian/intent.py`, righe 142-150
```python
# ATTUALE (fail-open — DA CAMBIARE):
except Exception as e:
    logger.error(f"LLM validation failed: {e}")
    return {
        "blocked": False,     # approva su errore LLM
        "reason": f"Approved (LLM error: {str(e)})",
        "intent_source": "llm_error",
        "confidence": 0.0
    }
```

**Fix:**
```python
# NUOVO:
except Exception as e:
    logger.error(f"LLM validation failed: {e}")
    fail_closed = os.environ.get("FAIL_CLOSED_ON_LLM_ERROR", "true").lower() == "true"
    return {
        "blocked": fail_closed,
        "reason": f"{'Blocked' if fail_closed else 'Approved'} (LLM unavailable: {str(e)})",
        "intent_source": "llm_error",
        "confidence": 0.0
    }
```

Aggiungere anche in `.env.example` e in `docker-compose.yml` (environment guardian):
```
FAIL_CLOSED_ON_LLM_ERROR=true
```

**Commit suggerito:** `fix(intent): make LLM failure behavior configurable via FAIL_CLOSED_ON_LLM_ERROR`

---

### CRITICO-3 — docs/ contiene ancora OLLAMA_HOST (stale)

**Impatto:** Un utente che segue la documentazione configura la variabile sbagliata.

**File e righe esatte:**
- `docs/CONFIGURATION.md:15` → `OLLAMA_HOST=http://host.docker.internal:11434`
- `docs/INSTALL.md:117`     → `OLLAMA_HOST=http://localhost:11434`
- `docs/INSTALL.md:213`     → `OLLAMA_HOST=0.0.0.0:11434 ollama serve`
- `docs/INSTALL.md:216`     → `OLLAMA_HOST=http://192.168.x.x:11434`

**Fix:** sostituire `OLLAMA_HOST` con `OLLAMA_URL` in tutti i docs. Comando rapido:
```bash
# (da WSL)
sed -i 's/OLLAMA_HOST/OLLAMA_URL/g' docs/CONFIGURATION.md docs/INSTALL.md
```

**Commit suggerito:** `docs: replace OLLAMA_HOST with OLLAMA_URL across documentation`

---

### ALTO-1 — tests/ copiata nell'immagine Docker di produzione

**File:** `guardian/Dockerfile`, riga 17
```dockerfile
COPY tests/ tests/   # da rimuovere
```

**Fix:** eliminare quella riga. Nessun altro cambiamento necessario.

**Commit suggerito:** `fix(dockerfile): remove tests/ from production image`

---

### ALTO-2 — CI GitHub Actions assente

**Da creare:** `.github/workflows/ci.yml`

**Nota NTFS:** la directory `.github/` non esiste e va creata da WSL con:
```bash
# (da WSL)
cmd.exe /c "mkdir C:\Users\anton\ai-lab-test\.github\workflows"
cmd.exe /c "type nul > C:\Users\anton\ai-lab-test\.github\workflows\ci.yml"
# poi scrivere il contenuto con python3 open(...)
```

**Contenuto ci.yml:**
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: pip install -r guardian/requirements.txt pytest
      - name: Run tests
        run: pytest tests/ -v
      - name: Docker smoke test
        run: |
          cp .env.example .env
          sed -i 's/API_KEY=CHANGE_ME/API_KEY=testkey123/' .env
          docker compose up -d --build guardian
          sleep 15
          curl -f -H "X-API-Key: testkey123" http://localhost:5000/health
          docker compose down
```

**Commit suggerito:** `ci: add GitHub Actions job (pytest + docker smoke test)`

---

### ALTO-3 — Rate limiter usa memory:// (non persistente)

**File:**
- `guardian/guardian/main.py:33` → `storage_uri="memory://"`
- `agent/agent/main.py` → stesso pattern

**Fix:** rendere configurabile tramite ENV:
```python
storage_uri=os.environ.get("RATE_LIMIT_STORAGE_URI", "memory://"),
```
Aggiungere a `.env.example`:
```
# Per produzione usare Redis: redis://redis:6379
# RATE_LIMIT_STORAGE_URI=memory://
```

**Commit suggerito:** `fix(limiter): make rate limit storage configurable via RATE_LIMIT_STORAGE_URI`

---

### MEDIO-1 — UI usa default http://lab-guardian:5000 (hostname sbagliato)

**File:** `ui/app.py:15`
```python
# ATTUALE:
GUARDIAN_API = os.environ.get("GUARDIAN_URL", "http://lab-guardian:5000")
# docker-compose passa GUARDIAN_URL=http://guardian:5000 quindi funziona
# ma il default hardcoded e' sbagliato (lab-guardian non esiste come service)
```

**Fix:**
```python
GUARDIAN_API = os.environ.get("GUARDIAN_URL", "http://guardian:5000")
```

**Commit suggerito:** `fix(ui): align default GUARDIAN_URL to docker-compose service name`

---

### MEDIO-2 — install.sh non scriptabile (nessuna modalita' non-interattiva)

**File:** `install.sh` — tutto interattivo con `read -p`

**Fix minimo:** aggiungere all'inizio:
```bash
NON_INTERACTIVE=${NON_INTERACTIVE:-false}
```
E wrappare ogni `read -p` con:
```bash
if [ "$NON_INTERACTIVE" != "true" ]; then
    read -p "..." variabile
else
    variabile="default"
fi
```

**Commit suggerito:** `fix(install): add NON_INTERACTIVE mode for CI`

---

### MINORE-1 — mask_secrets regex incompleta

**File:** `guardian/guardian/main.py:89`

**Fix:** aggiungere pattern a `secret_patterns`:
```python
(r'(?i)bearer\s+([A-Za-z0-9\-_\.]{20,})', r'bearer ***MASKED***'),
(r'[0-9a-f]{40,}', '***MASKED_HEX***'),
```

**Commit suggerito:** `fix(guardian): improve secret masking regex`

---

## Ordine esecuzione consigliato (prossima sessione)

| Step | Task | Tempo stimato |
|------|------|---------------|
| 1 | CRITICO-2: fail-closed intent.py | 15 min |
| 2 | CRITICO-1: warning sandbox README + agent | 10 min |
| 3 | CRITICO-3: OLLAMA_HOST → OLLAMA_URL nei docs | 5 min |
| 4 | ALTO-1: rimuovere COPY tests/ da Dockerfile | 2 min |
| 5 | MEDIO-1: fix default GUARDIAN_URL in ui/app.py | 2 min |
| 6 | ALTO-3: RATE_LIMIT_STORAGE_URI configurabile | 10 min |
| 7 | ALTO-2: GitHub Actions CI | 20 min |
| 8 | MEDIO-2: install.sh NON_INTERACTIVE | 30 min |

---

## Note operative (WSL + NTFS — leggere prima di iniziare)

**Push Gitea** (da WSL, Tailscale deve essere attivo):
```bash
git push http://Luca:24bab5cf1cf75bfd0c5b6710976c45ce1a83a12f@100.64.0.3:3001/Luca/AI-guardian-lab.git main
```

**Push GitHub** (da WSL, token gia' in ~/.git-credentials):
```bash
git push origin main
```

**Creare nuovi file** (directory NTFS owned da root — Write tool fallisce):
```bash
cmd.exe /c "type nul > C:\Users\anton\ai-lab-test\nuovo-file.txt"
python3 -c "open('/mnt/c/Users/anton/ai-lab-test/nuovo-file.txt','w',newline='\n').write('contenuto')"
```

**git merge/rebase/checkout -- . fallisce** con "unable to unlink" se VS Code ha i file aperti.
Soluzione: applicare diff manualmente con Edit tool invece di fare checkout.

**srv1 dopo ogni push:**
```bash
ssh nasvpn@100.64.0.3
cd /opt/ai-guardian-lab && git pull && docker compose up -d --build
```
Ricordare: nel .env su srv1 deve esserci `GUARDIAN_BIND_IP=100.64.0.3` (non in repo).
