# Cross-DCC workflows

The same skill is installed once into the shared skill path. Use the tool
slugs returned by `load_skill`; namespaced names are shown below for clarity.
Paths refer to the adapter machine, which must be able to read input files and
write the selected output directory.

## Text or image to 3D

```json
{
  "parameters": {
    "tier": "Gen-2.5-Medium",
    "prompt": "A weathered wooden treasure chest, game prop",
    "geometry_file_format": "glb",
    "material": "PBR"
  }
}
```

Pass this to `hyper3d__create_rodin_task`. For image or multiview generation,
add `image_paths: ["C:/references/front.png", "C:/references/back.png"]`.
Up to five images are supported. Optional `image_label` values correspond to
the supplied images in order, for example `["F", "B"]`.

Persist `task_uuid` and `subscription_key` from the successful result.
Call `hyper3d__get_task_status` with `{"subscription_key":"..."}` until
all returned jobs are `Done`. Then call:

```json
{
  "task_uuid": "saved-provider-task-uuid",
  "subscription_key": "saved-provider-subscription-key",
  "output_dir": "C:/assets/chest-run-001"
}
```

Use `hyper3d__download_assets`. A returned descriptor has local model variants
and provider provenance. Pass it to a typed scene import tool discovered on the
target Maya, Blender, Houdini, 3ds Max, Unreal or other adapter. Importer
availability and GLB/FBX/OBJ/USDZ/STL support depend on that host and version.
Core validates the descriptor shape; native import requires separate acceptance.

## Host import checks

Inspect the typed import tool's current schema before calling it. The tested
Blender adapter 0.2.4 accepted the returned `AssetDescriptor` unchanged. Maya
adapter 0.9.42 required its legacy `asset` shape: map a supported variant's
`local_path` to `asset.path` and retain its `format`. This is an importer-boundary
conversion; the skill continues to return the shared descriptor contract.

Check geometry, UVs, material bindings and scene scale after import. In live
testing, OBJ outputs had UVs but no MTL or `usemtl` declarations, so nearby PNG
files did not bind automatically. Assign those textures explicitly. FBX and
GLB carried usable texture information in the tested Blender imports; a
successful scene import alone does not prove rendered PBR fidelity.

For OBJ, source units and axes remain unknown; the Maya import used centimetres
as a caller assumption. The FBX importer applied its native unit conversion:
the tested asset measured approximately 190 cm in Maya and 1.9 Blender units.
Confirm the destination scene settings and intended asset size. See
[per-case acceptance results](https://github.com/dcc-mcp/dcc-ai-hyper3d/blob/main/docs/live-acceptance-2026-10-23.md).

## Topology or texture on an existing model

For Bang, choose an `asset_id` in `parameters` or supply `model_path` and
the image/parameters required by the chosen material mode. The two input modes
are mutually exclusive. Bang options such as `mesh_mode`, `quality` and
`quality_override` control topology; this is a paid provider operation.

For `hyper3d__create_texture_task`, supply the local mesh in `model_path`,
and exactly one reference image in `image_paths`, plus the optional prompt.
Consult [API constraints](API.md) before choosing format-specific options.

## Local acceptance harness

This harness requires a source checkout. `scripts/live_acceptance.py` lives at
the repository root and is deliberately outside the installable skill bundle.
Run it from the repository root. Set the API key in the process environment,
then pipe one JSON object to
`python scripts/live_acceptance.py`. This PowerShell example reads balance
without submitting a paid generation:

```powershell
'{"operation":"balance","evidence_dir":"local-evidence/your-run","arguments":{}}' | python scripts/live_acceptance.py
```

The stdout JSON contains `success`, `api_success`, `state_file` and
`report_file`. Exit status is zero only when the action succeeds. A status
query that finds a failed generation returns `success: false` with
`api_success: true`, distinguishing a completed query from a successful job.

Use `operation: "submit"` with an explicit `kind` of `rodin`, `agentic`, `bang`
or `texture`, and pass that runtime function's arguments in `arguments`.
Each invocation performs one action without polling or retrying. Paid actions
always require a separate, explicit invocation.

For `status`, pass a prior private `state_file` to reuse its subscription key.
For `download`, pass that state file and `arguments.output_dir`, with optional
`arguments.filenames`. The state carries identities through status calls;
download results preserve the runtime's hashes and asset descriptors.

The evidence directory must be writable before an API call starts. On POSIX,
it must deny group and other access; existing permissions are never changed,
and private files are created with mode `0600`. Windows uses inherited
filesystem ACLs, so choose an evidence directory with appropriate access.
Private state retains job credentials and full results with the API key removed;
stdout and the separate report redact credentials, provider identities and
remote URLs. Keep private state local. `local-evidence/` is ignored by Git.
Do not publish its files, generated assets, or reference images inadvertently.

## Recovery

- A missing key or 401/403: set the credential in the adapter environment and
  restart that adapter. Keep keys out of chat and command history.
- A 429: honor the retry interval and query known tasks later. Do not resubmit
  a charged task automatically.
- A submission transport timeout: inspect the provider account before creating
  another task; no public task-list or idempotency endpoint is documented.
- `Waiting` or `Generating`: poll the same `subscription_key` with backoff.
- `Failed`: preserve the response for diagnosis; a new submission may cost
  credits. No cancel endpoint is available.
- Expired links: query `get_download_links` again using `task_uuid`.
- Partial download: retain completed files and request only missing filenames.
  Existing files are never overwritten. Archives remain archives.

The software is MIT licensed. Generated assets and supplied reference material
are subject to the provider terms and the user's rights; no CC0/SPDX license
is inferred. Descriptor provenance records the provider without asserting
ownership, physical units or source orientation.
