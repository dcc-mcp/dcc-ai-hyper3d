---
name: hyper3d
description: >-
  Generate 3D assets with Hyper3D Rodin Gen 1/1.5, Gen 2, Gen 2.5 or Agentic;
  change topology with Bang, generate textures on existing meshes, inspect
  task status and balance, and download assets for any DCC-MCP adapter.
license: MIT
compatibility: "Python 3.7+, dcc-mcp-core 0.20.44+; Hyper3D API credential and network access"
metadata:
  dcc-mcp:
    version: "0.1.2"
    dcc: python
    layer: domain
    tags: [pipeline, ai, hyper3d, rodin, 3d-generation, text-to-3d, image-to-3d, cross-dcc]
    search-hint: "Hyper3D Rodin Gen 2.5 Gen2 Agentic Bang text image multiview 3D mesh PBR texture remesh quad download balance"
    tools: tools.yaml
    runtimes: runtimes.yaml
    skill-reference-docs:
      - "references/*.md"
---

# Hyper3D

Use this skill for Hyper3D cloud generation and local asset delivery. Use the
target adapter's typed import tools to bring the returned files into its scene.
All tools run at `affinity: any`; cloud work never calls a DCC scene API.

Set `HYPER3D_API_KEY` in the adapter process environment before starting it.
`RODIN_API_KEY` is also accepted. Never put credentials in tool arguments or
commit them. Calls use the fixed `https://api.hyper3d.com/api/v2` endpoint.

1. Read `get_balance` when checking credential readiness or budget.
2. Choose `create_rodin_task` for text/image/multiview generation;
   `create_agentic_task` for the Agentic Beta;
   `create_bang_task` for topology/material processing of an existing Rodin asset
   or uploaded mesh; `create_texture_task` for textures on an uploaded mesh.
3. Supply provider options in `parameters` using the exact documented names.
   Supply local files using `image_paths` / `model_path`; files are uploaded
   inline as multipart parts. See [API coverage](references/API.md).
4. Save both returned `task_uuid` and `subscription_key`. Check
   `get_task_status` after at least 5 seconds; back off toward 30 seconds while
   waiting. Honor a returned retry interval. Every job must report `Done`.
5. Call `download_assets` with those two identifiers and a new output directory.
   It rechecks status, obtains fresh signed links, saves files without replacing
   existing files, and returns checksums and `asset_descriptors`.
6. Pass a supported model descriptor to the destination adapter's import tool.
   Download every needed material sidecar together. Verify source axis, units,
   license and importer format support before scene mutation; the API does not
   provide verified coordinate or licensing metadata.

Inspect the destination import schema. Blender adapter 0.2.4 accepted the shared
descriptor unchanged; Maya adapter 0.9.42 required a legacy `asset` containing
the selected variant's `path` and `format`. Keep this mapping at the host import
boundary. In the tested OBJ output, no MTL or `usemtl` bindings were supplied;
downloaded texture images therefore require material assignment. See
[host import checks](references/WORKFLOWS.md#host-import-checks).

Generation/processing consumes account credits. A submission timeout can mean
the provider accepted the request: do not automatically submit it again. The
API exposes no documented cancel, task-list, deletion, account-key creation,
standalone upload or separate remesh endpoint. Topology options belong to Rodin
and Bang. `get_download_links` returns temporary signed URLs; keep them private.

Errors retain recovery context. If a multi-file download partially succeeds,
keep its verified files and retry only missing names with `filenames`, or use a
new output directory. There is no archive extraction or scene import side effect.

Multipart fields use lowercase booleans and JSON text for nonempty arrays.
Empty lists are omitted so optional fields use provider defaults; explicitly
sending `addons: []` as a form part was rejected in live testing. HTTP errors
retain bounded, sanitized validation details without credentials or remote URLs.

For cross-DCC examples see [workflows](references/WORKFLOWS.md).
