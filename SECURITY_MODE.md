# MODALITÀ SICUREZZA LAB AI

## STATO ATTUALE: DEV MODE (Fase 0-3)

### Deroghe Attive
✅ NUC2 può accedere a 192.168.0.50:11434 (Ollama)
   Motivo: Testing e sviluppo Agent MVP
   Rischio: MEDIO - PC Ollama esposto ma senza dati critici
   Scadenza: Fine Fase 3 (Test Funzionale)

✅ Firewall NUC2 aperto
   Motivo: Facilità debug container Docker
   Rischio: BASSO - NUC2 già isolato da NUC1
   Scadenza: Fine Fase 3

⚠️ Container Agent su rete con accesso LAN
   Motivo: Accesso Ollama mantenendo isolamento base
   Soluzione: Macvlan o routing via NUC2 host

---

## FASE 4: LAB MODE (Produzione Sandbox)

### Regole che verranno attivate
🔒 Isolamento Totale NUC2 da LAN
🔒 Ollama Proxy su NUC1 (10.10.10.1:11434)
🔒 Firewall NUC2 Restrittivo
🔒 Container Network: Solo agent-net interna

---

CHECKLIST TRANSIZIONE: Guardian testato, Agent testato, Docker Compose OK, Test E2E, Backup, Script rollback

Ultimo Aggiornamento: 10/02/2026 13:23 CET
Modalità Corrente: DEV MODE
