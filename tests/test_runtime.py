"""Offline API fixtures: no credentials, provider calls, or credits required."""

import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib import error


SCRIPTS = Path(__file__).resolve().parents[1] / "skill" / "hyper3d" / "scripts"
SPEC = importlib.util.spec_from_file_location("_hyper3d", str(SCRIPTS / "_hyper3d.py"))
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class Response(io.BytesIO):
    def __init__(self, body, headers=None):
        super().__init__(body)
        self.headers = headers or {}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"HYPER3D_API_KEY": "fixture-secret", "RODIN_API_KEY": "fallback-secret"})
        self.environment.start()
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.image = self.root / "view.png"
        self.image.write_bytes(b"png-fixture")
        self.model = self.root / "mesh.glb"
        self.model.write_bytes(b"glb-fixture")

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def api_fixture(self, data):
        opener = Mock()
        opener.open.return_value = Response(json.dumps(data).encode("utf-8"))
        return opener

    def submission(self, singular=False):
        return {"uuid": "task-1", "job" if singular else "jobs": {"subscription_key": "sub-1", "uuids": ["job-1"]}, "consumed": 0.5}

    def test_generation_endpoints_and_multipart_forwarding(self):
        cases = [
            (runtime.create_rodin_task, {"parameters": {"prompt": "a chair", "bbox_condition": [1, 2, 3], "addons": ["HighPack"], "image_label": ["F"], "soft": True, "future_provider_option": {"enabled": True}}, "image_paths": [str(self.image)]}, "rodin", b'name="images"', False),
            (runtime.create_agentic_task, {"parameters": {"tier": "basic", "export_type": "glb"}, "image_paths": [str(self.image)]}, "rodin_agentic", b'name="images"', True),
            (runtime.create_bang_task, {"parameters": {"material": "None"}, "model_path": str(self.model)}, "bang", b'name="model"', False),
            (runtime.create_texture_task, {"parameters": {"reference_scale": 0.5}, "model_path": str(self.model), "image_paths": [str(self.image)]}, "rodin_texture_only", b'name="image"', False),
        ]
        for operation, arguments, endpoint, field, singular in cases:
            with self.subTest(endpoint=endpoint):
                opener = self.api_fixture(self.submission(singular))
                with patch.object(runtime.request, "build_opener", return_value=opener):
                    result = operation(**arguments)
                req = opener.open.call_args[0][0]
                self.assertEqual(req.full_url, runtime.API_ROOT + "/" + endpoint)
                self.assertEqual(req.get_method(), "POST")
                self.assertEqual(req.get_header("Authorization"), "Bearer fixture-secret")
                self.assertIn(field, req.data)
                self.assertEqual(result["task_uuid"], "task-1")
                self.assertEqual(result["subscription_key"], "sub-1")
                self.assertEqual(opener.open.call_count, 1)
                if endpoint == "rodin":
                    self.assertIn(b"Gen-2.5-Medium", req.data)
                    self.assertIn(b'name="bbox_condition"\r\n\r\n[1,2,3]\r\n', req.data)
                    self.assertIn(b'name="addons"\r\n\r\nHighPack\r\n', req.data)
                    self.assertNotIn(b'["HighPack"]', req.data)
                    self.assertIn(b'name="image_label"\r\n\r\n["F"]\r\n', req.data)
                    self.assertIn(b'name="soft"\r\n\r\ntrue\r\n', req.data)
                    self.assertIn(b'name="future_provider_option"\r\n\r\n{"enabled":true}\r\n', req.data)

    def test_addons_use_literal_form_text_for_all_rodin_generations(self):
        for tier in ("Sketch", "Gen-2", "Gen-2.5-Medium"):
            with self.subTest(tier=tier):
                opener = self.api_fixture(self.submission())
                with patch.object(runtime.request, "build_opener", return_value=opener):
                    runtime.create_rodin_task({"prompt": "a chair", "tier": tier,
                                               "addons": ["HighPack"]})
                body = opener.open.call_args[0][0].data
                self.assertIn(b'name="addons"\r\n\r\nHighPack\r\n', body)
                self.assertNotIn(b'["HighPack"]', body)
                self.assertEqual(body.count(b'name="addons"'), 1)
                self.assertEqual(opener.open.call_count, 1)

    def test_empty_optional_arrays_are_omitted_from_multipart(self):
        opener = self.api_fixture(self.submission())
        with patch.object(runtime.request, "build_opener", return_value=opener):
            runtime.create_rodin_task({"prompt": "a chair", "addons": [], "image_label": [],
                                       "bbox_condition": [1, 1, 1], "soft": False})
        body = opener.open.call_args[0][0].data
        self.assertNotIn(b'name="addons"', body)
        self.assertNotIn(b'name="image_label"', body)
        self.assertIn(b'name="bbox_condition"\r\n\r\n[1,1,1]\r\n', body)
        self.assertIn(b'name="soft"\r\n\r\nfalse\r\n', body)
        self.assertEqual(opener.open.call_count, 1)

    def test_bang_asset_id_mode_needs_no_files(self):
        with patch.object(runtime, "_api", return_value=self.submission()) as api:
            runtime.create_bang_task({"asset_id": "source-task", "instruction": "wheels"})
        self.assertIn(b"source-task", api.call_args[1]["multipart"][0])

    def test_json_and_balance_endpoints(self):
        cases = [
            (runtime.get_task_status, {"subscription_key": "sub-1"}, "status", {"jobs": [{"uuid": "j", "status": "Done"}]}, {"subscription_key": "sub-1"}),
            (runtime.get_download_links, {"task_uuid": "task-1"}, "download", {"list": [{"name": "mesh.glb", "url": "https://assets.example/mesh?sig=fixture"}]}, {"task_uuid": "task-1"}),
            (runtime.get_balance, {"usage_page": 2}, "check_balance?usage_page=2", {"balance": 10, "usage": []}, None),
        ]
        for operation, arguments, endpoint, data, payload in cases:
            with self.subTest(endpoint=endpoint):
                opener = self.api_fixture(data)
                with patch.object(runtime.request, "build_opener", return_value=opener):
                    result = operation(**arguments)
                req = opener.open.call_args[0][0]
                self.assertEqual(req.full_url, runtime.API_ROOT + "/" + endpoint)
                self.assertEqual(json.loads(req.data) if req.data else None, payload)
                self.assertEqual(result["data"], data)

    def test_environment_only_key_and_fallback(self):
        with patch.dict(os.environ, {"HYPER3D_API_KEY": ""}):
            self.assertEqual(runtime._key(), "fallback-secret")
        with patch.dict(os.environ, {"HYPER3D_API_KEY": "", "RODIN_API_KEY": ""}):
            with self.assertRaises(runtime.Hyper3DError):
                runtime.get_balance()

    def test_validation_happens_before_network(self):
        cases = [
            (runtime.create_rodin_task, {"parameters": {}}),
            (runtime.create_rodin_task, {"parameters": {"prompt": "x", "seed": -1}}),
            (runtime.create_rodin_task, {"parameters": {"prompt": "x", "tier": "Gen-2.5-Extreme-Low", "geometry_instruct_mode": "creative"}}),
            (runtime.create_rodin_task, {"parameters": {"prompt": "x", "is_micro": True}}),
            (runtime.create_rodin_task, {"parameters": {"prompt": "x", "mesh_mode": "Quad", "quality_override": 200001}}),
            (runtime.create_rodin_task, {"parameters": {"prompt": "x", "bbox_condition": [1, 2]}}),
            (runtime.create_rodin_task, {"parameters": {"prompt": "x", "image_label": ["F"]}}),
            (runtime.create_rodin_task, {"parameters": {"prompt": "x", "hd_texture": "false"}}),
            (runtime.create_rodin_task, {"parameters": {"prompt": "x", "api_key": "untrusted"}}),
            (runtime.create_rodin_task, {"parameters": {"prompt": "x", "future": [float("nan")]}}),
            (runtime.create_agentic_task, {"parameters": {}, "image_paths": []}),
            (runtime.create_agentic_task, {"parameters": {"export_type": "obj"}, "image_paths": [str(self.image)]}),
            (runtime.create_bang_task, {"parameters": {"asset_id": "task"}, "model_path": str(self.model)}),
            (runtime.create_bang_task, {"parameters": {"asset_id": "task", "prompt": "x"}}),
            (runtime.create_bang_task, {"parameters": {}, "model_path": str(self.model)}),
            (runtime.create_texture_task, {"parameters": {"reference_scale": 0.4}, "model_path": str(self.model), "image_paths": [str(self.image)]}),
            (runtime.create_texture_task, {"parameters": {}, "model_path": str(self.model)}),
            (runtime.get_balance, {"usage_page": 0}),
            (runtime.get_balance, {"usage_page": True}),
            (runtime.get_task_status, {"subscription_key": ""}),
            (runtime.get_download_links, {"task_uuid": ""}),
        ]
        with patch.object(runtime, "_api") as api:
            for operation, arguments in cases:
                with self.subTest(operation=operation.__name__, arguments=arguments):
                    with self.assertRaises(runtime.Hyper3DError):
                        operation(**arguments)
            api.assert_not_called()

    def test_agentic_25mib_limit_and_total_upload_bound(self):
        with self.image.open("wb") as stream:
            stream.truncate(25 * 1024 * 1024 + 1)
        with patch.object(runtime, "_api") as api:
            with self.assertRaises(runtime.Hyper3DError):
                runtime.create_agentic_task({}, [str(self.image)])
            api.assert_not_called()
        with patch.object(runtime, "MAX_UPLOAD", 1):
            with self.assertRaises(runtime.Hyper3DError):
                runtime._multipart({}, [("images", self.model)])

    def test_growing_upload_is_bounded_and_rejected(self):
        class GrowingStream(io.BytesIO):
            def read(self, size=-1):
                if size < 0:
                    raise AssertionError("Upload read must stay bounded")
                return super().read(size)
        upload = SimpleNamespace(
            suffix=".png", stat=lambda: SimpleNamespace(st_size=4),
            open=lambda mode: GrowingStream(b"12345"),
        )
        with self.assertRaisesRegex(runtime.Hyper3DError, "Upload changed"):
            runtime._multipart({}, [("images", upload)])

    def test_cancellation_during_upload_prevents_paid_request(self):
        with patch.object(runtime, "check_cancelled", side_effect=[None, runtime.CancelledError("cancelled")]), patch.object(runtime.request, "build_opener") as opener:
            result = runtime.tool_call(runtime.create_rodin_task, parameters={}, image_paths=[str(self.image)])
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "cancelled")
        opener.assert_not_called()

    def test_rodin_generation_specific_fields(self):
        cases = [
            {"tier": "Regular", "texture_mode": "high"},
            {"tier": "Gen-2", "condition_mode": "fuse"},
            {"tier": "Gen-2.5-Medium", "mesh_simplify": True},
            {"tier": "Regular", "mesh_mode": "Quad", "mesh_simplify": True},
            {"tier": "Regular", "mesh_mode": "Raw", "mesh_smooth": True},
        ]
        with patch.object(runtime, "_api") as api:
            for parameters in cases:
                with self.subTest(parameters=parameters), self.assertRaises(runtime.Hyper3DError):
                    runtime.create_rodin_task(dict(parameters, prompt="x"))
            api.assert_not_called()

    def test_long_prompts_allowed_for_bang_and_texture(self):
        with patch.object(runtime, "_api", return_value=self.submission()):
            runtime.create_bang_task({"prompt": "x" * 1025, "material": "None"}, model_path=str(self.model))
            runtime.create_texture_task({"prompt": "x" * 1025}, model_path=str(self.model), image_paths=[str(self.image)])

    def test_known_provider_error_code_retained_without_raw_message(self):
        opener = self.api_fixture({"error": "API_INSUFFICIENT_FUNDS", "message": "fixture-secret https://asset.example/?sig=private"})
        with patch.object(runtime.request, "build_opener", return_value=opener):
            result = runtime.tool_call(runtime.get_balance)
        self.assertEqual(result["context"]["provider_code"], "API_INSUFFICIENT_FUNDS")
        self.assertNotIn("fixture-secret", repr(result))
        self.assertNotIn("sig=private", repr(result))

    def test_invalid_balance_responses_fail(self):
        for data in [{}, {"balance": True}, {"balance": "10"}, {"balance": float("inf")}, {"balance": 10, "usage": {}}]:
            with self.subTest(data=data), patch.object(runtime, "_api", return_value=data):
                with self.assertRaises(runtime.Hyper3DError) as caught:
                    runtime.get_balance()
                self.assertEqual(caught.exception.code, "invalid_response")

    def test_provider_error_on_2xx_and_unknown_submission(self):
        for data, code in [({"error": "fixture-secret https://asset.example/?sig=private"}, "provider_error"), ({"uuid": "task"}, "submission_ambiguous")]:
            opener = self.api_fixture(data)
            with patch.object(runtime.request, "build_opener", return_value=opener):
                result = runtime.tool_call(runtime.create_rodin_task, parameters={"prompt": "x"})
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], code)
            self.assertNotIn("fixture-secret", repr(result))
            self.assertNotIn("sig=private", repr(result))
            self.assertEqual(opener.open.call_count, 1)

    def test_http_and_network_errors_are_redacted_and_not_retried(self):
        failures = [error.HTTPError("https://secret.example/?sig=private", 429, "fixture-secret", {"Retry-After": "30"}, None), error.URLError("fixture-secret https://secret.example/?sig=private")]
        for failure in failures:
            opener = Mock()
            opener.open.side_effect = failure
            with patch.object(runtime.request, "build_opener", return_value=opener):
                result = runtime.tool_call(runtime.create_rodin_task, parameters={"prompt": "x"})
            self.assertFalse(result["success"])
            self.assertNotIn("fixture-secret", repr(result))
            self.assertNotIn("sig=private", repr(result))
            self.assertEqual(opener.open.call_count, 1)
            if isinstance(failure, error.HTTPError):
                self.assertEqual(result["context"]["retry_after"], "30")
            else:
                self.assertTrue(result["context"]["submission_may_have_succeeded"])

    def test_http_validation_details_are_bounded_and_redacted(self):
        data = {"error": "INVALID_REQUEST", "detail": [{"loc": ["body", "mesh_simplify"],
                "msg": "Expected boolean; fixture-secret fallback-secret Authorization: Bearer other-secret https://asset.example/?sig=private"}],
                "authorization": "another-secret"}
        opener = Mock()
        opener.open.side_effect = error.HTTPError("https://api.example", 400, "Bad Request", {}, io.BytesIO(json.dumps(data).encode("utf-8")))
        with patch.object(runtime.request, "build_opener", return_value=opener):
            result = runtime.tool_call(runtime.create_rodin_task, parameters={"prompt": "x"})
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(result["context"]["provider_code"], "INVALID_REQUEST")
        self.assertEqual(result["context"]["http_status"], 400)
        message = result["context"]["provider_message"]
        self.assertIn("mesh_simplify", message)
        self.assertIn("Expected boolean", message)
        self.assertLessEqual(len(message), 512)
        for secret in ("fixture-secret", "fallback-secret", "other-secret", "another-secret", "sig=private", "https://"):
            self.assertNotIn(secret, repr(result))

    def test_http_malformed_or_large_body_is_hidden(self):
        bodies = [b"fixture-secret <html>https://asset.example/?sig=private</html>",
                  json.dumps({"message": "x" * 600}).encode("utf-8"), b"x" * (runtime.MAX_RESPONSE + 1)]
        for body in bodies:
            with self.subTest(size=len(body)):
                stream = Mock(wraps=io.BytesIO(body))
                opener = Mock()
                opener.open.side_effect = error.HTTPError("https://api.example", 400, "Bad Request", {}, stream)
                with patch.object(runtime.request, "build_opener", return_value=opener):
                    result = runtime.tool_call(runtime.get_balance)
                self.assertFalse(result["success"])
                self.assertEqual(result["error"], "provider_http_error")
                stream.read.assert_called_once_with(runtime.MAX_RESPONSE + 1)
                self.assertLessEqual(len(result["context"].get("provider_message", "")), 512)
                self.assertNotIn("fixture-secret", repr(result))
                self.assertNotIn("sig=private", repr(result))

    def test_http_diagnostics_redact_nested_multiline_authorization(self):
        for header in ("Authorization:\n Basic\n multiline-secret", "Authorization: Digest username=secret-user, response=secret-response\r\n continuation-secret",
                       "Authorization:\r\n Bearer\r\n multiline-secret"):
            with self.subTest(header=header):
                body = json.dumps({"error": "INVALID_REQUEST", "detail": {"field": "addons", "message": header,
                                  "fixture-secret": "HTTPS://asset.example/?sig=private"}}).encode("utf-8")
                details = runtime._http_error_details(io.BytesIO(body))
                self.assertIn("addons", details["provider_message"])
                for secret in ("multiline-secret", "secret-user", "secret-response", "continuation-secret", "fixture-secret", "sig=private"):
                    self.assertNotIn(secret, repr(details))

    def test_raw_provider_data_redacts_both_keys(self):
        data = self.submission()
        data.update({"debug": "fixture-secret fallback-secret", "api_key": "echo", "authorization": "echo"})
        with patch.object(runtime.request, "build_opener", return_value=self.api_fixture(data)):
            result = runtime.create_rodin_task({"prompt": "x"})
        self.assertNotIn("fixture-secret", repr(result))
        self.assertNotIn("fallback-secret", repr(result))
        self.assertNotIn("echo", repr(result))

    def status(self, state="Done"):
        return {"jobs": [{"uuid": "job-1", "status": state}]}

    def listing(self, names=None):
        return {"list": [{"name": name, "url": "https://assets.example/file?sig=private"} for name in (names or ["mesh.glb"])]}

    def download(self, **kwargs):
        return runtime.download_assets("task-1", "sub-1", str(self.root / "output"), **kwargs)

    def test_download_requires_all_jobs_done(self):
        statuses = [self.status("Waiting"), self.status("Generating"), self.status("Failed"), {"jobs": []}, {"jobs": [{"status": "Done"}, {"status": "Generating"}]}]
        for status in statuses:
            with self.subTest(status=status), patch.object(runtime, "_api", return_value=status) as api:
                with self.assertRaises(runtime.Hyper3DError):
                    self.download()
                self.assertEqual(api.call_count, 1)
                self.assertEqual(api.call_args[0], ("status", {"subscription_key": "sub-1"}))
                self.assertFalse((self.root / "output").exists())

    def test_download_success_checksum_descriptor_and_no_zip_extraction(self):
        payload = b"asset-fixture"
        with patch.object(runtime, "_api", side_effect=[self.status(), self.listing(["mesh.glb", "textures.zip"])]), patch.object(runtime, "_public_url", return_value="1.1.1.1"), patch.object(runtime, "_open_asset", side_effect=lambda url, **kwargs: Response(payload, {"Content-Length": str(len(payload))})):
            result = self.download()
        self.assertEqual(len(result["files"]), 2)
        self.assertEqual((self.root / "output" / "textures.zip").read_bytes(), payload)
        self.assertEqual(len(list((self.root / "output").iterdir())), 2)
        from dcc_mcp_core import AssetDescriptor
        self.assertEqual(len(result["asset_descriptors"]), 1)
        for record in result["files"]:
            self.assertTrue(Path(record["path"]).is_absolute())
            self.assertEqual(record["sha256"], runtime.hashlib.sha256(payload).hexdigest())
        for descriptor in result["asset_descriptors"]:
            AssetDescriptor.from_dict(descriptor).validate()
            self.assertNotIn("attribution", descriptor)
            self.assertNotIn("meters_per_unit", descriptor)
            self.assertNotIn("up_axis", descriptor)
            self.assertNotIn("sig=private", repr(descriptor))

    def test_download_selection_and_provider_names(self):
        with patch.object(runtime, "_api", side_effect=[self.status(), self.listing(["mesh.glb", "mesh.obj"])]), patch.object(runtime, "_public_url", return_value="1.1.1.1"), patch.object(runtime, "_open_asset", return_value=Response(b"mesh")):
            result = self.download(filenames=["mesh.obj"])
        self.assertEqual([item["name"] for item in result["files"]], ["mesh.obj"])

    def test_download_rejects_traversal_names_collisions_and_unknown_names(self):
        bad_names = ["../mesh.glb", "..\\mesh.glb", "/mesh.glb", "C:mesh.glb", "CON.glb", "mesh.glb.", "mesh.glb ", "mesh\x00.glb"]
        for names, selection in [([name], None) for name in bad_names] + [(["mesh.glb", "MESH.glb"], None), (["mesh.glb"], ["other.glb"])]:
            with self.subTest(names=names), patch.object(runtime, "_api", side_effect=[self.status(), self.listing(names)]), patch.object(runtime, "_open_asset") as download:
                with self.assertRaises(runtime.Hyper3DError):
                    self.download(filenames=selection)
                download.assert_not_called()

    def test_download_does_not_overwrite_existing_or_racing_file(self):
        output = self.root / "output"
        output.mkdir()
        target = output / "mesh.glb"
        target.write_bytes(b"existing")
        with patch.object(runtime, "_api", side_effect=[self.status(), self.listing()]), patch.object(runtime, "_open_asset") as download:
            with self.assertRaises(runtime.Hyper3DError):
                self.download()
            download.assert_not_called()
        self.assertEqual(target.read_bytes(), b"existing")
        target.unlink()
        def racing_asset(url, **kwargs):
            target.write_bytes(b"racing-owner")
            return Response(b"new")
        with patch.object(runtime, "_api", side_effect=[self.status(), self.listing()]), patch.object(runtime, "_public_url", return_value="1.1.1.1"), patch.object(runtime, "_open_asset", side_effect=racing_asset):
            with self.assertRaises(runtime.Hyper3DError):
                self.download()
        self.assertEqual(target.read_bytes(), b"racing-owner")
        self.assertEqual([item.name for item in output.iterdir()], ["mesh.glb"])

    def test_asset_size_truncation_cleanup_and_partial_results(self):
        for body, headers, limit in [(b"too big", {}, 1), (b"short", {"Content-Length": "10"}, 100), (b"", {}, 100)]:
            with self.subTest(body=body), patch.object(runtime, "_api", side_effect=[self.status(), self.listing()]), patch.object(runtime, "_public_url", return_value="1.1.1.1"), patch.object(runtime, "_open_asset", return_value=Response(body, headers)), patch.object(runtime, "MAX_ASSET", limit):
                with self.assertRaises(runtime.Hyper3DError) as caught:
                    self.download()
                self.assertEqual(caught.exception.details["completed_files"], [])
                self.assertEqual(list((self.root / "output").iterdir()), [])

    def test_download_total_deadline_and_completed_files(self):
        with patch.object(runtime, "_api", return_value=self.status()), patch.object(runtime.time, "monotonic", side_effect=[0, 601]):
            with self.assertRaises(runtime.Hyper3DError) as caught:
                self.download()
            self.assertEqual(caught.exception.code, "asset_timeout")
        with patch.object(runtime, "_api", side_effect=[self.status(), self.listing(["mesh.glb", "mesh.obj"])]), patch.object(runtime, "_public_url", return_value="1.1.1.1"), patch.object(runtime, "_open_asset", side_effect=[Response(b"model"), runtime.Hyper3DError("failed", "asset_network_error")]):
            with self.assertRaises(runtime.Hyper3DError) as caught:
                self.download()
            self.assertEqual([item["name"] for item in caught.exception.details["completed_files"]], ["mesh.glb"])
            self.assertEqual([item.name for item in (self.root / "output").iterdir()], ["mesh.glb"])

    def test_archive_only_download_returns_no_import_descriptor(self):
        with patch.object(runtime, "_api", side_effect=[self.status(), self.listing(["textures.zip"])]), patch.object(runtime, "_public_url", return_value="1.1.1.1"), patch.object(runtime, "_open_asset", return_value=Response(b"archive")):
            result = self.download()
        self.assertEqual(result["asset_descriptors"], [])
        self.assertEqual(result["files"][0]["name"], "textures.zip")

    def test_asset_url_requires_public_https_addresses(self):
        addresses = lambda ip: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]
        for url in ["http://assets.example/file", "https://u:p@assets.example/file", "https://assets.example:8443/file", "file:///etc/passwd", "https://assets.example/file#fragment"]:
            with self.subTest(url=url), patch.object(runtime.socket, "getaddrinfo", return_value=addresses("1.1.1.1")):
                with self.assertRaises(runtime.Hyper3DError):
                    runtime._public_url(url)
        for ip in ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1"]:
            with self.subTest(ip=ip), patch.object(runtime.socket, "getaddrinfo", return_value=addresses(ip)):
                with self.assertRaises(runtime.Hyper3DError):
                    runtime._public_url("https://assets.example/file?sig=private")
        with patch.object(runtime.socket, "getaddrinfo", return_value=addresses("1.1.1.1")):
            self.assertEqual(runtime._public_url("https://assets.example/file?sig=private"), "1.1.1.1")
        with patch.object(runtime.socket, "getaddrinfo", return_value=addresses("1.1.1.1") + addresses("127.0.0.1")):
            with self.assertRaises(runtime.Hyper3DError):
                runtime._public_url("https://assets.example/file")

    def test_redirect_validation_and_no_asset_authorization(self):
        first = Mock()
        first.open.side_effect = error.HTTPError("https://assets.example/file", 302, "redirect", {"Location": "https://127.0.0.1/private?sig=private"}, io.BytesIO())
        with patch.object(runtime, "_public_url", side_effect=["1.1.1.1", runtime.Hyper3DError("unsafe", "unsafe_download_url")]) as validate, patch.object(runtime.request, "build_opener", return_value=first):
            result = runtime.tool_call(runtime._open_asset, url="https://assets.example/file")
        self.assertFalse(result["success"])
        self.assertEqual(validate.call_count, 2)
        req = first.open.call_args[0][0]
        self.assertIsNone(req.get_header("Authorization"))
        self.assertNotIn("sig=private", repr(result))

    def test_tls_connection_uses_validated_address_and_original_hostname(self):
        context = Mock()
        connection = runtime._PinnedHTTPSConnection("assets.example", "1.1.1.1", timeout=60, context=context)
        with patch.object(runtime.socket, "create_connection", return_value="socket") as connect:
            connection.connect()
        self.assertEqual(connect.call_args[0][0], ("1.1.1.1", 443))
        context.wrap_socket.assert_called_once_with("socket", server_hostname="assets.example")

    def test_all_wrappers_return_core_result_dict(self):
        with patch.dict(sys.modules, {"_hyper3d": runtime}):
            for path in SCRIPTS.glob("*.py"):
                if path.name.startswith("_"):
                    continue
                spec = importlib.util.spec_from_file_location(path.stem, str(path))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                with patch.object(module, "operation", return_value={"data": {"fixture": True}}):
                    signature = __import__("inspect").signature(module.main)
                    args = {name: "fixture" for name, parameter in signature.parameters.items() if parameter.default is parameter.empty}
                    result = module.main(**args)
                self.assertIsInstance(result, dict)
                self.assertTrue(result["success"])
                self.assertEqual(result["context"]["data"], {"fixture": True})


if __name__ == "__main__":
    unittest.main()
