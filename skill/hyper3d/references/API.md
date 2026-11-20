# Hyper3D public API contract

Request coverage for the eight implemented provider endpoints below was verified against the English official documentation on 2026-11-19. Clean Topology availability was rechecked on 2026-11-06; see its dated section below. This is a compact integration reference; the linked upstream schemas remain authoritative. It does not establish website or native-plugin feature parity. Uploads accompany multipart submissions; this bundle's topology and target-face controls belong to Rodin, PolyGen or Bang. `TAPose` requests rest-pose conditioning, not a skeleton or animation. The provider also documents [Rigging](https://docs.hyper3d.ai/en/api-specification/rigging) and [Generate Images](https://docs.hyper3d.ai/en/api-specification/images); these endpoints are not implemented here.

## Transport and lifecycle

Base URL: `https://api.hyper3d.com/api/v2`. Authenticate API calls with `Authorization: Bearer <RODIN_API_KEY>`; load the key from an environment variable or secret store. Never forward that header to result-download hosts. [Introduction](https://docs.hyper3d.ai/en), [Quick Start](https://docs.hyper3d.ai/en/get-started/quick-start)

| Method | Path | Body | Operation |
| --- | --- | --- | --- |
| POST | `/rodin` | multipart | Gen-1/1.5, Gen-2, Gen-2.5 generation |
| POST | `/rodin_agentic` | multipart | Agent-selected generation; beta |
| POST | `/polygen` | multipart | Low-poly generation from an asset, model, images or text |
| POST | `/rodin_texture_only` | multipart | Texture an uploaded model |
| POST | `/bang` | multipart | Split a generated asset or uploaded model |
| POST | `/status` | JSON | Inspect every sub-job |
| POST | `/download` | JSON | Obtain result URLs |
| GET | `/check_balance` | query | Balance and optional usage history |

Normal accepted submissions include `uuid`, `jobs:{uuids,subscription_key}`, and `consumed`; optional metadata includes `submit_time`, `message`, and the actual `prompt`. Agentic uses singular `job`, not `jobs`. Check both HTTP status and body `error`; HTTP 201 can contain a rejection. Require a nonempty task UUID and subscription key before polling. [Gen-2 response](https://docs.hyper3d.ai/en/api-specification/rodin-gen2), [Agentic response](https://docs.hyper3d.ai/en/api-specification/rodin-agentic)

`POST /status` takes `{"subscription_key":"..."}` and returns `jobs:[{uuid,status,queue_length?}]`, with optional `error` and `message`. States are `Waiting`, `Generating`, `Done`, `Failed`. Queue length is approximate. Abort on any failed sub-job; continue only when the nonempty collection is entirely `Done`. [Check Status](https://docs.hyper3d.ai/en/api-specification/check-status)

`POST /download` takes `{"task_uuid":"<top-level uuid>"}` and returns `list:[{name,url}]`, with optional `error`. Call only after every job completes: early calls can return incomplete files. Signed URLs expire; download promptly and retain local files. The documentation supplies no result-host allowlist or fixed URL lifetime. [Download Results](https://docs.hyper3d.ai/en/api-specification/download-results)

Wait at least five seconds before the first status call, increase polling delay, and enforce a deadline. Honor HTTP 429 `Retry-After`. A network timeout during a paid submission has an unknown acceptance outcome; avoid an automatic duplicate submission. [Quick Start](https://docs.hyper3d.ai/en/get-started/quick-start)

## Shared Rodin fields

`images`: ordered, repeated multipart file parts, one to five; omit for text-only generation. `prompt`: optional with images, otherwise required, maximum 1024 characters. The first image guides materials. Send `tier` explicitly: omission selects legacy `Regular`.

| Field | Values / limits |
| --- | --- |
| `geometry_file_format` | `glb` (default), `usdz`, `fbx`, `obj`, `stl` |
| `material` | `PBR` (default), `Shaded`, `All`, `Hybrid`, `None` |
| `mesh_mode` | `Quad`, `Raw`; defaults vary below |
| `quality` | `high`, `medium` (default), `low`, `extra-low` |
| `seed` | integer 0–65535 |
| `bbox_condition` | exactly three integers 1–2048, width X / height Y / length Z |
| `addons` | array containing `HighPack`; default `[]` |
| `TAPose`, `use_original_alpha`, `preview_render` | boolean; default false |

These fields are shared across the generation-family schemas. No general Rodin image byte-size limit is stated on those pages. [Gen-1/1.5 schema](https://docs.hyper3d.ai/en/api-specification/rodin-gen1-1-5), [BBOX Control](https://docs.hyper3d.ai/en/api-specification/bbox-control)

## Gen-1/1.5

`tier`: `Sketch`, `Regular`, `Detail`, `Smooth`. Default mesh: `Quad`. `quality_override`: integer 500–200000, overriding `quality`. Both mesh modes use high/medium/low/extra-low targets 50000/18000/8000/4000.

Additional fields: `condition_mode=concat|fuse` (default `concat`); `mesh_simplify` boolean (default true, Raw only); `mesh_smooth` boolean (default false, Quad only). Concat means multiple views of one object; fuse combines image features.

HighPack upgrades textures to 4K. With Sketch/Regular + Quad + explicitly supplied `quality_override<=100000`, it also requests a high-poly output around 16 times that count. Detail/Smooth change only texture resolution. [Gen-1/1.5](https://docs.hyper3d.ai/en/api-specification/rodin-gen1-1-5)

## Gen-2

`tier=Gen-2`; default mesh `Quad`. `quality_override`: integer 500–1000000, Quad maximum 200000. Raw quality targets: 500000/150000/20000/2000; Quad: 50000/18000/8000/4000.

Additional fields: `soft`, `quad_normal`, `hd_texture` booleans (default false); `detail_level` integer 1–3; `is_symmetric=symmetric|balanced|asymmetric|unknown` (default `unknown`). `hd_texture` enhances detail; HighPack selects 4K output and does not add high-poly geometry. Legacy `condition_mode`, `mesh_simplify`, `mesh_smooth` are absent from this family's schema. [Gen-2](https://docs.hyper3d.ai/en/api-specification/rodin-gen2)

## Gen-2.5

`tier=Gen-2.5-Extreme-Low|Gen-2.5-Low|Gen-2.5-Medium|Gen-2.5-High|Gen-2.5-Extreme-High`. Default mesh `Raw`. `quality_override`: 500–2000000; High/Extreme-High permit 2000000, others 1000000; Quad maximum 200000. Raw presets: 1000000/500000/60000/20000; Quad: 50000/18000/8000/4000.

Includes Gen-2's additional fields plus:

| Field | Values / constraints |
| --- | --- |
| `texture_mode` | `legacy`, `extreme-low`, `low`, `medium`, `high`, `extreme-high` |
| `image_label` | array: `F`,`FL`,`FR`,`L`,`R`,`B`,`BL`,`BR`,`U`,`D`,`?`; count ≤ images |
| `uhd_texture`, `is_micro`, `texture_delight` | boolean, default false |
| `geometry_instruct_mode` | `faithful`, `creative` (default) |

Explicit creative mode requires Medium or above; faithful is experimental. Micro detail requires Extreme-High. Texture defaults track tier: extreme-low/low/medium/high/high. Standard texture modes produce 2K, UHD 4K, HighPack 4K, both 8K; extreme-high mode produces 6K or 12K with HighPack. Fast mode requires non-Extreme-High tier, Raw, GLB/FBX/USDZ, and `quality_override<=20000`; it ignores preview renders. [Gen-2.5](https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5)

## Rodin Agentic

`POST /rodin_agentic`: required `images`, one to five, each ≤25 MiB; optional `prompt` ≤1024 characters; `tier=basic|standard|pro` (default standard); `export_type=glb|usdz|fbx|stl` (default glb); optional `route=high-poly|n-gons`. Blank prompt derives guidance from images. There is no OBJ export option here.

Response: `uuid`, `producer=high-poly|n-gons`, `job:{uuids,subscription_key}`. Poll with `job.subscription_key`, download with `uuid`. Agentic is beta and selects the generation route automatically when `route` is omitted. [Rodin Agentic](https://docs.hyper3d.ai/en/api-specification/rodin-agentic)

## PolyGen Low-poly

`POST /polygen` creates a low-poly task from exactly one of `asset_id` or
`model`, from one to five `images`, or from a non-blank `prompt`. `asset_id` and
`model` are mutually exclusive. Uploaded models support OBJ, GLB, STL, FBX,
USD, USDA, USDZ and USDC. Reference images support PNG, JPEG and WebP.

| Field | Values / limits |
| --- | --- |
| `transfer_texture` | boolean; applies to uploaded `model`, default true |
| `image_label` | array matched to uploaded images, using the standard direction labels |
| `face_count` | integer 200–10000 |
| `mesh_mode` | `Quad`, `Raw`, `NGon`; default `Quad` |
| `geometry_file_format` | `obj` (default), `glb`, `usdz`, `fbx`, `stl` |
| `material` | `None` (default), `PBR`, `Shaded`, `Hybrid`, `All` |
| `resolution` | `Basic` (default), `High` |
| `texture_mode` | `legacy`, `extreme-low`, `low`, `medium`, `high`, `extreme-high` |
| `uhd_texture` | boolean; sharpens generated texture detail |

For an uploaded model, PolyGen transfers its original textures and ignores
`prompt`, `material`, `texture_mode` and `uhd_texture`; `resolution` controls
the transferred texture export. For an asset, images or text input,
`material=None` produces geometry only. Each task costs 0.5 credits and uses
the standard status and download lifecycle. [Low-poly](https://docs.hyper3d.ai/en/api-specification/polygen)

## Texture generation

`POST /rodin_texture_only` requires one `model` and one to five repeated
`images` parts. Each image and the model must be smaller than 100 MiB. Images
support JPEG, PNG, WebP, TIFF, GIF, AVIF, HEIC, HEIF, BMP and JPEG 2000. Models
support OBJ, STL, glTF/GLB, FBX and USDZ.

| Field | Values / limits |
| --- | --- |
| `prompt` | optional string |
| `escore` | number 0–10; default 3.5 |
| `reference_scale` | number 0.5–1; default 1 |
| `hd_texture`, `uhd_texture`, `texture_delight` | boolean; default false |
| `texture_mode` | `legacy`,`extreme-low`,`low`,`medium`,`high` (default),`extreme-high` |
| `seed` | integer 0–65535 |
| `geometry_file_format` | `glb` (default),`usdz`,`fbx`,`obj`,`stl` |
| `material` | `PBR` (default),`Shaded`,`All`,`Hybrid` |
| `resolution` | `Basic` (default),`High` |
| `image_label` | array matched to the uploaded images, using the standard direction labels |

Basic/High means 2K/4K normally, 6K/12K in extreme-high mode. The schema includes Hybrid despite prose omitting it. [Generate Texture](https://docs.hyper3d.ai/en/api-specification/generate-texture)

## Bang

`POST /bang` requires exactly one `asset_id` (completed Rodin task UUID) or `model` file. Supported models: OBJ, GLB, STL, FBX, USD, USDA, USDZ, USDC. In asset mode omit `model`, `image`, `prompt`. In model mode, `image` is required unless `material=None`; nonempty `instruction` also requires an image. No upload size limit is stated.

| Field | Values / limits |
| --- | --- |
| `prompt`, `instruction` | optional strings; prompt custom-model only |
| `strength` | integer 1–12; default 5 |
| `mesh_mode` | `Raw` (default),`Quad` |
| `quality_override` | integer 500–2000000; total faces across parts; Quad worker caps 50000 |
| `escore` | number 0–10; default 3.5 |
| `reference_scale` | number 0–1; default 0.5 |
| `seed` | integer 0–65535 |
| `geometry_file_format` | `glb` (default),`usdz`,`fbx`,`obj`,`stl` |
| `material` | `PBR` (default),`Shaded`,`All`,`Hybrid`,`None` |
| `resolution` | `Basic` (default),`High` |

`instruction` enables directed splitting. Without an override, target faces are Quad 18000 / Raw 150000. Raw is simplified only above target. [Bang](https://docs.hyper3d.ai/en/api-specification/bang)

## Clean Topology (website)

On 2026-11-06, the [Rodin workspace](https://hyper3d.ai/workspace/rodin)'s
[public frontend bundle](https://hyper3d.ai/static/js/main.4162abdf.js) labels a
separate geometry operation **Clean Topology**, with `Fast` and `Legacy`
versions. Availability depends on the asset and account. This is frontend
evidence, not a supported public API contract or a completed generation test.

The provider now publishes a separate [Low-poly API](https://docs.hyper3d.ai/en/api-specification/polygen)
at `/api/v2/polygen`. Its documented contract does not name or version the
website's Clean Topology operation. Do not infer that `PolyGen` selects the
website `Fast` or `Legacy` mode.

`mesh_mode=Quad` selects a documented face type in Rodin, Bang or PolyGen; it
does not select Clean Topology or its version. Bang splits an asset and PolyGen
creates a low-poly result, so neither operation is an equivalent cleanup
operation. No Clean Topology tool, pricing, output contract or API acceptance
is claimed by this bundle. Follow the [website workflow](WORKFLOWS.md#clean-topology-website)
for an explicit website request. API integration requires a published provider
contract.

## Balance and errors

`GET /check_balance`: optional `usage_page>=1`; response `balance:number` and, when requested, up to 20 newest-first `usage:[{time,item,amount,task_uuid}]`. Balance is a point-in-time reading, not a reservation. [Check Balance](https://docs.hyper3d.ai/en/api-specification/check-balance)

Submission error codes include `INVALID_REQUEST`, `API_NO_ACTIVE_SUBSCRIPTION`, `API_SUBSCRIPTION_PLAN_TOO_LOW`, `API_PARALLELISM_LIMIT_REACHED`, `API_INSUFFICIENT_FUNDS`, `NO_ACTIVE_SUBSCRIPTION`, `INSUFFICIENT_FUNDS`, `API_OBJECT_NOT_FOUND_ON_IMAGE`, `IMAGE_CONTENT_VIOLATION`, `IMAGE_LABEL_LENGTH_TOO_LONG`, `NO_SUCH_TASK`, `ASSET_NOT_AVAILABLE`, `PERMISSION_DENIED`, `API_UNKNOWN` and the PolyGen-specific `UNKNOWN`. Status can return `NO_SUCH_TASK`; download can return `NO_SUCH_TASK` or `INVALID_REQUEST`. Text-only prompts can fail image moderation because they first generate an image.

HTTP 400: malformed input; 401: authentication; 429: throttling. Body errors must not trigger automatic resubmission. Upstream recommends backoff for 429/5xx; paid submissions need duplicate-charge caution when the outcome is ambiguous. Limits vary by endpoint/account, so do not hardcode a global rate. [Errors](https://docs.hyper3d.ai/en/api-specification/errors)

The integration retains HTTP status, a safe provider code, and up to 512
characters of sanitized JSON validation details. Credentials, Authorization
text and HTTP URLs are redacted. Malformed or oversized error bodies are not
returned. Read these details to correct a rejected request; a transport failure
still has an unknown submission outcome and must not trigger an automatic retry.

## Billing, retention, and documentation gaps

Endpoint documentation currently lists Gen-1/1.5 and Gen-2 at 0.5 credits; Gen-2.5 at 0.5 plus 0.5 for Extreme-High and 2 for extreme-high textures; Agentic basic/standard/pro at 0.5/1/2; PolyGen at 0.5; Bang at 0.5; texture generation at 0.5, or 2 for extreme-high. Current marketing still mentions a HighPack surcharge while generation pages say unlisted options add no charge. Do not promise estimates as final cost; expose returned `consumed` and check [current API pricing](https://hyper3d.ai/features/api) and [pricing plans](https://hyper3d.ai/pricing) before paid work.

API inputs/outputs remain in active systems for seven days. Download promptly. The API policy says they are not used for training or published to public assets, subject to the stated operational/legal exceptions. [Data Retention Policy](https://docs.hyper3d.ai/en/legal/data-retention-policy)

The official docs demonstrate repeated binary `images` parts and a JSON
bounding-box array without defining every multipart array convention. Live
acceptance on 2026-10-23 confirmed JSON text for nonempty `image_label` and
`bbox_condition` arrays and lowercase boolean text. An explicit empty `addons`
array form part caused HTTP 400 without a charge; omitting that part allowed
the otherwise identical request. The integration therefore omits empty list
fields. For nonempty `addons`, JSON array text was also rejected; the runtime
uses comma-separated literal text, matching the
[provider SDK](https://github.com/DeemosTech/rodin3d-skills/blob/46f311c768c0d12c6b63078e562110f958d3bf66/skills/rodin3d-skill/scripts/api_client.py#L97-L98).
The 2026-10-24 Sketch request with `addons=["HighPack"]` encoded as `HighPack`
was accepted, completed and downloaded. Other supported nonempty arrays retain
JSON encoding; public tool parameters remain arrays.

On 2026-10-23, five paid tasks exercised Gen-2.5 Low text and image generation, Agentic basic,
Bang asset mode, and texture generation, with completed downloads at a total
cost of 2.5 credits. See the
[dated acceptance report](https://github.com/dcc-mcp/dcc-ai-hyper3d/blob/main/docs/live-acceptance-2026-10-23.md).
The [2026-10-24 expanded report](https://github.com/dcc-mcp/dcc-ai-hyper3d/blob/main/docs/live-acceptance-2026-10-24.md)
records 21 further paid cases through the direct runtime harness for 14.5
credits. Its nine Rodin tiers plus the earlier Gen-2.5-Low examples cover all
ten documented tiers. The
[character addendum](https://github.com/dcc-mcp/dcc-ai-hyper3d/blob/main/docs/live-acceptance-2026-10-24-heroes.md)
adds two paid generations through actual MCP HTTP calls, making 23 cases and
15.5 credits in the expanded round. The earlier five-case cost is separate.

Accepted parameters do not establish every requested effect. Measured outputs
include HighPack textures below the documented resolution and face counts that
differ from requested targets; a triangulated export cannot prove quad topology.
The dated reports separate acceptance, completion, downloads, artifact checks
and native import. Combinations, reproducibility, rejection/error paths and
cross-DCC material fidelity remain incompletely exercised.

## Integration limits

These are local safeguards, not claims about provider limits: submissions
buffer at most 512 MiB of combined uploaded file content; Agentic additionally
caps each image at the documented 25 MiB. API responses are capped at 2 MiB.
Downloads allow 512 MiB per file, 2 GiB total, and a 600-second workflow
deadline. The file system must support hard links for atomic publication
without overwriting existing files. Archives are saved without extraction.
Input files must remain unchanged during submission. An OBJ/glTF may depend on
sidecars; the public texture API accepts one model part and documents no
multi-file sidecar upload protocol, so prefer a self-contained model.
