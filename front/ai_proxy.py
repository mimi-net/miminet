#!/usr/bin/env python3
"""
Простой HTTP прокси для Mistral API.
Запускается на хосте, принимает запросы от Flask-контейнера,
проксирует их к api.mistral.ai и возвращает ответ.

Запуск: python3 ai_proxy.py
"""
import json
import os
import sys
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 5050


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[proxy] {self.address_string()} - {format % args}")

    def do_POST(self):
        if self.path != "/chat":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body)
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        mistral_payload = json.dumps({
            "model": payload.get("model", "mistral-small-latest"),
            "messages": payload.get("messages", []),
        }).encode()

        req = urllib.request.Request(
            "https://api.mistral.ai/v1/chat/completions",
            data=mistral_payload,
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=240) as resp:
                result = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result)
        except urllib.error.HTTPError as e:
            error_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error_body)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())


if __name__ == "__main__":
    if not MISTRAL_API_KEY:
        print("ERROR: MISTRAL_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    server = HTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    print(f"[proxy] Listening on {LISTEN_HOST}:{LISTEN_PORT}")
    server.serve_forever()
