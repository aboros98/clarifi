"""Supabase JWT authentication.

Verifies JWT tokens from Supabase Auth. Extracts user_id (sub claim).
Falls back to anonymous in dev mode (no SUPABASE_JWT_SECRET set).
"""

import base64
import json
import logging

from fastapi import HTTPException, Request

from clarifi.config import settings

logger = logging.getLogger(__name__)


def get_user_id(request_or_ws) -> str:
    """Extract and verify user_id from Supabase JWT.

    In production (SUPABASE_JWT_SECRET set): verifies signature with HMAC-SHA256.
    In dev (no secret): decodes without verification, logs a warning.
    Returns 'anonymous' if no token present.
    """
    auth = None
    if hasattr(request_or_ws, "headers"):
        auth = request_or_ws.headers.get("authorization", "")

    if not auth or not auth.startswith("Bearer "):
        return "anonymous"

    token = auth.split(" ", 1)[1]

    # If we have the JWT secret, verify properly
    if settings.supabase_jwt_secret:
        return _verify_supabase_jwt(token)

    # Dev mode: decode without verification
    logger.debug("No SUPABASE_JWT_SECRET — decoding JWT without verification")
    return _decode_jwt_unsafe(token)


def require_auth(request: Request) -> str:
    """Like get_user_id but raises 401 if not authenticated."""
    user_id = get_user_id(request)
    if user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


def _verify_supabase_jwt(token: str) -> str:
    """Verify Supabase JWT with HMAC-SHA256 and extract sub."""
    import hmac
    import hashlib

    try:
        parts = token.split(".")
        if len(parts) != 3:
            return "anonymous"

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        secret = settings.supabase_jwt_secret.encode()
        message = f"{header_b64}.{payload_b64}".encode()
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(secret, message, hashlib.sha256).digest()
        ).rstrip(b"=").decode()

        actual_sig = signature_b64.rstrip("=")

        if not hmac.compare_digest(expected_sig, actual_sig):
            logger.warning("JWT signature verification failed")
            return "anonymous"

        # Decode payload
        payload = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))

        # Check expiration
        import time
        exp = data.get("exp", 0)
        if exp and time.time() > exp:
            logger.warning("JWT expired")
            return "anonymous"

        return data.get("sub", "anonymous")

    except Exception:
        logger.warning("JWT verification error", exc_info=True)
        return "anonymous"


def _decode_jwt_unsafe(token: str) -> str:
    """Decode JWT without verification (dev mode only)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("sub", "anonymous")
    except Exception:
        return "anonymous"
