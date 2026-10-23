# Character acceptance addendum: 2026-10-24

Skill **0.1.2**, Core **0.20.46**. Two approved original ImageGen concepts were
submitted once each through actual MCP HTTP `tools/call create_rodin_task`,
then the public Rodin API. Both submissions were accepted, reached all-jobs
`Done`, and downloaded successfully. No paid submission was retried
automatically.

| Character | Input | Route | Accepted | Provider | Download | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| Courier | Original single-view concept | Gen-2.5-High | Yes | All Done | GLB, WEBP, JPG | 0.5 credits |
| Guardian | Original single-view concept | Gen-2.5-High | Yes | All Done | GLB, WEBP, JPG | 0.5 credits |

Both requests used `mesh_mode=Raw`, `quality_override=30000`, `material=PBR`,
`texture_mode=high`, `geometry_file_format=glb`, `TAPose=true`,
`is_symmetric=balanced`, `preview_render=true` and `use_original_alpha=false`.
The seeds were 313 and 317 respectively. These accepted combinations do not
isolate the effect of each parameter or establish multiview consistency.

## Cost and transport boundaries

The [expanded API experiment](live-acceptance-2026-10-24.md) remains a historical
21-case report: its paid submissions used the direct Python runtime harness,
and its actual MCP wire checks covered four read-only/download tools. These
two new paid MCP submissions add **1 credit**, producing **23 completed paid
cases for 15.5 credits**, matching the approved expanded cap and recorded usage
delta. The separate [2026-10-23 five-case run](live-acceptance-2026-10-23.md)
cost 2.5 credits and is excluded from that total.

The 21-case run covered nine Rodin tiers. With the earlier Gen-2.5-Low cases,
all ten documented tiers have accepted, completed and downloaded examples.
Eight implemented tools and seven public API endpoints do not establish every
Hyper3D website/plugin feature, parameter effect, format combination or error
path. See the [API contract and limits](../skill/hyper3d/references/API.md).

## Generated assets and authored derivatives

Each immutable provider GLB contains **30,000 triangles**, one mesh, one
material, UVs and three embedded **2048 × 2048** PBR images. Native Blender
5.2 inspection checked front, quarter and rear views. Neither provider output
contains a skin, skeleton or animation; `TAPose` did not supply a rig.

The initial game derivatives use **Blender-authored** rigs and in-place clips: 17
joints, including a nondeforming root and 16 weighted deform joints; `Idle`
2 seconds, `Walk` 1 second and `Dash` 0.25 seconds. Native bone-heat weights
from a temporary welded proxy were transferred by matching vertex positions.
Final GLB inspection found no unweighted vertices or invalid weights and
verified normalized weights, changing leg-joint channels, loop seams, unit
quaternions and zero root translation. UV values and the original embedded
image bytes/PBR channel bindings were preserved; coordinates were normalized
to a 1.65 m rest height facing −Z, with +Y up. Native static deformation views
passed review. This authorship is separate from Hyper3D generation.

Initial Godot **4.6.3** checks imported one skinned mesh and the expected skeleton and three
clips for each character. Instrumented runtime checks passed for advancing
Idle, changing joint poses, Walk movement, Dash selection, pause freeze, retry
reset and visibility restoration. A continuous scripted course also completed
with three relics and full health. The user approved two native near-view
renders and a five-second scripted Idle/Walk/Dash sample. These checks do not
establish controlled playability: **OS-input playtesting and Web acceptance
remain pending**. Further ARPG interaction work is a separate acceptance gate.
Native checks on these two GLBs do not
establish cross-DCC import acceptance for all 23 cases.

The concepts were approved original ImageGen inputs. MIT covers integration
code; the API supplies no generated-content license grant in its responses.
Uploaded/generated content rights require separate verification. This report
contains no credentials, account readings, task identifiers or temporary URLs.
