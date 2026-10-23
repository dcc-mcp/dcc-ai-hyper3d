# Live acceptance: 2026-10-23

Candidate skill version: **0.1.1**. Five explicit paid tasks completed across
all four submission routes, and all five result sets downloaded successfully.
The total experiment cost was **2.5 credits**. Provider identities, account
balances, credentials, signed URLs and generated media are excluded here.

## Provider and download results

| Case | Submitted route and input | Output | Provider and download |
| --- | --- | --- | --- |
| Text generation | Rodin Gen-2.5 Low, text | OBJ | Passed |
| Image generation | Rodin Gen-2.5 Low, reference image | FBX | Passed |
| Agentic | Agentic basic, reference image | GLB | Passed |
| Model processing | Bang, completed asset ID, Raw mesh | OBJ | Passed |
| Retexture | Texture generation, local OBJ and reference image | GLB | Passed |

The first text request was definitively rejected with HTTP 400 and no balance
change. Removing only the empty `addons: []` multipart part allowed acceptance.
The runtime now omits empty list fields. Nonempty `image_label` and
`bbox_condition` JSON arrays and lowercase boolean fields were accepted.
Nonempty `addons` remains an offline encoding check.

Downloads used fresh provider links and returned local file hashes and shared
asset descriptors. Each paid task was invoked explicitly; the harness did not
retry submissions automatically.

## Native imports

| Output | Maya 2027.2 | Blender 5.2.0 |
| --- | --- | --- |
| Text OBJ | Passed | Passed |
| Image FBX | Passed | Passed |
| Agentic GLB | Unsupported by installed importer; not run | Passed |
| Bang OBJ | Passed | Passed |
| Retextured GLB | Unsupported by installed importer; not run | Passed |

Maya used adapter 0.9.42 with core 0.20.46. Blender used adapter 0.2.4 with
core 0.20.41. These versions identify the native import hosts; they do not
change the skill's declared minimum runtime. A separate live MCP HTTP
`tools/call` balance check passed with core 0.20.44 and all eight skill tools
available.

Blender accepted the shared `AssetDescriptor` unchanged. Maya's importer
required its legacy `asset` mapping with `path` and `format`, selected from a
descriptor variant. The skill's shared return contract remains unchanged.
Eight native import calls completed: three in Maya and five in Blender.

## Geometry, materials and scale

- Text OBJ: both hosts reported 2,496 vertices and 5,000 triangles with UVs.
  No MTL or `usemtl` bindings were present, so downloaded textures did not bind
  automatically.
- Image FBX: both hosts reported 2,393 vertices and 4,786 triangles. Four
  2,048 × 2,048 textures were verified.
- Retextured GLB: Blender reported 6,785 vertices and 5,000 triangles, three
  embedded 2,048 × 2,048 PBR images and four connected material channels.
- Agentic GLB: Blender imported 80 meshes and a WORLD node, totalling 3,805
  vertices and 3,244 triangles. Its four PBR materials use factors without
  embedded images.
- Bang OBJ: Blender imported nine meshes totalling 2,508 vertices and 5,000
  triangles. Maya merged them into one mesh with the same geometry totals and
  2,958 UVs.
- Maya viewport geometry was observed. Texture-display input was refused before
  dispatch with `TargetOccluded`; full Maya PBR fidelity was not verified.
- Blender's native EEVEE render passed at 960 × 720 with 32 samples. The textured
  chest, metallic straps and padlock were fully visible, with no clipped edges
  or neighbouring objects. A Blender scene was saved; reopening was not tested.

For OBJ, source units and axes remain unknown; the Maya import used centimetres
as a caller assumption. The FBX importer applied its native unit conversion,
yielding approximately 190 cm in Maya and 1.9 Blender units. Check scene scale
before production use.

## Source checks and remaining coverage

`python -m unittest discover -s tests -v`: **47 tests**; the Windows run passed
45 and skipped two POSIX-only permission checks, which run in Linux CI.
`dcc-mcp-cli lint skill/hyper3d --warnings-as-errors --no-update-maintenance`:
**8 execution contracts checked, 0 errors, 0 warnings**. The acceptance harness
also passed a Python 3.7 syntax check.

This run did not cover every tier or provider option, nonempty HighPack addons,
Bang model-upload mode, Maya GLB import, or Maya rendered PBR fidelity. Remote
CI and catalog/publication acceptance are separate from these local results.
Use the [workflow guide](../skill/hyper3d/references/WORKFLOWS.md) to repeat a
bounded check while keeping private evidence outside version control.
