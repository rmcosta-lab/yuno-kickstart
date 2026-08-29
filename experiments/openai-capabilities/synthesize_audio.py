"""Create the private synthetic English WAV used by the Phase 02 WebSocket probe."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.openai.com/v1/audio/speech"
ROOT = Path(__file__).resolve().parent
PRIVATE_ROOT = ROOT / "private"
SYNTHETIC_REQUEST = "Please check availability for the synthetic reference S Y N 2042."


class SynthesisFailure(Exception):
    pass


def private_output_path(value: str) -> Path:
    path = Path(value).resolve()
    if not path.is_relative_to(PRIVATE_ROOT):
        raise argparse.ArgumentTypeError(f"output must be under {PRIVATE_ROOT}")
    if path.suffix.lower() != ".wav":
        raise argparse.ArgumentTypeError("output must use the .wav extension")
    return path


def synthesize(output: Path, timeout_seconds: float) -> dict[str, object]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SynthesisFailure("authentication")
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(
            {
                "model": "gpt-4o-mini-tts",
                "voice": "cedar",
                "input": SYNTHETIC_REQUEST,
                "instructions": (
                    "Speak clearly in natural English at a calm, measured pace. Pause briefly "
                    "between the request and the reference."
                ),
                "response_format": "wav",
            }
        ).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            audio = response.read()
            request_id = response.headers.get("x-request-id")
    except urllib.error.HTTPError as error:
        category = "authentication" if error.code in (401, 403) else "provider"
        raise SynthesisFailure(category) from error
    except TimeoutError as error:
        raise SynthesisFailure("timeout") from error
    except urllib.error.URLError as error:
        raise SynthesisFailure("network") from error
    if not audio.startswith(b"RIFF") or b"WAVE" not in audio[:16]:
        raise SynthesisFailure("invalid_audio")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(audio)
    return {
        "status": "passed",
        "model": "gpt-4o-mini-tts",
        "voice": "cedar",
        "format": "wav",
        "bytes": len(audio),
        "request_id": request_id,
        "output": output.name,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=private_output_path)
    parser.add_argument("--timeout", type=float, default=45.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = synthesize(args.output, args.timeout)
    except SynthesisFailure as error:
        print(json.dumps({"status": "failed", "failure_category": str(error)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
