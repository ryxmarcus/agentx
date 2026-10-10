import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import dashboard_client as client


class DashboardApprovalTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.action_file = Path(self.folder.name) / "action.json"
        self.action_file.write_text(json.dumps({"accountId": "745510282686", "region": "ap-south-1", "resourceType": "ec2", "resourceId": "i-0123456789abcdef0", "action": "start"}))
        self.registry = {"accounts": [{"accountId": "745510282686", "regions": ["ap-south-1"], "configured": True}]}

    def test_cancellation_never_executes(self):
        with patch.object(client, "accounts", return_value=self.registry), patch.object(client, "request") as send, patch("builtins.input", return_value="yes"):
            result = client.approve_file(self.action_file)
        self.assertFalse(result["changed"])
        send.assert_not_called()

    def test_exact_confirmation_sends_reviewed_target(self):
        identifier = "a" * 32
        with patch.object(client, "accounts", return_value=self.registry), patch.object(client, "request", return_value={"ok": True}) as send, patch.object(client.uuid, "uuid4") as nonce, patch("builtins.input", return_value="APPROVE " + identifier):
            nonce.return_value.hex = identifier
            client.approve_file(self.action_file)
        args, kwargs = send.call_args
        self.assertEqual(args[0], "/api/master/action")
        self.assertEqual(args[1]["accountId"], "745510282686")
        self.assertEqual(args[1]["approvalId"], identifier)
        self.assertTrue(kwargs["confirmed"])

    def test_unconfigured_account_never_prompts_or_executes(self):
        with patch.object(client, "accounts", return_value={"accounts": []}), patch.object(client, "request") as send, patch("builtins.input") as prompt:
            with self.assertRaisesRegex(ValueError, "not configured"):
                client.approve_file(self.action_file)
        send.assert_not_called()
        prompt.assert_not_called()

    def test_expiration_during_review_never_executes(self):
        identifier = "a" * 32
        with patch.object(client, "accounts", return_value=self.registry), patch.object(client, "request") as send, patch.object(client.uuid, "uuid4") as nonce, patch.object(client.time, "time", side_effect=[100, 401]), patch("builtins.input", return_value="APPROVE " + identifier):
            nonce.return_value.hex = identifier
            with self.assertRaisesRegex(ValueError, "expired"):
                client.approve_file(self.action_file)
        send.assert_not_called()
