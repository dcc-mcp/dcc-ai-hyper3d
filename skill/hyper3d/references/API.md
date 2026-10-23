# Hyper3D public API contract

Verified against the current English official documentation on 2026-10-23. This is a compact integration reference; the linked upstream schemas remain authoritative. Public API coverage means the seven endpoints below, including all Rodin model families. The public reference does not document separate upload, cancel, task-list, delete, remesh, mesh-edit, rigging, model-search, or asset-library endpoints. Uploads accompany multipart submissions; topology and target-face controls belong to generation or Bang.

## Transport and lifecycle

Base URL: `https://api.hyper3d.com/api/v2`. Authenticate API calls with `Authorization: Bearer <RODIN_API_KEY>`; load the key from an environment variable or secret store. Never forward that header to result-download hosts. [Introduction](https://docs.hyper3d.ai/en), [Quick Start](https://docs.hyper3d.ai/en/get-started/quick-start)

| Method | Path | Body | Operation |
| --- | --- | --- | --- |
| POST | `/rodin` | multipart | Gen-1/1.5, Gen-2, Gen-2.5 generation |
| POST | `/rodin_agentic` | multipart | Agent-selected generation; beta |
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

`POST /rodin_agentic`: required `images`, one to five, each ≤25 MiB; optional `prompt` ≤1024 characters; `tier=basic|standard|pro` (default standard); `export_type=glb|usdz|fbx|stl` (default glb). Blank prompt derives guidance from images. There is no OBJ export option here.

Response: `uuid`, `producer=high-poly|n-gons`, `job:{uuids,subscription_key}`. Poll with `job.subscription_key`, download with `uuid`. Agentic is beta and selects the generation route automatically. [Rodin Agentic](https://docs.hyper3d.ai/en/api-specification/rodin-agentic)

## Texture generation

`POST /rodin_texture_only` requires exactly one `image` and one `model` file. Images: JPEG, PNG, WebP, TIFF, GIF, AVIF, HEIC, HEIF, BMP, JPEG 2000. Models: OBJ, STL, glTF/GLB, FBX, USDZ. No upload size limit is stated.

| Field | Values / limits |
| --- | --- |
| `prompt` | optional string |
| `escore` | number 0–10; default 3.5 |
| `reference_scale` | number 0.5–1; default 1 |
| `hd_texture`, `texture_delight` | boolean; default false |
| `texture_mode` | `legacy`,`extreme-low`,`low`,`medium`,`high` (default),`extreme-high` |
| `seed` | integer 0–65535 |
| `geometry_file_format` | `glb` (default),`usdz`,`fbx`,`obj`,`stl` |
| `material` | `PBR` (default),`Shaded`,`All`,`Hybrid` |
| `resolution` | `Basic` (default),`High` |

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

## Balance and errors

`GET /check_balance`: optional `usage_page>=1`; response `balance:number` and, when requested, up to 20 newest-first `usage:[{time,item,amount,task_uuid}]`. Balance is a point-in-time reading, not a reservation. [Check Balance](https://docs.hyper3d.ai/en/api-specification/check-balance)

Submission error codes: `INVALID_REQUEST`, `API_NO_ACTIVE_SUBSCRIPTION`, `API_SUBSCRIPTION_PLAN_TOO_LOW`, `API_PARALLELISM_LIMIT_REACHED`, `API_INSUFFICIENT_FUNDS`, `API_OBJECT_NOT_FOUND_ON_IMAGE`, `IMAGE_CONTENT_VIOLATION`, `IMAGE_LABEL_LENGTH_TOO_LONG`, `NO_SUCH_TASK`, `ASSET_NOT_AVAILABLE`, `PERMISSION_DENIED`, `API_UNKNOWN`. Status can return `NO_SUCH_TASK`; download can return `NO_SUCH_TASK` or `INVALID_REQUEST`. Text-only prompts can fail image moderation because they first generate an image.

HTTP 400: malformed input; 401: authentication; 429: throttling. Body errors must not trigger automatic resubmission. Upstream recommends backoff for 429/5xx; paid submissions need duplicate-charge caution when the outcome is ambiguous. Limits vary by endpoint/account, so do not hardcode a global rate. [Errors](https://docs.hyper3d.ai/en/api-specification/errors)

## Billing, retention, and documentation gaps

Endpoint documentation currently lists Gen-1/1.5 and Gen-2 at 0.5 credits; Gen-2.5 at 0.5 plus 0.5 for Extreme-High and 2 for extreme-high textures; Agentic basic/standard/pro at 0.5/1/2; Bang at 0.5; texture generation at 0.5, or 2 for extreme-high. Current marketing still mentions a HighPack surcharge while generation pages say unlisted options add no charge. Do not promise estimates as final cost; expose returned `consumed` and check [current API pricing](https://hyper3d.ai/features/api) and [pricing plans](https://hyper3d.ai/pricing) before paid work.

API inputs/outputs remain in active systems for seven days. Download promptly. The API policy says they are not used for training or published to public assets, subject to the stated operational/legal exceptions. [Data Retention Policy](https://docs.hyper3d.ai/en/legal/data-retention-policy)

Current docs demonstrate repeated binary `images` parts and a JSON bounding-box array. They do not specify a complete multipart encoding convention for non-file arrays. Lowercase boolean text and JSON array text are an integration choice that still needs authenticated service validation. This research did not submit paid tasks or verify live server behavior.

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
