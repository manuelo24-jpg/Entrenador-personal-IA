from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from app.core.config import DATA_DIR, ensure_data_dirs

_ITERATIONS = 120_000
_CACHED_KEY: bytes | None = None


def _get_signing_key() -> bytes:
    """
    Retrieve the local HMAC signing key from environment (`EPIA_SECRET_KEY`)
    or auto-generate a persistent 256-bit random key in `data/.epia_secret`
    (gitignored) so no secret is ever hardcoded in source control.
    """
    global _CACHED_KEY
    env_val = os.environ.get("EPIA_SECRET_KEY", "").strip()
    if env_val:
        return env_val.encode("utf-8")

    if _CACHED_KEY is not None:
        return _CACHED_KEY

    ensure_data_dirs()
    key_file = DATA_DIR / ".epia_secret"
    if key_file.exists():
        raw = key_file.read_text(encoding="utf-8").strip()
        if len(raw) >= 32:
            _CACHED_KEY = raw.encode("utf-8")
            return _CACHED_KEY

    generated = secrets.token_hex(32)
    key_file.write_text(generated, encoding="utf-8")
    _CACHED_KEY = generated.encode("utf-8")
    return _CACHED_KEY


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random 16-byte salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _ITERATIONS,
    )
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2 hash."""
    try:
        algo, iter_str, salt, hex_digest = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(dk.hex(), hex_digest)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, email: str, name: str, expires_days: int = 30) -> str:
    """Create a signed HMAC-SHA256 token containing user identity."""
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "exp": int(time.time()) + expires_days * 86400,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    sig = hmac.new(
        _get_signing_key(),
        b64_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{b64_payload}.{sig}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a signed token. Returns None if invalid or expired."""
    try:
        b64_payload, sig = token.split(".", 1)
        expected_sig = hmac.new(
            _get_signing_key(),
            b64_payload.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        padding = "=" * (-len(b64_payload) % 4)
        raw_bytes = base64.urlsafe_b64decode(b64_payload + padding)
        data: dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))
        if int(data.get("exp", 0)) < int(time.time()):
            return None
        return data
    except Exception:
        return None
