import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import agentx
from core.node_manager import Node, NodeManager
from agentx import node_tag

ROOT = Path(__file__).resolve().parent.parent

class UpgradeChecks(unittest.TestCase):
    def test_doctor_both_entrypoints(self):
        for entry in ("agentx.py", "agent/itopaz_agent.py"):
            result = subprocess.run([sys.executable, str(ROOT / entry), "--doctor"], capture_output=True, encoding="utf-8", cwd=ROOT, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["version"], "1.4.0")
            self.assertEqual(report["workspace"], str(ROOT))
            self.assertIsInstance(report["operation_locked"], bool)
            self.assertNotIn("ssh_key", result.stdout)

    def test_interactive_startup_and_doctor(self):
        result = subprocess.run([sys.executable, str(ROOT / "agentx.py"), "--provider", "offline"], input="/doctor\n/exit\n", capture_output=True, encoding="utf-8", cwd=ROOT, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Operation lock:", result.stdout)
        self.assertIn('"version": "1.4.0"', result.stdout)
        self.assertNotIn("??", result.stdout)
        self.assertIn("Goodbye!", result.stdout)

    def test_history_does_not_write_when_locked(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(agentx, "REPO_ROOT", Path(tmp)), \
             patch.object(agentx, "readline", MagicMock()), \
             patch.object(agentx, "is_locked", return_value=True):
            agentx.setup_history()
            self.assertFalse((Path(tmp) / ".tmp").exists())

    def test_shell_launcher_targets_canonical_cli(self):
        launcher = (ROOT / "agent" / "bin" / "itopaz-agent").read_text(encoding="utf-8")
        self.assertIn('exec python3 "${AGENT_ROOT}/agentx.py" "$@"', launcher)
        self.assertFalse((ROOT / "agent" / "agentx.py").exists())

    def test_disabled_node_cannot_run_directly(self):
        node = Node("standby", {"enabled": False, "optional": True})
        with self.assertRaisesRegex(PermissionError, "disabled"):
            node.ssh_command("pwd")
        self.assertEqual(node_tag(node.to_dict()), "[disabled / standby]")
        manager = NodeManager()
        manager._nodes = {"standby": node}
        self.assertEqual(manager.select_workers(high_load=True), [])
        self.assertEqual(manager.overflow_workers(), [])
