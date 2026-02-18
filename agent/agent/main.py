from flask import Flask, request, jsonify
import requests
import os
import re
import hmac
from litellm import completion

app = Flask(__name__)

GUARDIAN_URL = os.getenv('GUARDIAN_URL', 'http://guardian:5000')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://host.docker.internal:11434')
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')
LLM_MODEL_CODER = os.getenv('LLM_MODEL_CODER', 'qwen2.5-coder:7b')
API_KEY = os.getenv('API_KEY', '')

def check_auth():
    if not API_KEY:
        # FAIL CLOSED: reject all requests when no API_KEY is configured
        print("WARNING: API_KEY not set — rejecting request (fail-closed)")
        return False

    auth_header = request.headers.get('X-API-Key', '')
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(auth_header, API_KEY)

def get_auth_headers():
    if API_KEY:
        return {'X-API-Key': API_KEY}
    return {}

def clean_command(text):
    # Try to extract content inside ```bash ... ``` or ``` ... ```
    # This regex looks for code blocks and captures the inner content
    code_block_pattern = r'```(?:bash)?\s*(.*?)\s*```'
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        # Fallback: just strip delimiters if regex didn't match (maybe just single ticks or user sent code without blocks)
        text = re.sub(r'```bash\n?', '', text)
        text = re.sub(r'```\n?', '', text)
    
    return text.strip()

# Simple in-memory rate limiter
RATE_LIMIT = 60 # requests per minute
request_counts = {}

def is_rate_limited(ip):
    import time
    current_time = int(time.time())
    window_start = current_time // 60
    
    key = (ip, window_start)
    count = request_counts.get(key, 0)
    
    if count >= RATE_LIMIT:
        return True
    
    request_counts[key] = count + 1
    
    # Cleanup old keys (optional, simple garbage collection)
    if len(request_counts) > 1000:
        for k in list(request_counts.keys()):
            if k[1] < window_start:
                del request_counts[k]
                
    return False

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/execute', methods=['POST'])
def execute():
    # Rate Limit Check
    client_ip = request.remote_addr
    if is_rate_limited(client_ip):
        return jsonify({"error": "Too Many Requests", "retry_after": 60}), 429

    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    task = request.json.get('task', '')
    
    try:
        if LLM_PROVIDER == 'ollama':
            # Use direct requests for Ollama to avoid LiteLLM issues
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": LLM_MODEL_CODER,
                    "prompt": f"Generate a bash command for: {task}. Return ONLY the command, no markdown.",
                    "stream": False
                },
                timeout=30
            )
            if resp.status_code != 200:
                raise Exception(f"Ollama API error: {resp.text}")
            content = resp.json().get('response', '')
        else:
            response = completion(
                model=LLM_MODEL_CODER,
                messages=[{"role": "user", "content": f"Generate a bash command for: {task}"}]
            )
            content = response.choices[0].message.content
        
        command = clean_command(content)
        
        validation = requests.post(
            f"{GUARDIAN_URL}/validate",
            json={
                "command": command,
                "task": task,
                "llm_provider": LLM_PROVIDER
            },
            headers=get_auth_headers(),
            timeout=5
        )
        
        if validation.status_code == 401:
            return jsonify({"status": "error", "reason": "Guardian auth failed"}), 500
        
        val_data = validation.json()
        
        if val_data.get('approved'):
            return jsonify({
                "status": "executed",
                "command": command,
                "llm_provider": LLM_PROVIDER,
                "reason": ""
            }), 200
        else:
            return jsonify({
                "status": "rejected",
                "command": command,
                "reason": val_data.get('reason', ''),
                "explanation": val_data.get('reason', ''),
                "llm_provider": LLM_PROVIDER
            }), 200
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "reason": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
