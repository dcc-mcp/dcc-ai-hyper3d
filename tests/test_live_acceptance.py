"""Offline tests for the explicit, credential-safe acceptance harness."""

import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SPEC = importlib.util.spec_from_file_location("live_acceptance", str(Path(__file__).resolve().parents[1] / "scripts/live_acceptance.py"))
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


class ProviderError(Exception):
    def __init__(self, message="Provider rejected request", code="provider_error", **details):
        super().__init__(message)
        self.code = code
        self.details = details


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.runtime = SimpleNamespace(Hyper3DError=ProviderError)
        self.key = patch.dict(os.environ, {"HYPER3D_API_KEY": "fixture-api-secret"})
        self.key.start()
        self.addCleanup(self.key.stop)

    def run_operation(self, operation, **values):
        return harness.run(dict(operation=operation, evidence_dir=self.directory.name, **values), self.runtime)

    def test_submit_once_private_identity_and_sanitized_report(self):
        self.runtime.create_rodin_task = Mock(return_value={
            "task_uuid": "task-fixture", "subscription_key": "subscription-secret",
            "data": {"url": "https://assets.example/model?sig=signed-secret",
                     "api_key": "fixture-api-secret", "echo": "subscription-secret fixture-api-secret"}})
        result = self.run_operation("submit", kind="rodin", arguments={"parameters": {"prompt": "a chair"}})
        self.runtime.create_rodin_task.assert_called_once_with(parameters={"prompt": "a chair"})
        self.assertTrue(result["success"])
        for emitted in (json.dumps(result), Path(result["report_file"]).read_text()):
            for secret in ("task-fixture", "subscription-secret", "signed-secret", "fixture-api-secret", "https://"):
                self.assertNotIn(secret, emitted)
        private = json.loads(Path(result["state_file"]).read_text())
        self.assertEqual(private["identity"]["subscription_key"], "subscription-secret")
        self.assertNotIn("fixture-api-secret", json.dumps(private))

    def test_status_carries_identity_forward_and_failed_jobs_exit_unsuccessfully(self):
        source = Path(self.directory.name) / "source.private.json"
        source.write_text(json.dumps({"identity": {"task_uuid": "task-fixture", "subscription_key": "subscription-secret"}}))
        self.runtime.get_task_status = Mock(return_value={"jobs": [{"status": "Failed"}], "all_done": False})
        result = self.run_operation("status", state_file=str(source))
        self.runtime.get_task_status.assert_called_once_with(subscription_key="subscription-secret")
        self.assertFalse(result["success"])
        self.assertTrue(result["api_success"])
        self.assertEqual(result["error"]["code"], "task_failed")
        self.assertEqual(json.loads(Path(result["state_file"]).read_text())["identity"]["task_uuid"], "task-fixture")

    def test_unknown_submit_outcome_is_not_retried(self):
        self.runtime.create_bang_task = Mock(side_effect=TimeoutError("fixture-api-secret https://private.example/?secret=x"))
        result = self.run_operation("submit", kind="bang", arguments={"parameters": {"asset_id": "existing"}})
        self.runtime.create_bang_task.assert_called_once()
        self.assertFalse(result["success"])
        self.assertTrue(result["error"]["submission_may_have_succeeded"])
        self.assertNotIn("fixture-api-secret", json.dumps(result))
        self.assertNotIn("private.example", json.dumps(result))

    def test_provider_failure_is_distinct_and_sanitized(self):
        self.runtime.get_balance = Mock(side_effect=ProviderError("fixture-api-secret https://signed.example/?sig=secret", http_status=403))
        result = self.run_operation("balance")
        self.assertFalse(result["api_success"])
        self.assertEqual(result["error"]["http_status"], 403)
        self.assertNotIn("fixture-api-secret", json.dumps(result))
        self.assertNotIn("signed.example", json.dumps(result))

    def test_download_forwards_selection_and_keeps_hash_descriptor(self):
        source = Path(self.directory.name) / "source.private.json"
        source.write_text(json.dumps({"identity": {"task_uuid": "task-fixture", "subscription_key": "subscription-secret"}}))
        self.runtime.download_assets = Mock(return_value={"files": [{"path": "model.glb", "sha256": "abc", "size_bytes": 9}], "asset_descriptors": [{"asset_id": "hyper3d:task-fixture"}]})
        result = self.run_operation("download", state_file=str(source), arguments={"output_dir": "output", "filenames": ["model.glb"]})
        self.runtime.download_assets.assert_called_once_with(output_dir="output", filenames=["model.glb"], task_uuid="task-fixture", subscription_key="subscription-secret")
        self.assertEqual(result["result"]["files"][0]["sha256"], "abc")

    def test_invalid_input_and_cli_failure_never_call_runtime(self):
        with self.assertRaises(ValueError):
            self.run_operation("submit", arguments={})
        with patch.object(harness, "run", side_effect=RuntimeError("fixture-api-secret")), patch("sys.stdin", io.StringIO("{}")), patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(harness.main(), 1)
        self.assertNotIn("fixture-api-secret", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "harness_failed")

    def test_evidence_failure_prevents_paid_call(self):
        blocked = Path(self.directory.name) / "existing-file"
        blocked.write_text("preserve me")
        self.runtime.create_agentic_task = Mock()
        with self.assertRaises(OSError):
            harness.run({"operation": "submit", "kind": "agentic", "evidence_dir": str(blocked)}, self.runtime)
        self.runtime.create_agentic_task.assert_not_called()
        self.assertEqual(blocked.read_text(), "preserve me")

    def test_submit_routes_each_explicit_kind_to_runtime(self):
        for kind, name in (("rodin", "create_rodin_task"), ("agentic", "create_agentic_task"),
                           ("bang", "create_bang_task"), ("texture", "create_texture_task")):
            with self.subTest(kind=kind):
                method = Mock(return_value={"task_uuid": "task-fixture", "subscription_key": "subscription-secret"})
                setattr(self.runtime, name, method)
                result = self.run_operation("submit", kind=kind, arguments={"parameters": {"explicit": True}})
                method.assert_called_once_with(parameters={"explicit": True})
                self.assertTrue(result["success"])

    def test_multiline_header_text_and_trimmed_key_are_redacted(self):
        with patch.dict(os.environ, {"HYPER3D_API_KEY": " fixture-api-secret "}):
            value = {"message": "field addons invalid\nAuthorization:\r\n Basic\r\n multiline-secret",
                     "nested": ["Bearer\n token-secret", "fixture-api-secret"]}
            for public in (True, False):
                result = harness.sanitize(value, public=public)
                self.assertIn("field addons invalid", result["message"])
                for secret in ("multiline-secret", "token-secret", "fixture-api-secret"):
                    self.assertNotIn(secret, repr(result))

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits required")
    def test_posix_shared_directory_refuses_before_paid_call(self):
        directory = Path(self.directory.name)
        directory.chmod(0o777)
        self.addCleanup(directory.chmod, 0o700)
        self.runtime.create_rodin_task = Mock()
        with self.assertRaises(PermissionError):
            self.run_operation("submit", kind="rodin", arguments={"parameters": {"prompt": "a chair"}})
        self.runtime.create_rodin_task.assert_not_called()
        self.assertEqual(directory.stat().st_mode & 0o777, 0o777)
        self.assertEqual(list(directory.iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits required")
    def test_posix_private_file_is_restricted_before_paid_call_under_open_umask(self):
        def submission(**arguments):
            paths = list(Path(self.directory.name).glob("*.private.json"))
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].stat().st_mode & 0o777, 0o600)
            return {"task_uuid": "task-fixture", "subscription_key": "subscription-secret"}

        self.runtime.create_rodin_task = Mock(side_effect=submission)
        previous = os.umask(0)
        try:
            result = self.run_operation("submit", kind="rodin", arguments={"parameters": {"prompt": "a chair"}})
        finally:
            os.umask(previous)
        self.assertTrue(result["success"])
        self.runtime.create_rodin_task.assert_called_once()
        self.assertEqual(Path(result["state_file"]).stat().st_mode & 0o777, 0o600)
