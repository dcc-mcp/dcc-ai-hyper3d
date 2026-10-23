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

## Topology or texture on an existing model

For Bang, choose an `asset_id` in `parameters` or supply `model_path` and
the image/parameters required by the chosen material mode. The two input modes
are mutually exclusive. Bang options such as `mesh_mode`, `quality` and
`quality_override` control topology; this is a paid provider operation.

For `hyper3d__create_texture_task`, supply the local mesh in `model_path`,
and exactly one reference image in `image_paths`, plus the optional prompt.
Consult [API constraints](API.md) before choosing format-specific options.

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
