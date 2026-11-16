# Observed compatibility

Observed on Windows with Python 3.13.5 during the 2026-11-16 local execution. The installed official Python SDK is 1.30.0 and the observed handshake selected MCP 2025-11-25. Version 2026-07-28 on the current specification site has different lifecycle semantics. This package claims the protocol observed with its pinned SDK.

| Client/surface | Transport | Observed operations | Status |
|---|---|---|---|
| Official Python MCP SDK 1.30.0 | stdio and Streamable HTTP | Discovery, create/read/correct, evidence/session, export, preview/delete, restart and cross-transport continuity, rejected access | Executed in subprocess tests |
| MCP Inspector 2.15.0, Node 24.22.1 | stdio | tools/list and get_profile | Executed through independent TypeScript client |
| Claude Code 2.1.311 | stdio | Read empty profile, create shopping item at revision 1, prepare context returning oc-shopping | Executed in actual host |
| Codex CLI 0.167.2, GPT-6 Astra | stdio | Read the Claude-created profile, prepare context, correct familiarity with revision 1, observe revision 2 and fallback | Executed in actual host |
| VS Code/Copilot | stdio | Example configuration based on documentation; executable path requires platform adaptation | Configuration provided, host flow unobserved |
| ChatGPT remote custom MCP connection | Remote HTTPS or supported tunnel | Account/workspace permissions and appropriate remote authorization required | Not executed |
| Linux, standard GitHub runner | stdio/HTTP | Full source verification and package build | Executed in manual CI |
| macOS | stdio/HTTP | Source and dependency setup designed for supported Python | Runtime unobserved |

The two host tests used a synthetic database, isolated per-run configuration and the same authorized profile. They demonstrate continuity at the server and an observed host correction. They do not establish that every host prompt, operation or version behaves identically. Raw terminal diagnostics included a separate pre-existing Firebase connector startup warning in Codex. The Repertorio tool calls completed and the recorded profile state verified their effects.

Sanitized actual calls and returned values are in [Claude evidence](../evidence/host-claude.json) and [Codex evidence](../evidence/host-codex.json). Claude made three calls, then Codex made four in a new process against the same synthetic profile. Source package distributions omit these captured logs; use the source archive or regenerate the local checks. SDK protocol tests cover more operations than the host demonstration. Inspector evidence is limited to discovery and one read, not a full acceptance suite.

## Connection files

`examples/claude.mcp.json` and `examples/codex.config.toml` require absolute Python/database paths. `examples/vscode.mcp.json` also requires absolute Python/database paths. Use `.venv/bin/python` on Linux/macOS. Install the package in that interpreter first. stdio logs never share stdout with protocol frames. Returned tool data includes structured content and equivalent text for clients that render only text.

The server derives stdio identity from launch configuration. HTTP identity and scopes come from the validated bearer registry. A database profile can be shared between trusted clients with that identity. Export/import allows deliberate migration into another instance. Manual summaries are snapshots.

## ChatGPT surfaces

Official guidance checked on 2026-11-16 describes custom remote MCP connections through a public HTTPS endpoint or Secure MCP Tunnel, with availability governed by plan/workspace and admin permissions. The cited page describes Business and Enterprise/Edu workspace requirements. Confirm the current account-specific availability before configuring a remote connection. Local Codex MCP settings and ChatGPT's remote connections are separate product surfaces.

Repertorio's opaque development token and loopback address support local testing. A remote deployment would require a reviewed network boundary, HTTPS, an appropriate mature authorization provider, MCP resource-server metadata/token validation and the authentication flow accepted by the actual client. No remote endpoint or tunnel was created. Tools-only operation is supported by the documented model and does not require a custom UI.

## Official references

- https://code.claude.com/docs/en/mcp
- https://code.visualstudio.com/docs/agent-customization/mcp-servers
- https://learn.chatgpt.com/docs/extend/mcp
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
- https://modelcontextprotocol.io/docs/tools/inspector
- https://github.com/modelcontextprotocol/python-sdk


The public-release [Windows/Linux CI run](https://github.com/kayammaori2-afk/repertorio/actions/runs/43927397744) passed both jobs, including lockfile install, lint/types/tests, evaluation/pilot and package build. These are SDK/process checks; the two actual AI-host observations above remain Windows-specific. A fresh public GitHub clone also ran the demo and reproduced the eight deterministic evaluation files; see `evidence/publication/public-clone.json`.
