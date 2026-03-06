import os
import shlex
import re
import json
import logging
from litellm import completion

logger = logging.getLogger("guardian.intent")

INTENT_FAMILIES = {
    "read":    ["ls", "cat", "head", "tail", "find", "grep", "stat", "file", "du", "df"],
    "write":   ["cp", "mv", "mkdir", "touch", "tee", "chmod", "chown", "ln"],
    "delete":  ["rm", "rmdir", "shred", "truncate"],
    "network": ["curl", "wget", "nc", "ssh", "scp", "rsync", "ping"],
    "process": ["kill", "pkill", "systemctl", "service", "reboot", "shutdown"],
    "exec":    ["bash", "sh", "python", "python3", "perl", "ruby", "node"],
}

TASK_KEYWORDS = {
    "read":    ["list", "show", "check", "read", "view", "display", "get", "find", "search"],
    "write":   ["create", "write", "save", "copy", "move", "rename", "update"],
    "delete":  ["delete", "remove", "clean", "clear", "purge", "wipe"],
    "network": ["download", "upload", "fetch", "send", "connect", "ping"],
    "process": ["stop", "start", "restart", "kill", "reboot"],
    "exec":    ["run", "execute", "launch", "start"],
}

BLOCKED_COMBINATIONS = {
    ("read", "delete"),
    ("read", "process"),
    ("read", "exec"),
    ("write", "delete"),
    ("write", "process"),
    ("network", "exec"),
}

def classify_command(command: str) -> str:
    """Classifies a command into an intent family based on its first token."""
    if not command:
        return None
        
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
        
    if not tokens:
        return None
        
    binary = os.path.basename(tokens[0])
    
    for family, members in INTENT_FAMILIES.items():
        if binary in members:
            return family
            
    return None

def classify_task(task: str) -> str:
    """Classifies a task into an intent family based on keywords."""
    if not task or len(task.strip()) <= 5:
        return None
        
    task_lower = task.lower()
    # Simple word tokenization
    words = re.findall(r'\b\w+\b', task_lower)
    
    for family, keywords in TASK_KEYWORDS.items():
        for word in words:
            if word in keywords:
                return family
                
    return None

def check_intent_mapping(command: str, task: str) -> dict:
    """
    Checks if command and task map to conflicting intent families.
    Returns: {"blocked": bool, "reason": str, "intent_source": str, "needs_llm": bool}
    """
    # Skip if task is too short or missing
    if not task or len(task.strip()) <= 5:
        return {"blocked": False, "reason": "Approved (task too short or missing)", "intent_source": "skip", "needs_llm": False}
        
    cmd_family = classify_command(command)
    task_family = classify_task(task)
    
    if not cmd_family or not task_family:
        return {"blocked": False, "reason": "Requires LLM validation", "intent_source": "mapping", "needs_llm": True}
        
    combo = (cmd_family, task_family)
    
    if combo in BLOCKED_COMBINATIONS:
        reason = f"Blocked by Intent Mapping: Command family '{cmd_family}' conflicts with task family '{task_family}'"
        return {"blocked": True, "reason": reason, "intent_source": "mapping", "needs_llm": False}
        
    # If not blocked, but both classified
    return {"blocked": False, "reason": "Approved by Intent Mapping", "intent_source": "mapping", "needs_llm": False}

def check_intent_llm(command: str, task: str) -> dict:
    """
    Validates coherence using LLM for ambiguous cases.
    """
    model = os.getenv("INTENT_LLM_MODEL", "ollama/deepseek-coder-v2:16b")
    api_base = os.getenv("OLLAMA_URL", "http://localhost:11434")
    
    prompt = f"""You are a security validator. Given a task description and a shell command, determine if the command is coherent with the task.
Respond ONLY with valid JSON: {{"coherent": bool, "confidence": float 0-1, "reason": "short string"}}

Task: {task}
Command: {command}"""

    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_base=api_base,
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        coherent = result.get('coherent', True)  # default to true if missing
        confidence = float(result.get('confidence', 0.0))
        reason = result.get('reason', 'LLM analysis complete')
        
        # Blocco se coherent=false AND confidence >= 0.7. Sotto soglia -> approvato ma motivo scritto in audit
        blocked = (not coherent) and (confidence >= 0.7)
        
        if blocked:
            final_reason = f"Blocked by LLM (confidence {confidence:.2f}): {reason}"
        else:
            final_reason = f"Approved by LLM (coherent={coherent}, confidence={confidence:.2f}): {reason}"
            
        return {
            "blocked": blocked,
            "reason": final_reason,
            "intent_source": "llm",
            "confidence": confidence
        }
        
    except Exception as e:
        logger.error(f"LLM validation failed: {e}")
        # Fail-open for LLM fallback errors to avoid completely breaking the system if Ollama is down
        return {
            "blocked": False,
            "reason": f"Approved (LLM error: {str(e)})",
            "intent_source": "llm_error",
            "confidence": 0.0
        }
