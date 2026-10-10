import json
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from core.http_server import AgentHandler

class ControlChecks(unittest.TestCase):
 def test_approval_needs_master_and_confirmation(self):
  server=ThreadingHTTPServer(("127.0.0.1",0),AgentHandler)
  thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
  try:
   base=f"http://127.0.0.1:{server.server_port}"
   with patch.dict("os.environ", {"AGENT_API_TOKEN":"search","TOPAZ_MASTER_TOKEN":"master"}), patch.object(AgentHandler,"downstream") as downstream:
    for token, expected in (("search",401),("master",403)):
     req=Request(base+"/control/approve",data=json.dumps({"proposalId":"p1"}).encode(),headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
     with self.assertRaises(HTTPError) as denied: urlopen(req)
     self.assertEqual(denied.exception.code,expected); denied.exception.close()
    downstream.assert_not_called()
  finally:
   server.shutdown();server.server_close();thread.join()
