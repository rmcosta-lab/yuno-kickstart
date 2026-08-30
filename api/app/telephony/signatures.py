"""Bounded Twilio request-signature verification."""

import base64
import hashlib
import hmac
from collections.abc import Mapping, Sequence

type TwilioParameters = Mapping[str, str] | Sequence[tuple[str, str]]


def twilio_signature(url: str, parameters: TwilioParameters, auth_token: str) -> str:
    """Produce Twilio's HMAC-SHA1 signature for form-encoded callbacks."""

    items = list(parameters.items()) if isinstance(parameters, Mapping) else list(parameters)
    message = url + "".join(f"{name}{value}" for name, value in sorted(items))
    digest = hmac.new(auth_token.encode(), message.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_twilio_signature(
    url: str,
    parameters: TwilioParameters,
    signature: str | None,
    auth_token: str,
) -> bool:
    if not signature or not auth_token:
        return False
    expected = twilio_signature(url, parameters, auth_token)
    return hmac.compare_digest(signature.encode(), expected.encode())
