# Expanded live acceptance: 2026-10-24

Skill candidate: **0.1.2**. API and download results are final; native showcase acceptance is pending. This run explicitly submitted **21 paid cases**: **21 accepted, 21 all-jobs Done, 21 downloaded**. All **60 files (370,853,143 bytes)** passed the recorded container, archive, image and hash checks. See the [sanitized artifact receipt](live-acceptance-2026-10-24.json).

The additional experiment cost was **14.5 credits**, within a **15-credit reservation and cap**. Two final read-only checkpoints agreed. This delta excludes the separate [2026-10-23 run](live-acceptance-2026-10-23.md). Agentic responses did not report per-task consumed credits, so the aggregate delta is the cost authority here.

All paid submissions below used the skill's **direct Python runtime acceptance harness**. Separate live MCP HTTP `tools/call` checks passed for `get_balance`, `get_download_links`, `get_task_status` and `download_assets`. Paid submission through MCP was not exercised in this matrix. Eight MCP tools were discovered and source-contract checked; that evidence is distinct from live wire calls.

## Final case matrix

Accepted, provider completion, download, container validation and native import are separate gates. Native import for these expanded cases is not claimed in this API report.

| Case | Submitted route / tier or mode | Input | Requested format | Accepted | Provider | Downloaded outputs | Native import |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Rodin / Sketch | text | GLB | Yes | All Done | 1 GLB, 1 WEBP | Not run here |
| R2 | Rodin / Regular | 2 images | STL | Yes | All Done | 1 STL, 1 WEBP | Not run here |
| R3 | Rodin / Detail | 2 images | USDZ | Yes | All Done | 1 USDZ, 1 WEBP | Not run here |
| R4 | Rodin / Smooth | text | FBX | Yes | All Done | 3 FBX, 1 JPG, 6 PNG, 1 WEBP | Not run here |
| R5 | Rodin / Gen-2 | 1 image | GLB | Yes | All Done | 3 GLB, 1 WEBP | Not run here |
| R6 | Rodin / Gen-2.5-Extreme-Low | 2 images | GLB | Yes | All Done | 1 GLB | Not run here |
| R7 | Rodin / Gen-2.5-Medium | 1 image | GLB | Yes | All Done | 1 GLB | Not run here |
| R8 | Rodin / Gen-2.5-High | 1 image | GLB | Yes | All Done | 3 GLB, 1 JPG, 1 WEBP | Not run here |
| R9 | Rodin / Gen-2.5-Extreme-High | 1 image | GLB | Yes | All Done | 2 GLB, 1 WEBP | Not run here |
| A1 | Agentic / standard | 2 images | USDZ | Yes | All Done | 1 USDZ | Not run here |
| A2 | Agentic / pro | 1 image | GLB | Yes | All Done | 1 GLB | Not run here |
| A3 | Agentic / basic | 1 image | STL | Yes | All Done | 1 STL | Not run here |
| B1 | Bang / Raw | model upload | GLB | Yes | All Done | 1 GLB | Not run here |
| B2 | Bang / Quad | model + 1 image | GLB | Yes | All Done | 1 GLB | Not run here |
| T1 | Texture / legacy | model + 1 image | OBJ | Yes | All Done | 1 OBJ, 6 PNG | Not run here |
| T2 | Texture / low | model + 1 image | FBX | Yes | All Done | 4 FBX, 6 PNG | Not run here |
| T3 | Texture / high | model + 1 image | USDZ | Yes | All Done | 1 USDZ | Not run here |
| T4 | Texture / extreme-high | model + 1 image | GLB | Yes | All Done | 1 GLB | Not run here |
| O1 | Agentic / basic | 1 image | FBX | Yes | All Done | 1 FBX | Not run here |
| O2 | Texture / extreme-low | model + 1 image | STL | Yes | All Done | 1 PNG, 1 STL | Not run here |
| O3 | Texture / medium | model + 1 image | GLB | Yes | All Done | 2 GLB | Not run here |

