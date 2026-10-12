"""HTTP health and authenticated knowledge search for the Python agent."""
import hmac
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from core.knowledge_rag import KnowledgeRetriever

class AgentHandler(BaseHTTPRequestHandler):
    def route_path(self):
        path = urlparse(self.path).path
        aliases = {"status": "/control/status", "chat": "/control/chat", "search": "/control/search", "metrics": "/control/dashboard/metrics"}
        if path.startswith("/agentx/api/"):
            return aliases.get(path[len("/agentx/api/"):], "/not-found")
        return path

    def show_ui(self):
        from core.agent_ui import PAGE
        nonce = secrets.token_urlsafe(24)
        data = PAGE.replace("__NONCE__", nonce).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(data)

    def respond(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def authenticated(self):
        token = os.environ.get("TOPAZ_MASTER_TOKEN" if self.route_path().startswith("/control/") else "AGENT_API_TOKEN", "")
        return bool(token) and hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token)

    def downstream(self, base, path, payload=None, approved=False):
        headers = {"Content-Type": "application/json"}
        if approved:
            headers["Authorization"] = "Bearer " + os.environ.get("TOPAZ_APPROVAL_TOKEN", "")
        try:
            data = json.dumps(payload).encode() if payload is not None else None
            with urlopen(Request(base.rstrip("/") + path, data=data, headers=headers), timeout=45) as response:
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    return self.respond(502, {"error": "Downstream response too large"})
                return self.respond(response.status, json.loads(body))
        except HTTPError as error:
            with error:
                try: body = json.loads(error.read(65536))
                except ValueError: body = {"error": "Downstream request failed"}
            return self.respond(error.code, body)
        except (URLError, OSError, ValueError):
            return self.respond(502, {"error": "Downstream unavailable"})

    def do_POST(self):
        if not self.authenticated():
            return self.respond(401, {"error": "Authentication required"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32768: raise ValueError()
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict): raise ValueError()
        except (ValueError, TypeError):
            return self.respond(400, {"error": "Invalid JSON request"})
        bot = os.environ.get("KNOWLEDGE_BOT_URL", "http://knowledge-bot-backend.default.svc.cluster.local:8081")
        route = self.route_path()
        if route == "/control/chat":
            question = data.get("question")
            if not isinstance(question, str) or not 1 <= len(question) <= 8000:
                return self.respond(400, {"error": "question required (1-8000 characters)"})
            return self.downstream(bot, "/api/chat", {"question": question})
        if route == "/control/approve":
            proposal = data.get("proposalId")
            if not isinstance(proposal, str) or not proposal or self.headers.get("X-Topaz-Confirm") != proposal:
                return self.respond(403, {"error": "Explicit confirmation of proposalId required"})
            return self.downstream(bot, "/api/action/execute", {"proposalId": proposal}, approved=True)
        return self.respond(404, {"error": "Not found"})

    def do_GET(self):
        route = urlparse(self.path)
        if route.path in ("/agentx", "/agentx/"):
            return self.show_ui()
        if route.path in ("/healthz", "/health"):
            return self.respond(200, {"status": "ok", "service": "itopaz-agent", "runtime": "python"})
        path = self.route_path()
        if not self.authenticated():
            return self.respond(401, {"error": "Authentication required"})
        bot = os.environ.get("KNOWLEDGE_BOT_URL", "http://knowledge-bot-backend.default.svc.cluster.local:8081")
        dashboard = os.environ.get("DASHBOARD_API_URL", "http://aws-dashboard-api-svc.default.svc.cluster.local:8080")
        if path == "/control/status":
            health = {}
            for name, base in (("knowledge", bot), ("dashboard", dashboard)):
                try:
                    with urlopen(base + "/api/health", timeout=10) as result:
                        health[name] = {"reachable": result.status == 200}
                except (URLError, OSError): health[name] = {"reachable": False}
            return self.respond(200, {"master": "local-windows", "scm": "bitbucket", "backend": "dev-eks", "approval": "per-change", "services": health})
        if path.startswith("/control/pending/"):
            identifier = path[len("/control/pending/"):]
            if not identifier or len(identifier) > 100 or "/" in identifier:
                return self.respond(400, {"error": "Invalid proposal ID"})
            return self.downstream(bot, "/api/action/pending/" + quote(identifier, safe=""), approved=True)
        if path == "/control/dashboard/metrics":
            return self.downstream(dashboard, "/api/metrics")
        if path == "/control/audit":
            return self.downstream(bot, "/api/action/audit")
        if path in ("/api/search", "/control/search"):
            query = parse_qs(route.query).get("q", [""])[0].strip()
            if not query or len(query) > 500:
                return self.respond(400, {"error": "q must contain 1-500 characters"})
            try:
                return self.respond(200, {"results": KnowledgeRetriever().search(query, limit=5, context_chars=500)})
            except Exception:
                return self.respond(500, {"error": "Search failed"})
        return self.respond(404, {"error": "Not found"})

    def log_message(self, format, *args):
        # Request URLs may contain sensitive search terms.
        pass


def serve(host="0.0.0.0", port=8082):
    with ThreadingHTTPServer((host, port), AgentHandler) as server:
        print(f"Python agent HTTP listening on {host}:{port}", flush=True)
        server.serve_forever()
