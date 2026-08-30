"""Pure-Python bounded G.711 mu-law/8 kHz to PCM16/24 kHz conversion."""

import base64
import binascii
import struct

MAX_TWILIO_AUDIO_BYTES = 8_000


def _decode_sample(value: int) -> int:
    value = ~value & 0xFF
    magnitude = ((value & 0x0F) << 3) + 0x84
    magnitude <<= (value & 0x70) >> 4
    sample = magnitude - 0x84
    return -sample if value & 0x80 else sample


def _encode_sample(sample: int) -> int:
    sample = max(-32635, min(32635, sample))
    sign = 0x80 if sample < 0 else 0
    magnitude = abs(sample) + 0x84
    exponent = max(0, magnitude.bit_length() - 8)
    exponent = min(exponent, 7)
    mantissa = (magnitude >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


def twilio_payload_to_pcm24(payload: str) -> bytes:
    try:
        mulaw = base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("media payload must be valid base64") from exc
    if not mulaw or len(mulaw) > MAX_TWILIO_AUDIO_BYTES:
        raise ValueError("media payload size is invalid")
    samples = [sample for value in mulaw for sample in (_decode_sample(value),) * 3]
    return struct.pack(f"<{len(samples)}h", *samples)


def pcm24_to_twilio_payload(audio: bytes) -> str:
    if not audio or len(audio) % 6 != 0:
        raise ValueError("PCM24 audio must contain complete three-sample groups")
    samples = struct.unpack(f"<{len(audio) // 2}h", audio)
    mulaw = bytes(_encode_sample(samples[index]) for index in range(0, len(samples), 3))
    if len(mulaw) > MAX_TWILIO_AUDIO_BYTES:
        raise ValueError("PCM24 audio exceeds the outbound frame limit")
    return base64.b64encode(mulaw).decode("ascii")


class Pcm24ToMulawConverter:
    """Stateful 3:1 downsampler that tolerates arbitrary even PCM chunks."""

    def __init__(self) -> None:
        self._phase = 0

    def convert(self, audio: bytes) -> str | None:
        if not audio or len(audio) % 2 != 0:
            raise ValueError("PCM24 audio must contain complete little-endian samples")
        samples = struct.unpack(f"<{len(audio) // 2}h", audio)
        encoded = bytearray()
        for sample in samples:
            if self._phase == 0:
                encoded.append(_encode_sample(sample))
            self._phase = (self._phase + 1) % 3
        if not encoded:
            return None
        if len(encoded) > MAX_TWILIO_AUDIO_BYTES:
            raise ValueError("PCM24 audio exceeds the outbound frame limit")
        return base64.b64encode(encoded).decode("ascii")
