"""Validate the installable bundle rather than a second copy of its metadata."""

import ast
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

import jsonschema
import yaml
from dcc_mcp_core import McpHttpConfig, create_skill_server, validate_skill


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "hyper3d"


class BundleContracts(unittest.TestCase):
    def test_real_core_discovery_load_and_missing_key(self):
        environment = dict(os.environ)
        for name in list(environment):
            if name in {"HYPER3D_API_KEY", "RODIN_API_KEY"} or (
                name.startswith("DCC_MCP_") and name.endswith("SKILL_PATHS")
            ):
                environment.pop(name)
        environment.update(
            DCC_MCP_DISABLE_DEFAULT_SKILL_PATHS="1",
            DCC_MCP_PYTHON_EXECUTABLE=sys.executable,
        )
        with patch.dict(os.environ, environment, clear=True):
            config = McpHttpConfig(port=0)
            config.gateway_port = 0
            server = create_skill_server(
                "python", config, extra_paths=[str(ROOT / "skill")], accumulated=False
            )
            self.assertEqual({skill["name"] for skill in server.list_skills()}, {"hyper3d"})
            names = server.load_skill("hyper3d")
            self.assertEqual(len(names), 8)
            self.assertIn("hyper3d__get_balance", names)
            self.assertTrue(all(server.has_handler(name) for name in names))
            handle = server.start()
            try:
                request = Request(
                    handle.mcp_url(),
                    data=json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "hyper3d__get_balance", "arguments": {}},
                    }).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream",
                    },
                )
                with urlopen(request, timeout=15) as response:
                    result = json.load(response)["result"]
                self.assertTrue(result["isError"], result)
                self.assertIn("authentication_missing", json.dumps(result))
            finally:
                handle.shutdown()

    def test_core_validator(self):
        report = validate_skill(str(SKILL))
        self.assertFalse(report.has_errors, str(report))

    def test_manifest_schemas_examples_and_scripts(self):
        manifest = yaml.safe_load((SKILL / "tools.yaml").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["tools"]), 8)
        names = set()
        for tool in manifest["tools"]:
            self.assertNotIn(tool["name"], names)
            names.add(tool["name"])
            self.assertTrue((SKILL / tool["source_file"]).is_file())
            self.assertEqual(tool["affinity"], "any")
            for field in ("input_schema", "output_schema"):
                jsonschema.Draft7Validator.check_schema(tool[field])
            for example in tool.get("call_examples", []):
                jsonschema.validate(example["arguments"], tool["input_schema"])
        self.assertEqual(names, {p.stem for p in (SKILL / "scripts").glob("*.py") if not p.name.startswith("_")})

    @unittest.skipIf(sys.version_info < (3, 8), "Python 3.7 itself parses every imported runtime module")
    def test_runtime_syntax_supports_python37(self):
        for script in (SKILL / "scripts").glob("*.py"):
            ast.parse(script.read_text(encoding="utf-8"), filename=str(script), feature_version=(3, 7))

    def test_reference_files_are_installed(self):
        body = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/API.md", body)
        self.assertIn("references/WORKFLOWS.md", body)
        for filename in ("API.md", "WORKFLOWS.md"):
            self.assertTrue((SKILL / "references" / filename).is_file())


if __name__ == "__main__":
    os.environ["DCC_MCP_DISABLE_DEFAULT_SKILL_PATHS"] = "1"
    unittest.main()
