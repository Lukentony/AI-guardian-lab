# Troubleshooting / Risoluzione problemi

[English](#english) | [Italiano](#italiano)

## English

Run these checks on the host running the lab, from a dedicated terminal at the
repository root. Do not paste `.env`, expanded Compose output or unredacted logs
into a public issue.

### A service does not start

Inspect service state first:

```bash
docker compose ps
```

Use the relevant service name when inspecting logs, for example
`docker compose logs guardian`. Check state-directory ownership against
`LOCAL_UID` and `LOCAL_GID`. Do not use chmod 777 or rerun the installer over an
existing `.env`; follow [Install](INSTALL.md) for upgrades.

### llama.cpp or semantic review fails

Run `docker compose logs --tail=100 llama` and `./guardian-lab doctor`. Check that
`state/models` is readable by the container and contains the pinned GGUF, that
`LLM_API_BASE` points to `http://llama:8080/v1`, and that the served alias matches
`LLM_MODEL`. `./guardian-lab models` re-downloads and verifies the artifact.

An unavailable or malformed required semantic response denies validation. Do not
turn off failure handling to get an approval. Use the
[authenticated dry-run example](API.md#authenticated-dry-run-example) to test
validation without executing a command.

### The UI returns 401 or 503

401 requires valid UI Basic credentials. A dashboard 503 can indicate an
unavailable Guardian audit API. Check Guardian and the UI backend credential;
do not work around the error by sharing the SQLite volume.

### The optional model will not start

The Kev CPU service starts only in the full profile. Its startup gate checks the
reviewed torch 2.13 runtime and the pinned Kev package. If it does not start, run
`guardian-lab doctor`, inspect the model download and the container logs, and do
not bypass the gate. An unavailable observer is not a safety verdict. See
[System One](SYSTEM_ONE.md).

## Italiano

Esegui questi controlli sul computer che ospita il lab, in un terminale dedicato
aperto nella directory principale del repository. Non pubblicare `.env`, output
Compose con variabili espanse o log contenenti dati riservati.

### Un servizio non parte

Controlla prima lo stato:

```bash
docker compose ps
```

Per i log usa il nome del servizio, per esempio `docker compose logs guardian`.
Verifica che il proprietario delle directory di stato corrisponda a `LOCAL_UID`
e `LOCAL_GID`. Non usare chmod 777 e non rilanciare l'installer su una `.env`
esistente. La procedura di aggiornamento è in [Install](INSTALL.md).

### llama.cpp o la verifica semantica non rispondono

Esegui `docker compose logs --tail=100 llama` e `./guardian-lab doctor`. Controlla
che `state/models` sia leggibile dal container e contenga il GGUF bloccato, che
`LLM_API_BASE` punti a `http://llama:8080/v1` e che l'alias servito corrisponda a
`LLM_MODEL`. `./guardian-lab models` riscarica e verifica l'artefatto.

Se una verifica semantica necessaria fallisce, il comando viene rifiutato. Non
disattivare questo controllo per ottenere un'approvazione. Usa
[l'esempio autenticato](API.md#authenticated-dry-run-example) per provare la
validazione senza eseguire comandi.

### La UI restituisce 401 o 503

401 richiede credenziali Basic valide per la UI. Un 503 nella dashboard può
indicare che l'API di audit di Guardian non risponde. Controlla Guardian e la
credenziale del backend UI; non condividere il volume SQLite per aggirare l'errore.

### Il modello opzionale non parte

Il servizio Kev CPU parte solo nel profilo full. Il controllo di avvio verifica
il runtime torch 2.13 approvato e il pacchetto Kev bloccato. Se non parte, esegui
`guardian-lab doctor`, controlla il download del modello e i log del container,
senza aggirare il controllo. Un osservatore non disponibile non è un verdetto di
sicurezza. Leggi [System One](SYSTEM_ONE.md).