The actual request receipts govern this table. In particular, T1 requested OBJ, T2 FBX, T3 USDZ and O2 STL; the earlier plan used different placeholders. Nine new Rodin tiers completed here. Together with the prior Gen-2.5-Low examples, all ten documented Rodin tiers have at least one accepted, completed and downloaded example. This is not an exhaustive option-combination or semantic-fidelity claim.

## Parameters actually submitted

The following fields come from the accepted requests. Prompt and instruction contents are omitted; B2 included both, while R1, R4, A2 and T1 included a text prompt. Format and tier/mode appear above. Array and boolean values below are public API values, not generated identities.

| Case | Additional submitted parameters |
| --- | --- |
| R1 | `mesh_mode="Quad"; quality_override=1000; material="PBR"; addons=["HighPack"]; seed=41` |
| R2 | `mesh_mode="Raw"; quality="extra-low"; material="None"; condition_mode="concat"; mesh_simplify=true` |
| R3 | `mesh_mode="Quad"; quality="low"; material="Shaded"; condition_mode="fuse"; mesh_smooth=true` |
| R4 | `mesh_mode="Quad"; quality="high"; material="All"; preview_render=true; seed=43` |
| R5 | `mesh_mode="Quad"; quality="medium"; material="Hybrid"; quad_normal=true; hd_texture=true; soft=true; detail_level=2; is_symmetric="symmetric"; seed=17` |
| R6 | `mesh_mode="Raw"; quality_override=5000; material="PBR"; texture_mode="extreme-low"; image_label=["F","R"]; bbox_condition=[1,2,1]; use_original_alpha=true; is_symmetric="balanced"; seed=65535` |
| R7 | `mesh_mode="Raw"; quality_override=5000; material="PBR"; texture_mode="medium"; geometry_instruct_mode="creative"; texture_delight=true; detail_level=1; seed=23` |
| R8 | `mesh_mode="Quad"; quality_override=8000; material="Hybrid"; texture_mode="high"; uhd_texture=true; preview_render=true; is_symmetric="asymmetric"; seed=47` |
| R9 | `mesh_mode="Raw"; quality_override=5000; material="PBR"; texture_mode="high"; is_micro=true; TAPose=true; geometry_instruct_mode="faithful"; seed=53` |
| A1 | `Provider defaults beyond the fields above` |
| A2 | `Provider defaults beyond the fields above` |
| A3 | `Provider defaults beyond the fields above` |
| B1 | `mesh_mode="Raw"; quality_override=5000; material="None"; strength=1; seed=0` |
| B2 | `mesh_mode="Quad"; quality_override=5000; material="PBR"; resolution="High"; strength=12; reference_scale=1; escore=10; seed=31` |
| T1 | `resolution="High"; material="All"; hd_texture=true; texture_delight=true; reference_scale=0.5; escore=0; seed=0` |
| T2 | `resolution="Basic"; material="Hybrid"; reference_scale=1; escore=5; seed=59` |
| T3 | `resolution="High"; material="PBR"; reference_scale=1; hd_texture=true; seed=61` |
| T4 | `resolution="High"; material="PBR"; reference_scale=1; seed=67` |
| O1 | `Provider defaults beyond the fields above` |
| O2 | `resolution="Basic"; material="Shaded"` |
| O3 | `resolution="Basic"; material="All"` |

This samples Raw/Quad; named quality and explicit overrides; material None/Shaded/PBR/All/Hybrid; two-image concat/fuse; labels and bounding-box arrays; symmetry values; creative/faithful geometry modes; alpha, micro, T-pose, preview, HD/UHD and texture controls. Agentic basic/standard/pro and GLB/USDZ/STL/FBX exports completed. Bang covered model upload alone and model plus image, prompt and instruction at strength 1/12. Texture generation completed all six documented texture modes across OBJ/FBX/USDZ/STL/GLB outputs. Combined options establish request acceptance, not isolated causal effects.

## Output measurements and limits

