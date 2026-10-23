"""Host-independent Hyper3D operations; no scene changes or automatic retries."""

import hashlib
import http.client
import ipaddress
import math
import mimetypes
import os
from pathlib import Path
import re
import socket
import ssl
import tempfile
import time
import uuid
from urllib import error, parse, request

from dcc_mcp_core.skills_helper import (
    CancelledError, check_cancelled, json_dumps, json_loads, skill_error, skill_success,
)


API_ROOT = "https://api.hyper3d.com/api/v2"
API_TIMEOUT = 120
MAX_RESPONSE = 2 * 1024 * 1024
MAX_UPLOAD = 512 * 1024 * 1024
MAX_ASSET = 512 * 1024 * 1024
MAX_TOTAL = 2 * 1024 * 1024 * 1024
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".gif", ".avif", ".heic", ".heif", ".bmp", ".jp2", ".j2k"}
MODEL_EXTENSIONS = {".obj", ".stl", ".gltf", ".glb", ".fbx", ".usdz"}
FORMATS = {"glb", "usdz", "fbx", "obj", "stl"}
MATERIALS = {"PBR", "Shaded", "All", "Hybrid", "None"}
PROVIDER_ERRORS = {"INVALID_REQUEST", "API_NO_ACTIVE_SUBSCRIPTION", "API_SUBSCRIPTION_PLAN_TOO_LOW", "API_PARALLELISM_LIMIT_REACHED", "API_INSUFFICIENT_FUNDS", "API_OBJECT_NOT_FOUND_ON_IMAGE", "IMAGE_CONTENT_VIOLATION", "IMAGE_LABEL_LENGTH_TOO_LONG", "NO_SUCH_TASK", "ASSET_NOT_AVAILABLE", "PERMISSION_DENIED", "API_UNKNOWN"}
TIERS = {"Sketch", "Regular", "Detail", "Smooth", "Gen-2"} | {
    "Gen-2.5-" + quality for quality in ("Extreme-Low", "Low", "Medium", "High", "Extreme-High")
}


class Hyper3DError(Exception):
    """Only controlled, credential-free messages cross the tool boundary."""

    def __init__(self, message, code="invalid_request", **details):
        super().__init__(message)
        self.code = code
        self.details = details


def tool_call(operation, **arguments):
    try:
        return skill_success("Hyper3D operation completed", **operation(**arguments))
    except Hyper3DError as exc:
        return skill_error(str(exc), exc.code, **exc.details)
    except CancelledError:
        return skill_error("Hyper3D operation cancelled", "cancelled")
    except Exception:
        return skill_error("Hyper3D operation failed; credentials and remote URLs are hidden", "operation_failed")


def _key():
    value = os.environ.get("HYPER3D_API_KEY") or os.environ.get("RODIN_API_KEY")
    if not value or not value.strip():
        raise Hyper3DError("Set HYPER3D_API_KEY in the adapter process environment", "authentication_missing")
    if "\r" in value or "\n" in value:
        raise Hyper3DError("API key contains invalid characters", "authentication_invalid")
    return value.strip()


def _clean(value):
    secrets = [os.environ.get(name) for name in ("HYPER3D_API_KEY", "RODIN_API_KEY")]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
                if secret.strip():
                    value = value.replace(secret.strip(), "[REDACTED]")
        return value
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if key.lower() in {"authorization", "api_key", "apikey", "access_token"} else _clean(item)) for key, item in value.items()}
    return value


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _safe_diagnostic(value):
    if isinstance(value, str):
        value = _clean(value)
        value = re.sub(r"https?://[^\s\"<>]+", "[REDACTED_URL]", value, flags=re.IGNORECASE)
        value = re.sub(r"\bbearer\s+[^\s,;\"}]+", "[REDACTED]", value, flags=re.IGNORECASE)
        return re.sub(r"\bauthorization\s*[:=]\s*(?:(?:bearer|basic)\s+)?[^\r\n]*(?:\r?\n[ \t]+[^\r\n]*)*", "[REDACTED]", value, flags=re.IGNORECASE)
    if isinstance(value, list):
        return [_safe_diagnostic(item) for item in value]
    if isinstance(value, dict):
        return {_safe_diagnostic(key): _safe_diagnostic(item) for key, item in value.items()}
    return value


