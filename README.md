# AI Guardian Lab

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Docker](https://img.shields.io/badge/docker--compose-blue.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)

> [!IMPORTANT]
> **"Security first. Because you can't control the randomness of an LLM with another random LLM."**

---

## The Problem

Volevo usare un agente AI sulla mia macchina, ma non mi fidavo a dargli accesso alla shell senza controllo. I framework attuali non hanno un enforcement nativo sui tool e si affidano quasi esclusivamente alla compliance del modello o a prompt engineering fragile. Ho costruito Guardian come layer intermedio deterministico per togliere il potere decisionale finale all'LLM quando si tratta di eseguire comandi sul sistema.

## How it works

Il Guardian opera una pipeline di validazione a 4 layer. È "Fail-Closed" per design: se un layer ha un dubbio, il comando viene bloccato.

1.  **L1: Binary Allowlist**: Filtro immediato basato su zone di rischio (green, yellow, red). Se un binario non è esplicitamente permesso nel contesto attuale, l'esecuzione muore qui.
2.  **L2: Regex Pattern Matching**: Un motore dual-path ReDoS-safe che controlla sia il comando raw che quello normalizzato contro pattern di offuscamento, esfiltrazione e distruzione.
3.  **L3: Intent Coherence Mapping**: Questo è il differenziatore. Verifica che il comando sia coerente con il task assegnato classificandoli in famiglie di intenti (read, write, delete).
    - *Esempio: task="analyze disk usage" + command="rm -rf /tmp" -> **BLOCKED** (conflitto tra intent 'read' e azione 'delete').*
4.  **L4: LLM Semantic Check**: L'LLM è l'ultima risorsa. Viene interpellato solo per i casi ambigui che i layer deterministici non riescono a risolvere, aggiungendo un livello finale di comprensione semantica.

## Why determinism first

Ho dato priorità ai controlli deterministici rispetto alla validazione basata su LLM per tre motivi:
- **Trasparenza**: Puoi auditare le regex e le mappature. Sai esattamente perché un comando è stato bloccato.
- **Velocità**: I controlli deterministici richiedono millisecondi e zero token.
- **Affidabilità**: La logica non "allucina". Offre un confine rigido che nessun prompt injection può saltare.

## The integration wall

I framework per agenti bloccano per design le chiamate verso IP privati per protezione SSRF. È una scelta intenzionale e corretta, ma ha un effetto collaterale pesante: l'enforcement di Guardian oggi dipende dalla compliance del modello (che deve essere istruito a chiamare il middleware) e non da un hook hard nativo del framework. Questo è un problema aperto dell'intero ecosistema: l'enforcement automatico e inviolabile arriverà solo quando i framework implementeranno hook pre-tool nativi.

## Quick Start

#### 1. Installation
```bash
git clone https://github.com/Lukentony/AI-guardian-lab.git
cd ai-guardian-lab
./install.sh
```

#### 2. Start
```bash
docker-compose up -d
```

## Use cases reali

- **Local Testing**: Sviluppatori che testano agenti AI localmente e vogliono capire cosa tentano di fare prima di dare accesso totale.
- **Audit & Compliance**: Chi necessita di log immutabili di ogni singolo comando tentato da un agente, inclusi i rifiuti.
- **Hard Chokepoint**: Chi vuole un filtro reale tra LLM e shell senza sperare che il modello "si comporti bene" seguendo le system instructions.

## Threat Model & Limits

Guardian è uno scudo, non un miracolo:
1.  **Regex limitations**: Offuscamenti estremamente sofisticati potrebbero teoricamente evadere i pattern statici.
2.  **Normalization**: La varietà della sintassi shell è un battleground costante; alcuni edge case potrebbero richiedere aggiornamenti alle regole di normalizzazione.
3.  **Sandbox Dependency**: Guardian blocca i comandi, ma la sicurezza finale dipende anche dall'isolamento dell'ambiente (sandbox/docker) in cui l'agente gira.

## Documentation
- [Architecture & Layers](ARCHITECTURE.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY_POLICY.md)

---

## 📄 License
MIT License. Vedi [LICENSE](LICENSE) per i dettagli.
