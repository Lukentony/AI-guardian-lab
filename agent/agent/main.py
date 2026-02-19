from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import os
import re
import hmac
import subprocess
from litellm import completion

app = Flask(__name__)

GUARDIAN_URL = os.getenv('GUARDIAN_URL', 'http://guardian:5000')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://host.docker.internal:11434')
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')
LLM_MODEL_CODER = os.getenv('LLM_MODEL_CODER', 'qwen2.5-coder:7b')
API_KEY = os.getenv('API_KEY', '')

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

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
        text = re.sub(r'`', '', text)
    
    return text.strip()


def run_command(command):
    """Executes a bash command safely with a timeout."""
    try:
        # SEC-SAFE: We run the command via /bin/bash -c for flexibility, 
        # but within the containerized Agent environment.
        print(f"--- EXECUTION START: {command} ---")
        result = subprocess.run(
            ["/bin/bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"--- EXECUTION COMPLETE (Code: {result.returncode}) ---")
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 30s", "exit_code": 124}
    except Exception as e:
        print(f"CRITICAL: Failed to execute command: {e}")
        return {"error": str(e), "exit_code": 1}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/execute', methods=['POST'])
@limiter.limit("60 per minute")
def execute():
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
            # PHASE 1: Real command execution
            exec_result = run_command(command)
            
            return jsonify({
                "status": "executed",
                "command": command,
                "output": exec_result.get("stdout", ""),
                "stderr": exec_result.get("stderr", ""),
                "exit_code": exec_result.get("exit_code", 0),
                "error": exec_result.get("error", ""),
                "llm_provider": LLM_PROVIDER
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
