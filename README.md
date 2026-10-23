# DCC-AI Hyper3D

Hyper3D's public API as a reusable [DCC-MCP](https://github.com/dcc-mcp)
skill. One host-neutral skill supplies cloud generation, model processing,
texture generation, task queries and local asset delivery to any adapter.

## Capabilities

| Tool | Operation |
| --- | --- |
| `create_rodin_task` | Text/image/multiview generation, Gen 1/1.5, Gen 2 and Gen 2.5, all documented options |
| `create_agentic_task` | Image-driven Agentic Beta, basic/standard/pro |
| `create_bang_task` | Split/process an existing Rodin asset or uploaded model, with topology controls |
| `create_texture_task` | Generate textures from an uploaded model and reference image |
| `get_task_status` | Query every sub-job using the returned subscription key |
| `get_download_links` | Obtain fresh temporary result URLs |
| `get_balance` | Read account balance and paginated usage history |
| `download_assets` | Check completion, save selected/all outputs, return hashes and asset descriptors |

This covers the seven documented API endpoints. Files upload inline with the
submission. The public API has no separate cancellation, task-list, delete,
rigging or standalone remesh endpoint. See the full
[API reference and constraints](skill/hyper3d/references/API.md), verified
against [Hyper3D documentation](https://docs.hyper3d.ai/en) on 2026-10-23.

## Install

Requires Python 3.7+, `dcc-mcp-core>=0.20.44`, a current `dcc-mcp-cli`,
network access and a Hyper3D API account. The bundle adds no Python dependency.

Set **`HYPER3D_API_KEY`** in the environment of the process running the skill
before starting the adapter. The provider's `RODIN_API_KEY` spelling is also
accepted. Store the credential outside this repository; never pass it as a
tool argument.

The source repository can be installed at an explicitly reviewed commit:

```text
dcc-mcp-cli marketplace add-repo dcc-mcp/dcc-ai-hyper3d --commit <FULL_40_CHARACTER_COMMIT_SHA> --dcc any
```

After the official catalog entry is merged, install through the shared catalog:

```text
dcc-mcp-cli marketplace install dcc-ai-hyper3d --dcc all
```

Alternatively clone this repository and add its absolute `skill` directory to
`DCC_MCP_SKILL_PATHS` for the adapter process. Separate multiple paths with
the platform's path separator. Restart or reload skill discovery, search for
`hyper3d`, then load the skill and use the tool slugs it returns.

Shared installation makes the same tools available to Maya, Blender, Houdini,
3ds Max, Unreal and other DCC-MCP adapters. The adapter owns native scene
import and must support the selected output format.

## Use

Submit `create_rodin_task` with, for example:

```json
{
  "parameters": {
    "tier": "Gen-2.5-Medium",
    "prompt": "A wooden treasure chest, game-ready prop",
    "geometry_file_format": "glb",
    "material": "PBR"
  }
}
```

All official provider options are declared inside `parameters`, preserving
their exact names. Add `image_paths` for image/multiview input. Model uploads
use `model_path`. Paths are local to the adapter machine. An omitted Rodin tier
uses `Gen-2.5-Medium` explicitly, rather than the provider's legacy default.

Successful submission returns `context.task_uuid` and
`context.subscription_key`; preserve both. Wait at least five seconds, query
`get_task_status`, and back off toward thirty seconds while work is pending.
When every job reports `Done`, call `download_assets` with both identifiers
and an absolute `output_dir`. Inspect `context.files` and
`context.asset_descriptors`, then hand a supported model descriptor to the
target adapter's typed importer. See [workflows and recovery](skill/hyper3d/references/WORKFLOWS.md).

Generation consumes provider credits and has no automatic retries. A transport
timeout can leave submission acceptance unknown. Recheck the provider account
before submitting again. Signed URLs expire and API files have limited
retention; download promptly. Completed local files are never overwritten.

Descriptors follow the core `AssetDescriptor` shape. Provenance records the
provider and task; generated asset license, physical units and orientation are
not supplied by the API and must be verified before import. MIT covers this
integration's code. It does not grant rights to uploaded/generated content.

## Validate

```text
python -m pip install dcc-mcp-core==0.20.44 pyyaml jsonschema
python -m unittest discover -s tests -v
dcc-mcp-cli lint skill/hyper3d --warnings-as-errors --no-update-maintenance
```

Tests use offline fixtures and do not spend account credits. CI checks Python
3.7 and 3.12 on Windows and Linux. The [2026-10-23 live acceptance](docs/live-acceptance-2026-10-23.md)
covered all four paid submission routes, five downloads, and native imports in
Maya 2027.2 and Blender 5.2.0, at a total experiment cost of 2.5 credits.
See that report for per-format material and unit limits. Agentic remains a
provider beta.

The [2026-10-24 expanded acceptance](docs/live-acceptance-2026-10-24.md)
adds 21 completed paid cases for 14.5 credits: every documented Rodin and
Agentic tier, Bang upload/instruction modes, all six texture modes and all five
output formats across the sampled workflows. It records actual output hashes
and measured limits; this is representative coverage, not every option
combination. The resulting assets also feed a native Godot showcase.

From a source checkout, [the acceptance harness](skill/hyper3d/references/WORKFLOWS.md#local-acceptance-harness)
reads one explicit action from JSON stdin and records private state separately
from a sanitized report. It never retries a paid submission automatically.
