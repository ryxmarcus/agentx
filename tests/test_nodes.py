import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from core.node_manager import NodeManager, Node

ROOT = Path(__file__).resolve().parent.parent

class NodeChecks(unittest.TestCase):
    def test_both_entrypoints(self):
        for entry in ("itopaz_agent.py", "agent/itopaz_agent.py"):
            result = subprocess.run([sys.executable, str(ROOT / entry), "--nodes"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("running on: local", result.stdout)
            self.assertIn("worker-2", result.stdout)

    def test_search_with_windows_output_encoding(self):
        import os
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        result = subprocess.run([sys.executable, str(ROOT / "itopaz_agent.py"), "--search", "DEV Grafana"], cwd=ROOT, env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"matches", result.stdout)

    @patch("core.node_manager.require_unlocked")
    @patch("core.node_manager.check_command")
    def test_local_task_preserves_arguments(self, *_):
        node = NodeManager().get("local")
        task = "review spaces and 'quotes'"
        self.assertEqual(node.agent_invocation(task), [node.python, node.agent_entry, task])
        self.assertEqual(node.ssh_command("Write-Output ok")[:3], ["powershell", "-NoProfile", "-Command"])

    @patch("core.node_manager.require_unlocked")
    def test_undeployed_workers_fail_before_execution(self, *_):
        for node in NodeManager().workers():
            node.cfg = dict(node.cfg, agent_deployed=False)
            with self.assertRaises(RuntimeError):
                node.agent_invocation("review")
            self.assertIn("StrictHostKeyChecking=yes", node.ssh_command("pwd"))

    def test_unknown_machine_is_not_master(self):
        with patch("core.node_manager.AGENT_ROOT", Path("/unknown/workspace")):
            self.assertIsNone(NodeManager(ROOT / "nodes.json").current_node())

if __name__ == "__main__":
    unittest.main()
