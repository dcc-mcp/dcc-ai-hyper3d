"""Run exactly one explicit API action from JSON stdin; never retry submissions.

Input: {"operation": "balance|submit|status|download", "evidence_dir": "...",
"arguments": {...}, "kind": "rodin|agentic|bang|texture", "state_file": "..."}.
Only submit uses kind; status/download may recover identities from state_file.
The private state contains job credentials. Keep its directory private and local.
"""

import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import uuid


SECRET_FIELDS = {"authorization", "api_key", "apikey", "access_token"}
IDENTITY_FIELDS = {"subscription_key", "task_uuid", "uuid", "uuids", "asset_id"}


def runtime_module():
    path = Path(__file__).resolve().parents[1] / "skill/hyper3d/scripts/_hyper3d.py"
    spec = importlib.util.spec_from_file_location("_hyper3d_live", str(path))
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    return runtime


def sanitize(value, public=True, secrets=None):
    secrets = list(secrets or []) + [os.environ.get(name, "") for name in
                                   ("HYPER3D_API_KEY", "RODIN_API_KEY")]
    secrets.extend(secret.strip() for secret in list(secrets))
    fields = SECRET_FIELDS | (IDENTITY_FIELDS if public else set())

    def collect(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key.lower() in fields and isinstance(child, str):
                    secrets.append(child)
                collect(child)
        elif isinstance(item, list):
            for child in item:
                collect(child)

    def clean(item):
        if isinstance(item, dict):
            return {clean(key): "[REDACTED]" if key.lower() in fields else clean(child)
                    for key, child in item.items()}
        if isinstance(item, list):
            return [clean(child) for child in item]
        if isinstance(item, str):
            for secret in sorted(set(secrets), key=len, reverse=True):
                if secret:
                    item = item.replace(secret, "[REDACTED]")
            item = re.sub(r"\bbearer\s+[^\s,;\"}]+", "[REDACTED]", item, flags=re.IGNORECASE)
            item = re.sub(r"\bauthorization\s*[:=]\s*(?:(?:bearer|basic)\s+)?[^\r\n]*(?:\r?\n[ \t]+[^\r\n]*)*", "[REDACTED]", item, flags=re.IGNORECASE)
            return re.sub(r"https?://[^\s\"<>]+", "[REDACTED_URL]", item, flags=re.IGNORECASE) if public else item
        return item

    collect(value)
    return clean(value)


def run(payload, runtime=None):
    if not isinstance(payload, dict):
        raise ValueError("Input must be an object")
    operation = payload.get("operation")
    kind = payload.get("kind")
    methods = {"balance": "get_balance", "status": "get_task_status", "download": "download_assets"}
    submissions = {"rodin": "create_rodin_task", "agentic": "create_agentic_task",
                   "bang": "create_bang_task", "texture": "create_texture_task"}
    if operation not in set(methods) | {"submit"} or (operation == "submit" and kind not in submissions):
        raise ValueError("Choose a supported operation and explicit submit kind")
    arguments = payload.get("arguments", {})
    if not isinstance(arguments, dict) or not isinstance(payload.get("evidence_dir"), str) or not payload["evidence_dir"]:
        raise ValueError("arguments must be an object and evidence_dir a nonempty path")
    arguments = dict(arguments)
    identity = {}
    if payload.get("state_file"):
        if operation not in {"status", "download"}:
            raise ValueError("Only status/download accept state_file")
        state = json.loads(Path(payload["state_file"]).read_text(encoding="utf-8"))
        identity = state["identity"]
        for field in ("subscription_key", "task_uuid") if operation == "download" else ("subscription_key",):
            if field not in arguments and field in identity:
                arguments[field] = identity[field]
    identity = dict(identity, **{key: arguments[key] for key in ("task_uuid", "subscription_key") if key in arguments})
    runtime = runtime or runtime_module()
    method = getattr(runtime, submissions[kind] if operation == "submit" else methods[operation])
    directory = Path(payload["evidence_dir"]).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix" and directory.stat().st_mode & 0o077:
        raise PermissionError("evidence_dir must deny group and other access")
    identifier = uuid.uuid4().hex
    private_path = directory / (identifier + ".private.json")
    report_path = directory / (identifier + ".json")
    record = {"operation": operation, "success": False, "api_success": False,
              "identity": identity, "arguments": arguments}
    if operation == "submit":
        record["kind"] = kind
    # Reserve both evidence files before a possibly billed call, and never overwrite.
    private_handle = os.open(str(private_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(private_handle, "w", encoding="utf-8") as private, report_path.open("x", encoding="utf-8") as report:
        try:
            result = method(**arguments)
            record.update(success=True, api_success=True, result=result)
            if operation == "submit":
                identity.update({field: result[field] for field in ("task_uuid", "subscription_key")})
            if operation == "status" and any(job.get("status") == "Failed" for job in result["jobs"]):
                record.update(success=False, error={"code": "task_failed", "message": "Generation failed"})
        except runtime.Hyper3DError as exc:
            record["error"] = dict(exc.details, code=exc.code, message=str(exc))
        except Exception:
            record["error"] = {"code": "operation_failed", "message": "Operation failed; inspect private evidence before resubmitting"}
            if operation == "submit":
                record["error"]["submission_may_have_succeeded"] = True
        json.dump(sanitize(record, public=False), private, indent=2, allow_nan=False)
        private.flush()
        os.fsync(private.fileno())
        safe = sanitize(dict(record, state_file=str(private_path), report_file=str(report_path)))
        safe.pop("identity", None)
        json.dump(safe, report, indent=2, allow_nan=False)
    return safe


def main():
    try:
        report = run(json.load(sys.stdin))
    except Exception:
        report = {"success": False, "error": {"code": "harness_failed", "message": "Check input, runtime installation, and evidence directory; no action is retried"}}
    print(json.dumps(report, allow_nan=False))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
