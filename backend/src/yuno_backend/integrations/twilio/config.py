"""Redacted, immutable Twilio outbound-call configuration."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from ipaddress import ip_address
from types import MappingProxyType
from urllib.parse import urlsplit

__all__ = [
    "TwilioDestinationAllowlist",
    "TwilioHumanHandoffConfig",
    "TwilioOutboundCallConfig",
]

_ACCOUNT_SID = re.compile(r"^AC[0-9a-fA-F]{32}$")
_API_KEY_SID = re.compile(r"^SK[0-9a-fA-F]{32}$")
_E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_HOST_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_MAX_TIMEOUT_SECONDS = 60.0
_MAX_AUTHORIZATION_AGE_SECONDS = 3_600
_MAX_ATTEMPTS = 3


def _https_url(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a public HTTPS URL")
    parsed = urlsplit(value)
    hostname = parsed.hostname
    try:
        if hostname is not None:
            ip_address(hostname)
            is_ip_literal = True
        else:
            is_ip_literal = False
    except ValueError:
        is_ip_literal = False
    if (
        parsed.scheme != "https"
        or not hostname
        or "." not in hostname
        or len(hostname) > 253
        or hostname == "localhost"
        or is_ip_literal
        or any(_HOST_LABEL.fullmatch(label) is None for label in hostname.split("."))
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or bool(parsed.query)
        or bool(parsed.fragment)
    ):
        raise ValueError(f"{field_name} must be a public HTTPS URL")
    return value


def _e164(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _E164.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be an E.164 number")
    return value


@dataclass(frozen=True, slots=True)
class TwilioDestinationAllowlist:
    """Server-only label-to-number resolver with a redacted representation."""

    destinations: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.destinations, Mapping) or not self.destinations:
            raise ValueError("at least one allowlisted destination is required")
        validated: dict[str, str] = {}
        for label, number in self.destinations.items():
            if not isinstance(label, str) or _SAFE_LABEL.fullmatch(label) is None:
                raise ValueError("destination labels must be safe bounded identifiers")
            validated[label] = _e164(number, "allowlisted destination")
        object.__setattr__(self, "destinations", MappingProxyType(validated))

    def resolve(self, destination_label: str) -> str | None:
        """Resolve a public label without exposing the private mapping."""

        return self.destinations.get(destination_label)


@dataclass(frozen=True, slots=True)
class TwilioOutboundCallConfig:
    """Strict US1 Call-resource configuration with no injectable API origin."""

    account_sid: str = field(repr=False)
    api_key_sid: str = field(repr=False)
    api_key_secret: str = field(repr=False)
    from_e164: str = field(repr=False)
    instruction_url: str = field(repr=False)
    status_callback_url: str = field(repr=False)
    timeout_seconds: float = 10.0
    max_attempts: int = 2
    backoff_seconds: tuple[float, ...] = (0.25,)
    authorization_max_age_seconds: int = 300

    def __post_init__(self) -> None:
        if not isinstance(self.account_sid, str) or _ACCOUNT_SID.fullmatch(
            self.account_sid
        ) is None:
            raise ValueError("Twilio Account SID must be a valid AC SID")
        if not isinstance(self.api_key_sid, str) or _API_KEY_SID.fullmatch(
            self.api_key_sid
        ) is None:
            raise ValueError("Twilio API key SID must be a valid SK SID")
        if (
            not isinstance(self.api_key_secret, str)
            or not self.api_key_secret.strip()
            or len(self.api_key_secret) > 256
        ):
            raise ValueError("Twilio API key secret is required")
        _e164(self.from_e164, "Twilio caller ID")
        _https_url(self.instruction_url, "instruction_url")
        _https_url(self.status_callback_url, "status_callback_url")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int | float)
            or not math.isfinite(self.timeout_seconds)
            or not 0 < self.timeout_seconds <= _MAX_TIMEOUT_SECONDS
        ):
            raise ValueError("timeout must be positive and at most 60 seconds")
        if (
            not isinstance(self.max_attempts, int)
            or isinstance(self.max_attempts, bool)
            or not 1 <= self.max_attempts <= _MAX_ATTEMPTS
        ):
            raise ValueError("max_attempts must be between 1 and 3")
        if not isinstance(self.backoff_seconds, tuple):
            raise ValueError("backoff_seconds must be an immutable tuple")
        if len(self.backoff_seconds) < self.max_attempts - 1 or any(
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
            or not 0 <= value <= 10
            for value in self.backoff_seconds
        ):
            raise ValueError("bounded backoff is required between attempts")
        if (
            not isinstance(self.authorization_max_age_seconds, int)
            or isinstance(self.authorization_max_age_seconds, bool)
            or not 1
            <= self.authorization_max_age_seconds
            <= _MAX_AUTHORIZATION_AGE_SECONDS
        ):
            raise ValueError("authorization age must be between 1 and 3600 seconds")

    @property
    def create_call_url(self) -> str:
        return (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid}/Calls.json"
        )


@dataclass(frozen=True, slots=True)
class TwilioHumanHandoffConfig:
    """Strict server-only configuration for a bounded conference handoff."""

    account_sid: str = field(repr=False)
    api_key_sid: str = field(repr=False)
    api_key_secret: str = field(repr=False)
    coordinator_caller_id_e164: str = field(repr=False)
    status_callback_url: str = field(repr=False)
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not isinstance(self.account_sid, str) or _ACCOUNT_SID.fullmatch(
            self.account_sid
        ) is None:
            raise ValueError("Twilio Account SID must be a valid AC SID")
        if not isinstance(self.api_key_sid, str) or _API_KEY_SID.fullmatch(
            self.api_key_sid
        ) is None:
            raise ValueError("Twilio API key SID must be a valid SK SID")
        if (
            not isinstance(self.api_key_secret, str)
            or not self.api_key_secret.strip()
            or len(self.api_key_secret) > 256
        ):
            raise ValueError("Twilio API key secret is required")
        _e164(self.coordinator_caller_id_e164, "coordinator caller ID")
        _https_url(self.status_callback_url, "status_callback_url")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int | float)
            or not math.isfinite(self.timeout_seconds)
            or not 0 < self.timeout_seconds <= _MAX_TIMEOUT_SECONDS
        ):
            raise ValueError("timeout must be positive and at most 60 seconds")

    def call_url(self, call_sid: str) -> str:
        return (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid}/Calls/{call_sid}.json"
        )

    def participants_url(self, conference_name: str) -> str:
        return (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid}/Conferences/{conference_name}/Participants.json"
        )
