"""Direct Windows master control of the authenticated AWS Dashboard API."""
import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


def settings():
    config = json.loads((ROOT / "control.json").read_text(encoding="utf-8"))
    base = config.get("dashboard_url", "http://127.0.0.1:18080").rstrip("/")
    parsed = urlparse(base)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Dashboard URL must not contain credentials, query, or fragment")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost", "::1")):
        raise ValueError("Use HTTPS or the encrypted SSH loopback connection")
    token = os.environ.get("TOPAZ_DASHBOARD_MASTER_TOKEN")
    if not token:
        token = (ROOT / "secrets/dashboard-master-token.txt").read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError("Direct dashboard master credential is missing")
    return base, token


def request(path, payload=None, confirmed=False):
    base, token = settings()
    headers = {"Authorization": "Bearer " + token}
    data = None
    if payload is not None:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
        if confirmed:
            headers["X-Topaz-Confirm"] = hashlib.sha256(data).hexdigest()
    with urlopen(Request(base + path, data=data, headers=headers), timeout=60) as response:
        return json.load(response)


def accounts():
    return request("/api/master/accounts")


def approve_file(path):
    action = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(action, dict):
        raise ValueError("Action must be a JSON object")
    required = ("accountId", "region", "resourceType", "resourceId", "action")
    if any(not isinstance(action.get(key), str) or not action[key].strip() for key in required):
        raise ValueError("Action requires explicit accountId, region, resourceType, resourceId, and action")
    configured = accounts().get("accounts", [])
    target = next((item for item in configured if item["accountId"] == action["accountId"]), None)
    if not target or not target.get("configured") or action["region"] not in (target.get("regions") or []):
        raise ValueError("Target account or region is not configured in the Dashboard")
    action["approvalId"] = uuid.uuid4().hex
    action["expiresAt"] = int(time.time()) + 300
    print("Review this exact AWS infrastructure change:")
    print(json.dumps(action, indent=2))
    confirmation = "APPROVE " + action["approvalId"]
    if input("Type " + confirmation + " to execute: ").strip() != confirmation:
        return {"status": "cancelled", "changed": False}
    if int(time.time()) >= action["expiresAt"]:
        raise ValueError("Approval expired; review the action again")
    return request("/api/master/action", action, confirmed=True)
