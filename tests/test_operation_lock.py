import unittest
from unittest.mock import patch
from core.operation_lock import check_command, require_unlocked
from core.tools import ToolExecutor

class LockTests(unittest.TestCase):
    @patch("core.operation_lock.is_locked", return_value=True)
    def test_blocks_mutations(self, _):
        for cmd in ("rm -rf data", "del file", "Remove-Item file", "git pull", "python -c pass", "bash script.sh", "git status; rm file", "git diff --output=file"):
            with self.assertRaises(PermissionError, msg=cmd):
                check_command(cmd)
        for name in ("patch_file", "write_file", "run_diagnostic"):
            self.assertEqual(ToolExecutor().execute_tool(name, {})["status"], "error")

    @patch("core.operation_lock.is_locked", return_value=True)
    def test_inspection(self, _):
        check_command("git -C /workspace status --short")
        check_command("git branch --show-current")
        with self.assertRaises(PermissionError):
            require_unlocked()

    @patch("core.operation_lock.is_locked", return_value=False)
    def test_operator_unlock(self, _):
        require_unlocked()
        check_command("git pull --ff-only")
