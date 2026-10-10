import json
import subprocess
import sys
import unittest
from pathlib import Path
from core.node_manager import Node, NodeManager
from itopaz_agent import node_tag

ROOT = Path(__file__).resolve().parent.parent

class UpgradeChecks(unittest.TestCase):
    def test_doctor_both_entrypoints(self):
        for entry in ("itopaz_agent.py", "agent/itopaz_agent.py"):
            result = subprocess.run([sys.executable, str(ROOT / entry), "--doctor"], capture_output=True, encoding="utf-8", cwd=ROOT, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["version"], "1.4.0")
            self.assertEqual(report["workspace"], str(ROOT))
            self.assertIsInstance(report["operation_locked"], bool)
            self.assertNotIn("ssh_key", result.stdout)

    def test_interactive_startup_and_doctor(self):
        result = subprocess.run([sys.executable, str(ROOT / "itopaz_agent.py"), "--provider", "offline"], input="/doctor\n/exit\n", capture_output=True, encoding="utf-8", cwd=ROOT, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Operation lock:", result.stdout)
        self.assertIn('"version": "1.4.0"', result.stdout)
        self.assertNotIn("??", result.stdout)
        self.assertIn("Goodbye!", result.stdout)

    def test_disabled_node_cannot_run_directly(self):
        node = Node("standby", {"enabled": False, "optional": True})
        with self.assertRaisesRegex(PermissionError, "disabled"):
            node.ssh_command("pwd")
        self.assertEqual(node_tag(node.to_dict()), "[disabled / standby]")
        manager = NodeManager()
        manager._nodes = {"standby": node}
        self.assertEqual(manager.select_workers(high_load=True), [])
        self.assertEqual(manager.overflow_workers(), [])
