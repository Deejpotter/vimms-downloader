---
name: "Agent workflow"
description: "Repository-specific required steps for AI agents"
applyTo: "**/*"
---

- Read `README.md` before any change.
- Use #tool:mcp_context7_resolve-library-id and #tool:mcp_context7_get-library-docs to fetch authoritative library docs before implementing changes.
- Use #tool:activate_search_tools and #tool:mcp_my-mcp-server_search_documentation to find official docs and examples for missing information.
- Prefer updating existing files over creating new ones; only add files when necessary and explain why in the PR.
- NOTE: The canonical Python implementation has been moved to `archive/`. For migration work to TypeScript/Electron, prefer incremental module-by-module conversion and keep functional parity tests in `tests/`.
- Prefer Express (Node) when porting the `webapp.py` endpoints for the Desktop UI — use `ts-node`/`ts-node-esm` for local dev and `vitest` for unit tests of ported modules.
- Before starting work, update `.github/TODOs.md` (mark task as "In Progress") and post a short plan (1–6 steps) in the issue/PR; get confirmation for changes that affect defaults or deletion behavior.
- After completing work, update `.github/TODOs.md` (mark Completed) and keep only the last 10 completed tasks.
- For changes to algorithms (normalization, matching, indexing) add small, deterministic unit tests and run them locally with `pytest`.
- When referencing code or files in instructions, use `code formatting` and Markdown links (e.g., `download_vimms.py`, `clean_filenames.py`).
- Keep changes conservative for anything that affects downloads or deletion behavior — document any risk and provide a rollback plan.
