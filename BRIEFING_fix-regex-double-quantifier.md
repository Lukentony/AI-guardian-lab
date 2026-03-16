# Briefing — fix/regex-double-quantifier

*Branch: `fix/regex-double-quantifier` | File: `guardian/guardian/main.py`*

---

## Problema

All'avvio appaiono 5 WARNING e quei pattern non vengono caricati:

```
WARNING - Invalid regex [remote_execution]: wget.*??\|\s*sh — multiple repeat at position 7
WARNING - Invalid regex [remote_execution]: curl.*??\|\s*bash — multiple repeat at position 7
WARNING - Invalid regex [dangerous_find]: find\s+/.*??-exec\s+rm — multiple repeat at position 11
WARNING - Invalid regex [encoding_bypass]: python.*??-c — multiple repeat at position 9
WARNING - Invalid regex [exfiltration]: curl\s+.*??-X\s+POST — multiple repeat at position 10
```

## Causa

`safe_compile` sostituisce `.*` con `.*?` per prevenire ReDoS, ma `'.*' in 'wget.*?|sh'` è True perché `.*?` contiene `.*`. Risultato: `.*??` — doppio quantificatore, regex invalida.

```python
if '.*' in pattern_str:
    safe_str = pattern_str.replace('.*', '.*?')  # BUG: matcha anche dentro '.*?'
```

## Fix

Sostituire `str.replace` con un regex che usa negative lookahead, e loggare solo se la sostituzione è effettiva:

```python
safe_str = re.sub(r'\.\*(?!\?)', '.*?', pattern_str)
if safe_str != pattern_str:
    logger.info(f"Replaced greedy .* with .*? in pattern [{source}]: {pattern_str}")
    pattern_str = safe_str
```

Non riscrivere altro in `safe_compile` — solo questa modifica.

## Verifica

Dopo rebuild del container, nessun WARNING sui pattern esistenti e conteggio finale a 35:

```bash
docker compose up --build -d guardian
docker logs lab-guardian 2>&1 | grep -E "WARNING|initialized with"
```

## Feedback richiesto

1. Il negative lookahead è l'approccio più leggibile, o suggerisci un'alternativa nello stesso stile del codice?
2. Altri punti in `safe_compile` che meritano attenzione?
3. Vale la pena loggare quando un pattern viene skippato perché già non-greedy?
