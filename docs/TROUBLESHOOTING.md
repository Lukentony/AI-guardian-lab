# Troubleshooting / Risoluzione Problemi

[🇬🇧 English](#english) | [🇮🇹 Italiano](#italiano)

---

<a name="english"></a>
## 🇬🇧 English

If you encounter errors like `Ollama API error` or `500 Internal Server Error` during testing, follow these steps:

### 1. Check Ollama Models
Ensure you have the correct model pulled locally:
```bash
ollama list
```
You should see `qwen2.5-coder:1.5b` (or whatever model you selected).

### 2. Check Docker Logs
View the full logs of the Agent container to see the exact error:
```bash
docker logs lab-agent
```

### 3. Verify Connectivity
Test if the Agent container can reach Ollama on the host:
```bash
docker exec lab-agent curl http://host.docker.internal:11434/api/tags
```
If this fails, check your Docker Desktop settings (Allow connection to host).

### 4. Manual Test
You can manually trigger the agent using `curl`:
```bash
curl -X POST http://localhost:5001/execute \
     -H "Content-Type: application/json" \
     -H "X-API-Key: test_secret_key" \
     -d '{"task": "echo hello"}'
```

### 5. Model Selection
The `install.sh` script supports interactive model selection. Run it to easily configure your environment:
```bash
./install.sh
```
It will query your running Ollama instance and let you pick from available models.

---

<a name="italiano"></a>
## 🇮🇹 Italiano

Se incontri errori come `Ollama API error` o `500 Internal Server Error` durante i test, segui questi passaggi:

### 1. Controlla i Modelli Ollama
Assicurati di avere il modello corretto installato localmente:
```bash
ollama list
```
Dovresti vedere `qwen2.5-coder:1.5b` (o il modello che hai selezionato).

### 2. Controlla i Log di Docker
Visualizza i log completi del container Agent per vedere l'errore esatto:
```bash
docker logs lab-agent
```

### 3. Verifica la Connettività
Testa se il container Agent riesce a raggiungere Ollama sull'host:
```bash
docker exec lab-agent curl http://host.docker.internal:11434/api/tags
```
Se fallisce, controlla le impostazioni di Docker Desktop (Consenti connessione all'host).

### 4. Test Manuale
Puoi attivare manualmente l'agent usando `curl`:
```bash
curl -X POST http://localhost:5001/execute \
     -H "Content-Type: application/json" \
     -H "X-API-Key: test_secret_key" \
     -d '{"task": "echo ciao"}'
```

### 5. Selezione Modello
Lo script `install.sh` supporta la selezione interattiva del modello. Eseguilo per configurare facilmente il tuo ambiente:
```bash
./install.sh
```
Interrogherà la tua istanza Ollama in esecuzione e ti permetterà di scegliere tra i modelli disponibili.
