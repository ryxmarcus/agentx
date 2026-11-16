#!/usr/bin/env python3
"""Small local HTTP API for testing AWS Bedrock inference profiles."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


AWS_PROFILE = os.environ.get("AWS_PROFILE", "bedrock-test")
AWS_REGION = os.environ.get("BEDROCK_REGION", "eu-north-1")
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
)
HOST = os.environ.get("BEDROCK_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("BEDROCK_API_PORT", "8080"))


def invoke(prompt: str) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("prompt must not be empty")

    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    client = session.client("bedrock-runtime")
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 256, "temperature": 0},
    )
    content = response.get("output", {}).get("message", {}).get("content", [])
    text = "".join(part.get("text", "") for part in content)
    return {
        "model": MODEL_ID,
        "profile": AWS_PROFILE,
        "region": AWS_REGION,
        "response": text,
        "usage": response.get("usage", {}),
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, {"status": "ok", "model": MODEL_ID, "region": AWS_REGION})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/chat":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            result = invoke(str(payload.get("prompt", "")))
            self._send(200, result)
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
        except (ClientError, BotoCoreError) as exc:
            self._send(502, {"error": type(exc).__name__, "message": str(exc)})
        except (TypeError, json.JSONDecodeError) as exc:
            self._send(400, {"error": "invalid JSON request", "message": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return


if __name__ == "__main__":
    print(f"Bedrock API listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
