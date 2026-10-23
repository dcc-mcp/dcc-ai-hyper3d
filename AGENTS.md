# DCC-AI Hyper3D

Reusable, host-neutral DCC-MCP skill. Implementations live in
`skill/hyper3d/scripts`, declarations in `skill/hyper3d/tools.yaml`.

- Follow SOLID, existing core contracts, and Python 3.7-compatible syntax.
- Use `dcc_mcp_core.skills_helper` for supported helpers. Streaming and
  redirect-sensitive downloads use the standard library.
- Never retry a paid submission automatically, log credentials, or overwrite
  existing downloaded files. Keep every documented API option accessible.
- Host adapters own scene import; return the shared `AssetDescriptor` contract.
- Run `python -m unittest discover -s tests -v` and
  `dcc-mcp-cli lint skill/hyper3d --warnings-as-errors --no-update-maintenance`.
- Git identity: `loonghao <hal.long@outlook.com>`; concise English
  Conventional Commits.
- UI work must use project-owned `dcc-cua` and DCC-MCP `ui-control` routes.
  Before observation/input report `provider=dcc-cua`, runtime version, PID,
  and HWND. If unavailable, repair or report the blocker; no generic fallback.
