# Attack Corpus

A categorized collection of attack scenarios used to validate AI Guardian Lab's detection capabilities.

Each file contains labeled examples in JSON format with the following schema:

```json
{
  "id": "string",
  "category": "string",
  "description": "string",
  "task": "string",
  "command": "string",
  "expected_verdict": "blocked" | "allowed",
  "expected_layer": "L1" | "L2" | "L3" | "L4" | null,
  "notes": "string"
}
```

## Categories

| File | Category | Scenarios |
|------|----------|-----------|
| `obfuscation.json` | Command obfuscation techniques | 8 |
| `reverse-shells.json` | Reverse shell and backdoor payloads | 6 |
| `exfiltration.json` | Data exfiltration attempts | 6 |
| `prompt-injection.json` | Prompt injection patterns that generate dangerous commands | 5 |

## Usage

Run the full corpus against a live Guardian instance:

```bash
for file in attack-corpus/*.json; do
  echo "=== $file ==="
  python3 -c "
import json, subprocess, sys
with open('$file') as f:
    cases = json.load(f)
for c in cases:
    r = subprocess.run(['curl','-s','-X','POST','http://localhost:5000/validate',
        '-H','Content-Type: application/json',
        '-H','X-API-Key: YOUR_API_KEY',
        '-d', json.dumps({'command': c['command'], 'task': c['task']})],
        capture_output=True, text=True)
    result = json.loads(r.stdout)
    verdict = 'blocked' if not result.get('approved') else 'allowed'
    status = '✓' if verdict == c['expected_verdict'] else '✗'
    print(f\"{status} [{c['id']}] {c['description']}: {verdict}\")
"
done
```

_This corpus is used for regression testing and to demonstrate Guardian's detection surface._
