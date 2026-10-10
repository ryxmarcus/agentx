import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from unittest.mock import patch
from core.http_server import AgentHandler

class HTTPChecks(unittest.TestCase):
    def test_health_and_authentication(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), AgentHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/healthz") as result:
                self.assertEqual(json.load(result)["runtime"], "python")
            with patch.dict("os.environ", {"AGENT_API_TOKEN": "test-token"}):
                with self.assertRaises(HTTPError) as denied:
                    urlopen(base + "/api/search?q=anything")
                self.assertEqual(denied.exception.code, 401)
                request = Request(base + "/api/search?q=anything", headers={"Authorization": "Bearer test-token"})
                with urlopen(request) as result:
                    self.assertIn("results", json.load(result))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
