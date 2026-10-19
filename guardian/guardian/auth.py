import hmac
import logging
import os

from flask import request

logger = logging.getLogger("guardian")

API_KEY = os.getenv("API_KEY", "")


def check_auth() -> bool:
    """
    Validates X-API-Key header against the configured API_KEY environment variable.
    Fail-closed: rejects all requests if API_KEY is not set.
    Uses constant-time comparison to prevent timing attacks.
    """
    if not API_KEY or API_KEY == "CHANGE_ME":
        logger.critical("CRITICAL: API_KEY not set — rejecting request (fail-closed)")
        return False

    auth_header = request.headers.get("X-API-Key", "")
    return hmac.compare_digest(auth_header.encode(), API_KEY.encode())
