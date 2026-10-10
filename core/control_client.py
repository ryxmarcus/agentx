import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent

def request(path, payload=None):
    settings = json.loads((ROOT / "control.json").read_text(encoding="utf-8"))
    base = settings["backend_url"].rstrip("/")
    token = os.environ.get("TOPAZ_CONTROL_TOKEN")
    if not token:
        token = (ROOT / "secrets/control-token.txt").read_text(encoding="utf-8").strip()
    headers = {"Authorization": "Bearer " + token}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if path == "/control/approve":
        headers["X-Topaz-Confirm"] = payload["proposalId"]
    with urlopen(Request(base + path, data=data, headers=headers), timeout=60) as response:
        return json.load(response)

def approve(proposal_id):
    from urllib.parse import quote
    proposal = request("/control/pending/" + quote(proposal_id, safe=""))
    print(json.dumps(proposal, indent=2))
    answer = input("Type the proposal ID to approve this exact resource change: ").strip()
    if answer != proposal_id:
        return {"status": "cancelled", "changed": False}
    return request("/control/approve", {"proposalId": proposal_id})