def _http_error_details(response):
    try:
        raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            return {}
        data = _clean(json_loads(raw.decode("utf-8")))
        if not isinstance(data, dict):
            return {}
        result = {}
        code = data.get("code") or data.get("error")
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,79}", code):
            result["provider_code"] = code
        fields = {field: data[field] for field in ("message", "detail", "errors", "error") if field in data}
        if fields:
            message = json_dumps(_safe_diagnostic(fields))
            result["provider_message"] = message[:512]
        return result
    except Exception:
        return {}


def _api(endpoint, payload=None, multipart=None, usage_page=None):
    key = _key()
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    url = API_ROOT + "/" + endpoint
    if usage_page is not None:
        url += "?" + parse.urlencode({"usage_page": usage_page})
    if multipart is not None:
        body, content_type = multipart
        headers["Content-Type"] = content_type
    elif payload is not None:
        body = json_dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        body = None
    req = request.Request(url, data=body, headers=headers, method="GET" if body is None else "POST")
    check_cancelled()
    try:
        # urllib is needed for multipart/streaming; disable redirects to keep API credentials on the fixed origin.
        with request.build_opener(request.ProxyHandler({}), _NoRedirect()).open(req, timeout=API_TIMEOUT) as response:
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise Hyper3DError("Hyper3D response exceeded the size limit", "response_too_large")
            try:
                data = json_loads(raw.decode("utf-8"))
            except Exception:
                raise Hyper3DError("Hyper3D returned invalid JSON", "invalid_response")
    except error.HTTPError as exc:
        retry_after = exc.headers.get("Retry-After")
        details = dict(_http_error_details(exc), http_status=exc.code)
        if retry_after and re.fullmatch(r"[A-Za-z0-9 ,:+-]{1,80}", retry_after):
            details["retry_after"] = retry_after
        raise Hyper3DError("Hyper3D rejected the request; do not automatically resubmit a generation", "provider_http_error", **details)
    except (error.URLError, TimeoutError, OSError):
        raise Hyper3DError("Hyper3D request outcome is unknown; do not automatically resubmit a generation", "network_error", submission_may_have_succeeded=endpoint in {"rodin", "rodin_agentic", "bang", "rodin_texture_only"})
    if not isinstance(data, dict):
        raise Hyper3DError("Hyper3D returned an unexpected response shape", "invalid_response")
    if data.get("error"):
        code = data["error"] if isinstance(data["error"], str) and data["error"] in PROVIDER_ERRORS else "unknown"
        raise Hyper3DError("Hyper3D reported an error; inspect account usage before resubmitting", "provider_error", provider_code=code)
    return _clean(data)


def _parameters(parameters):
    if parameters is None:
        return {}
    if not isinstance(parameters, dict):
        raise Hyper3DError("parameters must be an object")
    result = dict(parameters)
    for key, value in result.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key):
            raise Hyper3DError("parameters contains an invalid field name")
        if key.lower() in {"authorization", "api_key", "apikey", "base_url", "url", "images", "image", "model", "model_path", "image_paths"}:
            raise Hyper3DError("parameters contains a reserved field; use the file arguments and process environment")
        if not _json_value(value):
            raise Hyper3DError("parameters must contain finite JSON values")
    return result


def _json_value(value):
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _json_value(item) for key, item in value.items())
    return False


def _enum(parameters, field, choices):
    if field in parameters and (not isinstance(parameters[field], str) or parameters[field] not in choices):
        raise Hyper3DError("Invalid " + field + " option")


