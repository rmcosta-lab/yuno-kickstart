"""Loopback-only server for the Phase 02 WebRTC capability harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
WEB_ROOT = ROOT / "web"
TOKEN_URL = "https://api.openai.com/v1/realtime/client_secrets"


def session_config(model: str) -> dict[str, Any]:
    return {
        "session": {
            "type": "realtime",
            "model": model,
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "turn_detection": {
                        "type": "server_vad",
                        "create_response": True,
                        "interrupt_response": True,
                    }
                },
                "output": {"voice": "cedar"},
            },
            "instructions": (
                "Always respond only in English. Speak at a calm, measured, conversational pace "
                "with natural pauses and a warm tone. Do not sound rushed or overly formal. Use "
                "the tool when the operator asks about synthetic reference SYN-2042."
            ),
            "tools": [
                {
                    "type": "function",
                    "name": "check_synthetic_availability",
                    "description": "Check a fully synthetic reference.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reference": {"type": "string", "enum": ["SYN-2042"]}
                        },
                        "required": ["reference"],
                        "additionalProperties": False,
                    },
                }
            ],
            "tool_choice": "auto",
        }
    }


class HarnessHandler(BaseHTTPRequestHandler):
    model = ""

    def log_message(self, format: str, *args: object) -> None:
        # Avoid request-body logging; the default line contains only method/path/status.
        super().log_message(format, *args)

    def _security_headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "microphone=(self)")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self' https://api.openai.com; media-src 'self' blob:",
        )

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self._security_headers("application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        paths = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
        }
        selected = paths.get(self.path)
        if selected is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        filename, content_type = selected
        body = (WEB_ROOT / filename).read_bytes()
        self.send_response(HTTPStatus.OK)
        self._security_headers(content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/token":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if self.headers.get("X-Phase02-Harness") != "1":
            self._json(HTTPStatus.FORBIDDEN, {"error": "invalid_harness_request"})
            return
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "authentication"})
            return
        request = urllib.request.Request(
            TOKEN_URL,
            data=json.dumps(session_config(self.model)).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "OpenAI-Safety-Identifier": hashlib.sha256(
                    b"phase-02-synthetic-operator"
                ).hexdigest(),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                provider_payload = json.loads(response.read())
            value = provider_payload.get("value")
            if not isinstance(value, str):
                raise ValueError("missing token value")
            self._json(
                HTTPStatus.OK,
                {"value": value, "expires_at": provider_payload.get("expires_at")},
            )
        except urllib.error.HTTPError as error:
            category = "authentication" if error.code in (401, 403) else "provider"
            self._json(HTTPStatus.BAD_GATEWAY, {"error": category, "status": error.code})
        except (OSError, ValueError, json.JSONDecodeError):
            self._json(HTTPStatus.BAD_GATEWAY, {"error": "provider"})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("Refusing non-loopback host", file=sys.stderr)
        return 2
    HarnessHandler.model = args.model
    try:
        server = ThreadingHTTPServer((args.host, args.port), HarnessHandler)
    except socket.gaierror:
        print("Unable to bind loopback server", file=sys.stderr)
        return 2
    print(f"Open http://{args.host}:{args.port} (model: {args.model})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
