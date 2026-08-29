"""Yuno raw-body HMAC-SHA256 signature verification."""

import base64
import binascii
import hashlib
import hmac


def _secret_bytes(secret: str | bytes) -> bytes:
    value = secret.encode("utf-8") if isinstance(secret, str) else secret
    if not value:
        message = "Webhook HMAC secret must not be empty"
        raise ValueError(message)
    return value


def compute_yuno_webhook_signature(payload: bytes, secret: str | bytes) -> str:
    """Compute Yuno's Base64-encoded SHA-256 HMAC over the exact body bytes."""

    digest = hmac.new(_secret_bytes(secret), payload, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_yuno_webhook_signature(
    payload: bytes,
    signature: str | None,
    secret: str | bytes,
) -> bool:
    """Return whether a header matches the raw body without leaking comparison timing."""

    if not signature:
        return False

    try:
        provided_digest = base64.b64decode(signature.encode("ascii"), validate=True)
        expected_digest = hmac.new(_secret_bytes(secret), payload, hashlib.sha256).digest()
    except (UnicodeEncodeError, ValueError, binascii.Error):
        return False

    return hmac.compare_digest(provided_digest, expected_digest)
