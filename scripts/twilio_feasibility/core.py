"""Pure helpers for the disposable Twilio feasibility harness."""

from __future__ import annotations

import base64
import hashlib
import math
import secrets
from dataclasses import dataclass
from xml.etree import ElementTree

DISCLOSURE_SCRIPT = (
    "Olá. Eu sou Volta, um assistente automatizado de inteligência artificial operado "
    "pela equipe desta demonstração. Este é um teste técnico autorizado; ele não cria "
    "reserva nem compromisso real. Seu áudio será processado em tempo real para devolver "
    "uma resposta técnica, mas não será gravado nem armazenado."
)
CONSENT_PROMPT = "Para autorizar a continuação, pressione um. Para recusar, desligue."
DISCLOSURE_LANGUAGE = "pt-BR"


@dataclass(frozen=True)
class PublicUrls:
    """Canonical externally visible URLs used for signatures and TwiML."""

    base: str

    @classmethod
    def parse(cls, value: str) -> PublicUrls:
        normalized = value.rstrip("/")
        if not normalized.startswith("https://"):
            raise ValueError("TWILIO_PUBLIC_BASE_URL must start with https://")
        return cls(base=normalized)

    @property
    def twiml(self) -> str:
        return f"{self.base}/twilio/twiml"

    @property
    def consent(self) -> str:
        return f"{self.base}/twilio/consent"

    @property
    def status(self) -> str:
        return f"{self.base}/twilio/status"

    @property
    def media(self) -> str:
        return f"wss://{self.base.removeprefix('https://')}/twilio/media"


def disclosure_twiml(urls: PublicUrls) -> str:
    response = ElementTree.Element("Response")
    gather = ElementTree.SubElement(
        response,
        "Gather",
        {
            "action": urls.consent,
            "input": "dtmf",
            "method": "POST",
            "numDigits": "1",
            "timeout": "8",
        },
    )
    ElementTree.SubElement(
        gather, "Say", {"language": DISCLOSURE_LANGUAGE}
    ).text = DISCLOSURE_SCRIPT
    ElementTree.SubElement(gather, "Say", {"language": DISCLOSURE_LANGUAGE}).text = CONSENT_PROMPT
    ElementTree.SubElement(response, "Hangup")
    return ElementTree.tostring(response, encoding="unicode")


def consent_twiml(urls: PublicUrls, *, affirmed: bool) -> str:
    response = ElementTree.Element("Response")
    if not affirmed:
        ElementTree.SubElement(
            response, "Say", {"language": DISCLOSURE_LANGUAGE}
        ).text = "A autorização não foi recebida. O teste será encerrado agora."
        ElementTree.SubElement(response, "Hangup")
        return ElementTree.tostring(response, encoding="unicode")

    connect = ElementTree.SubElement(response, "Connect")
    stream = ElementTree.SubElement(connect, "Stream", {"url": urls.media})
    ElementTree.SubElement(
        stream,
        "Parameter",
        {"name": "evidence", "value": "phase03"},
    )
    return ElementTree.tostring(response, encoding="unicode")


def _pcm_to_mulaw(sample: int) -> int:
    """Encode one signed 16-bit PCM sample as ITU-T G.711 mu-law."""

    bias = 0x84
    clip = 32635
    sign = 0x80 if sample < 0 else 0
    magnitude = min(abs(sample), clip) + bias
    exponent = 7
    mask = 0x4000
    while exponent > 0 and not magnitude & mask:
        exponent -= 1
        mask >>= 1
    mantissa = (magnitude >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


def tone_frames(
    *,
    duration_ms: int = 500,
    frequency_hz: int = 400,
    sample_rate_hz: int = 8_000,
    frame_ms: int = 20,
) -> tuple[str, ...]:
    """Return headerless base64 mu-law frames for a bounded deterministic tone."""

    samples_per_frame = sample_rate_hz * frame_ms // 1_000
    total_samples = sample_rate_hz * duration_ms // 1_000
    amplitude = 8_000
    encoded = bytes(
        _pcm_to_mulaw(
            round(amplitude * math.sin(2 * math.pi * frequency_hz * index / sample_rate_hz))
        )
        for index in range(total_samples)
    )
    return tuple(
        base64.b64encode(encoded[index : index + samples_per_frame]).decode("ascii")
        for index in range(0, len(encoded), samples_per_frame)
    )


class SafeAliases:
    """Create process-local aliases without publishing provider identifiers."""

    def __init__(self, salt: bytes | None = None) -> None:
        self._salt = secrets.token_bytes(32) if salt is None else salt

    def for_value(self, value: str | None) -> str | None:
        if not value:
            return None
        digest = hashlib.sha256(self._salt + value.encode()).hexdigest()
        return f"alias-{digest[:12]}"
