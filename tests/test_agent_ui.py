import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from core.http_server import AgentHandler


class AgentUITests(unittest.TestCase):
    def test_console_and_authenticated_ui_api(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), AgentHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            for path in ("/agentx", "/agentx/"):
                with urlopen(base + path) as response:
                    page = response.read().decode()
                    self.assertIn("text/html", response.headers["Content-Type"])
                    self.assertIn("Daily routine", page)
                    self.assertIn("Ask Topaz", page)
                    self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
                    self.assertNotIn("__NONCE__", page)
            with patch.dict("os.environ", {"TOPAZ_MASTER_TOKEN": "master", "AGENT_API_TOKEN": "search"}), patch("core.http_server.KnowledgeRetriever") as retriever:
                retriever.return_value.search.return_value = [{"excerpt": "context"}]
                for token in (None, "search"):
                    headers = {"Authorization": "Bearer " + token} if token else {}
                    with self.assertRaises(HTTPError) as denied:
                        urlopen(Request(base + "/agentx/api/search?q=dev", headers=headers))
                    self.assertEqual(denied.exception.code, 401)
                    denied.exception.close()
                with urlopen(Request(base + "/agentx/api/search?q=dev", headers={"Authorization": "Bearer master"})) as response:
                    self.assertEqual(json.load(response)["results"][0]["excerpt"], "context")
                with patch.object(AgentHandler, "downstream") as downstream:
                    req = Request(base + "/agentx/api/approve", data=b'{"proposalId":"p1"}', headers={"Authorization": "Bearer master"})
                    with self.assertRaises(HTTPError) as denied:
                        urlopen(req)
                    self.assertIn(denied.exception.code, (401, 404))
                    denied.exception.close()
                    downstream.assert_not_called()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