- **R1 Sketch HighPack:** one delivered high-poly geometry variant contains **559,968 triangles** and three **1,024 × 1,024** embedded images. The accepted request asked for Quad and `quality_override=1000`; this result does not prove that budget or quad topology. It does not support a 4K HighPack texture claim. The submission reported **0.5 credits** consumed.
- **R5/R8 Quad:** Gen-2 delivered **35,198 triangles**; Gen-2.5-High with `quality_override=8000` delivered **16,528 triangles**. glTF triangle counts do not establish native quad topology. R8 includes a 4,096 × 4,096 base-color image with other channels at 2,048 × 2,048.
- **R6/R7/R9 Raw:** the final GLBs contain **4,788 / 4,912 / 5,000 triangles**, respectively, with three 2,048 × 2,048 images each. R9 also returned a separate raw variant with **5,124,470 triangles and no images**; variant selection matters.
- **B2:** the Quad request delivered **9,062 triangles**, two meshes and three 4,096 × 4,096 images. **A2 pro** delivered **2,488 triangles**, 17 meshes, four materials and no embedded images.
- **T4 extreme-high:** the **121,254,336-byte** GLB preserves the source's **4,788 triangles** and embeds images at **4,096², 12,288² and 4,096²**. One 12K channel was verified; 12K across all maps was not.

These measurements describe the downloaded containers. Native material appearance, topology, axes, scale, prompt fidelity, symmetry, alpha preservation, T-pose, reproducibility and paired on/off effects require separate checks. A successful parameter submission alone proves none of those effects.

## Encoding and recovery

The original nonempty `addons` JSON-array form part received a definitive HTTP 400. The corrected R1 submission encoded the public array as literal comma-separated form text (`HighPack`), matching the [official SDK implementation](https://github.com/DeemosTech/rodin3d-skills/blob/46f311c768c0d12c6b63078e562110f958d3bf66/skills/rodin3d-skill/scripts/api_client.py#L100-L101), and completed. It was an explicit corrected submission, with no automatic paid retry. The field-specific fix preserves the public array schema, JSON encoding for `image_label` / `bbox_condition`, lowercase boolean encoding and omission of empty arrays.

R7's initial download failed on the network; resuming the same completed task succeeded without another paid submission. A selected-filename download also passed. Live status receipts observed Waiting, Generating and Done; usage pagination page 2 returned nine entries. An initial unsupported links harness operation made no provider call; the corrected explicit MCP HTTP links probe passed.

## Source checks and remaining gates

The multipart fix passed **32 runtime tests**. The full local suite discovered **48 tests: 46 passed, two POSIX-only permission tests skipped on Windows**. Lint checked **eight execution contracts with zero errors and zero warnings**; the Python 3.7 syntax contract passed. These source checks do not establish the live MCP paid-submission path.

The following remain outside this API receipt: native import/render and playable showcase acceptance for the new cases; saved-scene reopening; exhaustive per-endpoint file-format and image-encoding matrices; five-image limits; all option values and combinations; paired semantic effects and seed reproducibility; 6K extreme-high Basic textures; live account-dependent failures, expired-link/redirect variations and ambiguous paid timeouts. Consumer-site or enterprise-only features without a documented public endpoint are also excluded. Exact-head CI, catalog publication and clean installed-client acceptance are separate release gates.

API scope follows the official [legacy Rodin](https://docs.hyper3d.ai/en/api-specification/rodin-gen1-1-5), [Gen-2](https://docs.hyper3d.ai/en/api-specification/rodin-gen2), [Gen-2.5](https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5), [Agentic](https://docs.hyper3d.ai/en/api-specification/rodin-agentic), [Bang](https://docs.hyper3d.ai/en/api-specification/bang), [texture](https://docs.hyper3d.ai/en/api-specification/generate-texture), [status](https://docs.hyper3d.ai/en/api-specification/check-status), [download](https://docs.hyper3d.ai/en/api-specification/download-results) and [balance](https://docs.hyper3d.ai/en/api-specification/check-balance) specifications.
