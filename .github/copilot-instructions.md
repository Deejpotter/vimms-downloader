# GitHub Copilot / AI Agent Instructions for vimms-downloader ✅

Purpose: Give an AI coding agent the essential, actionable knowledge to be immediately productive in this repository.

Quick summary

- Canonical downloader: `download_vimms.py` (workspace root) — fetches games from Vimm's Lair and writes progress to `download_progress.json`.
- Runner: `run_vimms.py` — orchestrates per-console runs, reads `vimms_config.json` (workspace root) and optionally per-folder `vimms_folder.json`.
- Utility scripts: `clean_filenames.py`, `fix_folder_names.py` (see examples below).

How to run (developer workflow) 🔧

- Install dependencies in a venv (see `README.md` / `README_VIMMS.md`):
  python -m venv .venv
  source .venv/Scripts/activate # on Windows Git Bash / WSL
  pip install -r requirements.txt

- Dry-run the runner (safe):
  python run_vimms.py --dry-run

- Run a single console folder (non-interactive):
  python run_vimms.py --folder "DS" --no-prompt --extract-files

- Run the canonical downloader directly (for a folder):
  python download_vimms.py --folder "C:/path/to/DS" --no-prompt

Key files & patterns (what to look at) 🔍

- `download_vimms.py` — main logic: sections listing, `VimmsDownloader` class, detection and download flow, progress handling, logging
  - progress file saved as `<folder>/download_progress.json` (tracks 'completed', 'failed', 'last_section')
  - per-download logging file: `ROMs/vimms_downloader.log`
  - failed HTTP bodies saved under `ROMs/failed_responses/`
- `run_vimms.py` — orchestration: resolves targets, loads `vimms_config.json`, supports legacy whitelist/blacklist, supports `--report` to write `progress_report.json`
- `vimms_config.json` (workspace root) preferred for global folder mapping; per-folder fallback: `vimms_folder.json` in console folder
- `clean_filenames.py` — canonical cleaning rules used by the downloader (`_clean_filename`) — prefer keeping logic in sync
- `fix_folder_names.py` — utility to infer console by extensions and propose safe renames

Project-specific conventions & behaviors ⚠️

- Preferred ROM folder: downloader creates/uses a `ROMs` subfolder inside each console folder; inspect there for progress and logs.
- Local-detection heuristic (avoid re-downloads): normalization → substring containment (A in B) → fuzzy ratio (threshold 0.75 by default). See `_normalize_for_match`, `find_all_matching_files`, and `is_game_present`.
- Indexing: `pre_scan` builds an in-memory index limited by `limits.index_max_files` (default 20000) to speed detection.
- Default extraction policy: DS extracts by default; other systems may keep archives. Extraction controlled by `extract_files` arg/config and top-level `defaults.extract_files`.
- Duplicate handling: `--delete-duplicates` prompts per-title; `--yes-delete` auto-confirms and moves duplicates to `scripts/deleted_duplicates/<timestamp>/`.
- Rate-limiting: script respects server rate limits and will back off on 429 responses—see retry/backoff code.

Integration & dependencies 🔗

- HTTP fetching: `requests`, HTML parsing: `beautifulsoup4` (`bs4`).
- Optional: `py7zr` for `.7z` extraction (missing => extraction skipped with a user-visible message).
- Tests/CI: None present — prefer small unit tests around `_clean_filename`, normalization, and fuzzy-match heuristics.

Debugging tips 🐞

- For download issues: check `ROMs/vimms_downloader.log` and `ROMs/failed_responses/` for saved responses.
- Reproduce network behavior: use `--section-priority` to run a small section, or `--no-detect-existing` to force downloads of sample items.
- To debug filename normalization, use `clean_filenames.py` in preview mode (`dry-run`) before applying renames.

Examples to reference in code (use these snippets as test cases)

- Filename cleaning: input: `005 4426__MY_GAME_(EU).nds` → `MY GAME.nds` (see `_clean_filename` / `clean_filename`)
- Local detection threshold: fuzzy match ratio >= 0.75 (see `limits.match_threshold` default)
- Config example shown in `README_VIMMS.md` (`vimms_config.json` mapping style)