def _number(parameters, field, minimum, maximum, integer=False):
    if field not in parameters:
        return
    value = parameters[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum or (integer and not isinstance(value, int)):
        raise Hyper3DError(field + " is outside the documented range")


def _common(parameters):
    for field in ("prompt", "instruction", "asset_id"):
        if field in parameters and not isinstance(parameters[field], str):
            raise Hyper3DError(field + " must be text")
    _number(parameters, "seed", 0, 65535, True)
    _number(parameters, "escore", 0, 10)
    _enum(parameters, "mesh_mode", {"Raw", "Quad"})
    _enum(parameters, "geometry_file_format", FORMATS)
    _enum(parameters, "material", MATERIALS)
    _enum(parameters, "quality", {"high", "medium", "low", "extra-low"})
    _enum(parameters, "texture_mode", {"legacy", "extreme-low", "low", "medium", "high", "extreme-high"})
    _enum(parameters, "resolution", {"Basic", "High"})
    for field in ("soft", "quad_normal", "TAPose", "use_original_alpha", "preview_render", "hd_texture", "uhd_texture", "is_micro", "texture_delight", "mesh_simplify", "mesh_smooth"):
        if field in parameters and not isinstance(parameters[field], bool):
            raise Hyper3DError(field + " must be boolean")


def _file(path, extensions, limit=MAX_UPLOAD):
    if not isinstance(path, str) or not path:
        raise Hyper3DError("Upload paths must be nonempty strings")
    item = Path(path).expanduser().resolve()
    if not item.is_file() or item.suffix.lower() not in extensions:
        raise Hyper3DError("Upload must be an existing file with a supported extension")
    if item.stat().st_size <= 0 or item.stat().st_size > limit:
        raise Hyper3DError("Upload is empty or exceeds the local upload size limit")
    return item


def _images(image_paths, maximum=5, limit=MAX_UPLOAD):
    if image_paths is None:
        return []
    if not isinstance(image_paths, list) or len(image_paths) > maximum:
        raise Hyper3DError("image_paths exceeds the documented image count")
    return [_file(path, IMAGE_EXTENSIONS, limit) for path in image_paths]


def _multipart(parameters, uploads):
    boundary = "hyper3d-" + uuid.uuid4().hex
    parts = []
    total = 0
    for field, value in parameters.items():
        if isinstance(value, list) and not value:
            continue
        if field == "addons" and isinstance(value, list):
            # Match the provider SDK's comma-separated addon form field.
            value = ",".join(value)
        encoded = value if isinstance(value, str) else json_dumps(value)
        parts.append(("--" + boundary + '\r\nContent-Disposition: form-data; name="' + field + '"\r\n\r\n' + encoded + "\r\n").encode("utf-8"))
    for field, path in uploads:
        check_cancelled()
        size = path.stat().st_size
        total += size
        if total > MAX_UPLOAD:
            raise Hyper3DError("Combined uploads exceed the local upload size limit")
        # Never copy user-controlled filenames into multipart headers.
        name = "upload" + path.suffix.lower()
        header = '--' + boundary + '\r\nContent-Disposition: form-data; name="' + field + '"; filename="' + name + '"\r\nContent-Type: ' + (mimetypes.guess_type(name)[0] or "application/octet-stream") + '\r\n\r\n'
        with path.open("rb") as stream:
            content = stream.read(size + 1)
        if len(content) != size:
            raise Hyper3DError("Upload changed while being read")
        parts.extend([header.encode("utf-8"), content, b"\r\n"])
    parts.append(("--" + boundary + "--\r\n").encode("ascii"))
    return b"".join(parts), "multipart/form-data; boundary=" + boundary


def _submit(endpoint, parameters, uploads):
    data = _api(endpoint, multipart=_multipart(parameters, uploads))
    task_uuid = data.get("uuid")
    jobs = data.get("jobs") or data.get("job")
    if not isinstance(task_uuid, str) or not task_uuid or not isinstance(jobs, dict) or not isinstance(jobs.get("subscription_key"), str) or not jobs["subscription_key"]:
        raise Hyper3DError("Submission returned no complete task identity; inspect account usage before resubmitting", "submission_ambiguous", submission_may_have_succeeded=True)
    return {"task_uuid": task_uuid, "subscription_key": jobs["subscription_key"], "data": data}


def create_rodin_task(parameters, image_paths=None):
    parameters = _parameters(parameters)
    parameters.setdefault("tier", "Gen-2.5-Medium")
    _common(parameters)
    _enum(parameters, "tier", TIERS)
    images = _images(image_paths)
    if not images and not parameters.get("prompt", "").strip():
        raise Hyper3DError("Rodin requires a prompt or one to five images")
    if len(parameters.get("prompt", "")) > 1024:
        raise Hyper3DError("prompt must contain at most 1024 characters")
    tier = parameters["tier"]
    mesh_mode = parameters.get("mesh_mode", "Raw" if tier.startswith("Gen-2.5-") else "Quad")
    first_generation = {"condition_mode", "mesh_simplify", "mesh_smooth"}
    second_generation = {"soft", "detail_level", "quad_normal", "is_symmetric", "hd_texture"}
    latest_generation = {"texture_mode", "image_label", "uhd_texture", "is_micro", "geometry_instruct_mode", "texture_delight"}
    forbidden = first_generation if tier.startswith("Gen-2") else second_generation | latest_generation
    if tier == "Gen-2":
        forbidden |= latest_generation
    if any(field in parameters for field in forbidden):
        raise Hyper3DError("A parameter is unsupported by the selected Rodin generation")
    if "mesh_simplify" in parameters and mesh_mode != "Raw":
        raise Hyper3DError("mesh_simplify requires Raw mesh mode")
    if "mesh_smooth" in parameters and mesh_mode != "Quad":
        raise Hyper3DError("mesh_smooth requires Quad mesh mode")
    maximum = 2000000 if tier in {"Gen-2.5-High", "Gen-2.5-Extreme-High"} else 1000000 if tier.startswith("Gen-2") else 200000
    _number(parameters, "quality_override", 500, min(maximum, 200000) if mesh_mode == "Quad" else maximum, True)
    _number(parameters, "detail_level", 1, 3, True)
    _enum(parameters, "is_symmetric", {"symmetric", "balanced", "asymmetric", "unknown"})
    _enum(parameters, "condition_mode", {"concat", "fuse"})
    _enum(parameters, "geometry_instruct_mode", {"faithful", "creative"})
    if parameters.get("is_micro") and tier != "Gen-2.5-Extreme-High":
        raise Hyper3DError("is_micro requires Gen-2.5-Extreme-High")
    if parameters.get("geometry_instruct_mode") == "creative" and tier in {"Gen-2.5-Low", "Gen-2.5-Extreme-Low"}:
        raise Hyper3DError("creative geometry instructions require Gen-2.5-Medium or higher")
    if "bbox_condition" in parameters:
        values = parameters["bbox_condition"]
        if not isinstance(values, list) or len(values) != 3 or any(isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 2048 for v in values):
            raise Hyper3DError("bbox_condition requires three integers from 1 to 2048")
    if "addons" in parameters and (not isinstance(parameters["addons"], list) or any(v != "HighPack" for v in parameters["addons"])):
        raise Hyper3DError("addons supports only HighPack")
    if "image_label" in parameters:
        values = parameters["image_label"]
        if not isinstance(values, list) or len(values) > len(images) or any(v not in {"F", "FL", "FR", "L", "R", "B", "BL", "BR", "U", "D", "?"} for v in values):
            raise Hyper3DError("image_label must contain supported labels for uploaded images")
    return _submit("rodin", parameters, [("images", image) for image in images])


def create_agentic_task(parameters, image_paths=None):
    parameters = _parameters(parameters)
    _common(parameters)
    if len(parameters.get("prompt", "")) > 1024:
        raise Hyper3DError("prompt must contain at most 1024 characters")
    _enum(parameters, "tier", {"basic", "standard", "pro"})
    _enum(parameters, "export_type", {"glb", "usdz", "fbx", "stl"})
    images = _images(image_paths, limit=25 * 1024 * 1024)
    if not images:
        raise Hyper3DError("Agentic requires one to five images")
    return _submit("rodin_agentic", parameters, [("images", image) for image in images])


def create_bang_task(parameters, model_path=None, image_paths=None):
    parameters = _parameters(parameters)
    _common(parameters)
    _number(parameters, "strength", 1, 12, True)
    _number(parameters, "quality_override", 500, 2000000, True)
    _number(parameters, "reference_scale", 0, 1)
    images = _images(image_paths, maximum=1)
    asset_id = parameters.get("asset_id", "").strip()
    if bool(asset_id) == bool(model_path):
        raise Hyper3DError("Bang requires exactly one asset_id or model_path")
    if asset_id:
        if images or "prompt" in parameters:
            raise Hyper3DError("Bang asset_id mode cannot include images or prompt")
        uploads = []
    else:
        model = _file(model_path, (MODEL_EXTENSIONS - {".gltf"}) | {".usd", ".usda", ".usdc"})
        if not images and (parameters.get("material", "PBR") != "None" or parameters.get("instruction", "").strip()):
            raise Hyper3DError("Bang model mode requires an image for texturing or instructions")
        uploads = [("model", model)] + [("image", image) for image in images]
    return _submit("bang", parameters, uploads)


def create_texture_task(parameters, model_path, image_paths=None):
    parameters = _parameters(parameters)
    _common(parameters)
    _number(parameters, "reference_scale", 0.5, 1)
    _enum(parameters, "material", MATERIALS - {"None"})
    images = _images(image_paths, maximum=1)
    if not images:
        raise Hyper3DError("Texture generation requires exactly one image")
    model = _file(model_path, MODEL_EXTENSIONS)
    return _submit("rodin_texture_only", parameters, [("model", model), ("image", images[0])])


def _identifier(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 1024 or any(ord(c) < 32 for c in value):
        raise Hyper3DError(field + " must be nonempty text without control characters")
    return value


def get_task_status(subscription_key):
    data = _api("status", {"subscription_key": _identifier(subscription_key, "subscription_key")})
    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs or any(not isinstance(job, dict) or job.get("status") not in {"Waiting", "Generating", "Done", "Failed"} for job in jobs):
        raise Hyper3DError("Hyper3D returned an invalid or empty job list", "invalid_response")
    return {"data": data, "jobs": jobs, "all_done": all(job["status"] == "Done" for job in jobs)}


def get_download_links(task_uuid):
    data = _api("download", {"task_uuid": _identifier(task_uuid, "task_uuid")})
    files = data.get("list")
    if not isinstance(files, list) or not files or any(not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("url"), str) for item in files):
        raise Hyper3DError("Hyper3D returned an invalid or empty download list", "invalid_response")
    return {"data": data, "files": files}


def get_balance(usage_page=None):
    if usage_page is not None:
        _number({"usage_page": usage_page}, "usage_page", 1, 2147483647, True)
    data = _api("check_balance", usage_page=usage_page)
    balance = data.get("balance")
    if isinstance(balance, bool) or not isinstance(balance, (int, float)) or (isinstance(balance, float) and not math.isfinite(balance)) or ("usage" in data and not isinstance(data["usage"], list)):
        raise Hyper3DError("Hyper3D returned invalid balance information", "invalid_response")
    return {"data": data}


def _public_url(url):
    try:
        parsed = parse.urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None, 443):
            raise ValueError()
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise ValueError()
        return addresses[0][4][0]
    except (ValueError, OSError):
        raise Hyper3DError("Asset URL must resolve exclusively to public HTTPS addresses", "unsafe_download_url")


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address, **kwargs):
        self._address = address
        super().__init__(host, **kwargs)

    def connect(self):
        self.sock = socket.create_connection((self._address, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


class _PinnedHTTPSHandler(request.HTTPSHandler):
    def __init__(self, address):
        super().__init__()
        self.address = address

    def https_open(self, req):
        def connection(host, **kwargs):
            return _PinnedHTTPSConnection(host, self.address, **kwargs)
        return self.do_open(connection, req, context=ssl.create_default_context())


def _open_asset(url, deadline=None):
    for redirect in range(6):
        address = _public_url(url)
        opener = request.build_opener(request.ProxyHandler({}), _NoRedirect(), _PinnedHTTPSHandler(address))
        try:
            return opener.open(request.Request(url, headers={"Accept-Encoding": "identity"}), timeout=_remaining(deadline))
        except error.HTTPError as exc:
            if exc.code not in {301, 302, 303, 307, 308} or not exc.headers.get("Location"):
                raise Hyper3DError("Asset host rejected the download", "asset_http_error", http_status=exc.code)
            if redirect == 5:
                raise Hyper3DError("Asset download exceeded the redirect limit", "asset_redirect_limit")
            url = parse.urljoin(url, exc.headers["Location"])
            exc.close()
        except (error.URLError, OSError):
            raise Hyper3DError("Asset download failed; refresh signed links before retrying", "asset_network_error")


def _remaining(deadline):
    remaining = 60 if deadline is None else deadline - time.monotonic()
    if remaining <= 0:
        raise Hyper3DError("Asset download exceeded the 600 second deadline", "asset_timeout")
    return min(60, remaining)


def _safe_name(name):
    if (not isinstance(name, str) or not name or name in {".", ".."} or len(name) > 240
            or any(ord(c) < 32 for c in name) or re.search(r'[\\/:<>"|?*]', name)
            or name.endswith((".", " ")) or name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL"}
            or re.fullmatch(r"(?:COM|LPT)[1-9]", name.split(".")[0], re.IGNORECASE)):
        raise Hyper3DError("Provider supplied an unsafe download filename", "unsafe_filename")
    return name


def download_assets(task_uuid, subscription_key, output_dir, filenames=None):
    deadline = time.monotonic() + 600
    task_uuid = _identifier(task_uuid, "task_uuid")
    _identifier(subscription_key, "subscription_key")
    if not isinstance(output_dir, str) or not output_dir:
        raise Hyper3DError("output_dir must be a nonempty local path")
    root = Path(output_dir).expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise Hyper3DError("output_dir must be a directory")
    if filenames is not None and (not isinstance(filenames, list) or not filenames or any(not isinstance(name, str) for name in filenames) or len(set(filenames)) != len(filenames)):
        raise Hyper3DError("filenames must be a nonempty list of distinct provider filenames")
    status = get_task_status(subscription_key)
    _remaining(deadline)
    if any(job["status"] == "Failed" for job in status["jobs"]):
        raise Hyper3DError("Generation failed; no files were downloaded", "task_failed")
    if not status["all_done"]:
        raise Hyper3DError("All jobs must be Done before downloading", "task_not_ready", job_statuses=[job["status"] for job in status["jobs"]])
    available = get_download_links(task_uuid)["files"]
    _remaining(deadline)
    names = [_safe_name(item["name"]) for item in available]
    if len(set(name.casefold() for name in names)) != len(names):
        raise Hyper3DError("Provider download names collide", "filename_collision")
    if filenames is not None and any(name not in names for name in filenames):
        raise Hyper3DError("Requested filename was not returned by Hyper3D", "unknown_filename")
    selected = [item for item in available if filenames is None or item["name"] in filenames]
    for item in selected:
        target = root / item["name"]
        if target.exists() or target.is_symlink():
            raise Hyper3DError("Download would overwrite an existing file", "file_exists")
        _public_url(item["url"])
    root.mkdir(parents=True, exist_ok=True)
    files = []
    total = 0
    try:
        for item in selected:
            check_cancelled()
            target = root / item["name"]
            handle, temporary = tempfile.mkstemp(prefix=".hyper3d-", dir=str(root))
            try:
                digest = hashlib.sha256()
                size = 0
                with os.fdopen(handle, "wb") as stream, _open_asset(item["url"], deadline=deadline) as response:
                    length = response.headers.get("Content-Length")
                    if length is not None and (not length.isdigit() or int(length) > MAX_ASSET):
                        raise Hyper3DError("Asset exceeds the download size limit", "asset_too_large")
                    while True:
                        check_cancelled()
                        remaining = _remaining(deadline)
                        network_socket = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
                        if network_socket is not None:
                            network_socket.settimeout(remaining)
                        chunk = response.read1(64 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        total += len(chunk)
                        if size > MAX_ASSET or total > MAX_TOTAL:
                            raise Hyper3DError("Asset exceeds the download size limit", "asset_too_large")
                        digest.update(chunk)
                        stream.write(chunk)
                    if not size or (length is not None and size != int(length)):
                        raise Hyper3DError("Asset download was empty or incomplete", "asset_incomplete")
                    stream.flush()
                    os.fsync(stream.fileno())
                # Hard-link publication is atomic and refuses existing paths on Windows and POSIX.
                os.link(temporary, str(target))
                record = {"path": str(target), "name": item["name"], "size_bytes": size, "sha256": digest.hexdigest()}
                files.append(record)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    except Hyper3DError as exc:
        exc.details["completed_files"] = files
        raise
    except Exception:
        raise Hyper3DError("Asset download failed; completed files are preserved", "asset_download_failed", completed_files=files)
    models = [item for item in files if Path(item["path"]).suffix.lower() in MODEL_EXTENSIONS | {".usd", ".usda", ".usdc", ".abc", ".blend"}]
    descriptors = []
    if models:
        descriptors.append({"asset_id": "hyper3d:" + task_uuid, "variants": [{"local_path": item["path"], "format": Path(item["path"]).suffix.lstrip(".").lower()} for item in models], "extra": {"provider": "hyper3d", "task_uuid": task_uuid, "source_coordinate_system": "unknown", "source_units": "unknown", "license": "not supplied by API", "files": files}})
    return {"task_uuid": task_uuid, "files": files, "asset_descriptors": descriptors}
