#!/usr/bin/env python3
"""WSB-friendly local API to fetch ready Context Payloads by ID."""

from __future__ import annotations

import json
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
READY_DIR = ROOT / "tickets" / "ready"

HOST = os.environ.get("QF_WIZ_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("QF_WIZ_API_PORT", "8787"))
API_KEY = os.environ.get("QF_WIZ_API_KEY")

ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def json_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class PayloadHandler(BaseHTTPRequestHandler):
    server_version = "QFWizAPI/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        if not API_KEY:
            json_response(
                self,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "QF_WIZ_API_KEY is not set"},
            )
            return

        api_key = self.headers.get("X-API-Key")
        if api_key != API_KEY:
            json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized"})
            return

        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 2 or parts[0] != "payload":
            json_response(self, HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        ticket_id = parts[1]
        if not ID_PATTERN.match(ticket_id):
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid ticket id"})
            return

        path = (READY_DIR / f"{ticket_id}.json").resolve()
        if READY_DIR not in path.parents:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid ticket id"})
            return

        if not path.exists():
            json_response(self, HTTPStatus.NOT_FOUND, {"error": "Payload not found"})
            return

        try:
            raw = path.read_text(encoding="utf-8")
            json.loads(raw)
        except Exception:
            json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Invalid JSON payload"})
            return

        body = raw.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - stdlib signature
        message = format % args
        print(f"[qf-wiz-api] {self.address_string()} - {message}")


def main() -> None:
    READY_DIR.mkdir(parents=True, exist_ok=True)
    server = HTTPServer((HOST, PORT), PayloadHandler)
    print(f"[qf-wiz-api] Serving on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