When editing code ✏️

- Keep CLI argument behavior and config precedence intact: CLI flags > per-folder `vimms_folder.json` > top-level `vimms_config.json` defaults.
- Preserve progress file format (list of completed ids + failed entries with metadata) to keep resume capability stable.
- If changing filename cleaning logic, update both `clean_filenames.py` and the in-class `_clean_filename` implementation to avoid divergence.
- Add unit tests for any algorithmic change (normalization, fuzzy thresholds, index-building). Keep tests small and deterministic.

Help & iteration 💬

- If any section here is unclear, add a specific question as an issue and request clarification. Prefer modifying this file with short edits rather than long rewrites.

---

Agent workflow & repository rules (must-follow)

These points describe the exact workflow and constraints an AI agent should follow when making changes in this repository. Follow them in order for each task.

#codebase

1. **Read the README first** to understand the correct workflow and expected behavior before proposing or making changes.
2. **Use Context7 / library docs** to find canonical documentation for libraries or APIs before implementing changes. Use the `mcp_context7_resolve-library-id` and `mcp_context7_get-library-docs` tools when available. (#tool:mcp_context7_resolve-library-id, #tool:mcp_context7_get-library-docs)
3. **Search web resources** for missing documentation or best-practices using the provided search tools (Google/DuckDuckGo via my-mcp-server). Use `activate_search_tools` and `mcp_my-mcp-server_search_documentation` for these queries. (#tool:activate_search_tools, #tool:mcp_my-mcp-server_search_documentation)
4. **Prefer updates to existing files**: keep the current code and comments where possible. When changing behavior, update the original source rather than creating new files and copying code over.
5. **Prioritize editing over adding files** — update `*.py`, `README.md`, and existing docs first unless a new file is required for clarity or CI/test harnesses.
6. **Maintain the TODOs list**: Always update `.github/TODOs.md` before starting work (marking the task as In Progress) and again after completion (mark Completed and keep only the most recent 10 completed items). Do not add stale completed tasks.
7. **Plan before coding**: First, outline a short plan of actions (1–6 steps). Share the plan and obtain quick confirmation if a change affects defaults or deletion behavior. Follow the plan; if you diverge, update the plan and note why.

Practical tips for instruction files (VS Code / Copilot Chat)

- Use a single `.github/copilot-instructions.md` for workspace-wide rules and add targeted `*.instructions.md` files under `.github/instructions/` for task-specific guidance (use `applyTo` globs to scope them).
- Keep instructions short and explicit (single statements). Prefer multiple files when instructions differ by file type or folder.
- Include tool references using the `#tool:<tool-name>` syntax to indicate which tools to call for searches or docs (e.g., `#tool:mcp_my-mcp-server_search_documentation`).
- Use YAML frontmatter in `*.instructions.md` files for `name`, `description`, and `applyTo` (example below):

```markdown
---
name: "Agent workflow"
description: "Repository-specific agent rules and search/tool usage"
applyTo: "**/*"
---

- Read the README before any change.
- Update `.github/TODOs.md` before and after work.
- Use #tool:mcp_context7_get-library-docs and #tool:mcp_my-mcp-server_search_documentation for documentation lookups.
```

Debugging & tool usage

- Prefer `#tool:mcp_context7_resolve-library-id` + `#tool:mcp_context7_get-library-docs` when you need authoritative library docs.
- Use `#tool:activate_search_tools` to run general web searches (Google and DuckDuckGo) for best-practice guidance.
- When referencing files or symbols in instructions, use Markdown links and `code formatting` (e.g., `download_vimms.py`, `VimmsDownloader`).

Notes & cautions

- Custom instruction files are **not** applied to inline editor suggestions, only to chat sessions — keep that in mind when writing guidance.
- If an instruction file is not applied, verify `applyTo` globs, config settings, and the Chat Debug view as documented by VS Code.

---

Small housekeeping note: before making changes, update `.github/TODOs.md` (added alongside these instructions) and mark tasks as Todo / In Progress / Completed. Keep only the last 10 completed tasks for history.

Thank you — stay conservative when changing defaults that affect downloads or deletion behavior. ⚠️
