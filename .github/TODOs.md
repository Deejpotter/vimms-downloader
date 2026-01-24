# TODOs for vimms-downloader

This file tracks the work planned and completed for this repository. Keep the most recent 10 completed items.

- [x] (Completed) Scaffold Electron + Vite + React + TypeScript app and get dev server running (M1) — 2026-01-24
- [x] (Completed) Extract parsing & fetch helpers into `downloader_lib` and remove duplicate `download_vimms/` package — 2026-01-24
- [x] (Completed) Add `.github/copilot-instructions.md` to document repo-specific guidance for AI agents — 2026-01-24
- [x] (Completed) Add unit tests for `_clean_filename` and `_normalize_for_match` (small cases, edge cases) — 2026-01-24
- [x] (Completed) Fix README reference: `requirements_vimms.txt` vs `requirements.txt` (updated docs to reference Python archive & Node instructions)
- [~] (In Progress) Add integration tests for `VimmsDownloader.get_game_list_from_section` using recorded HTML fixtures — unit tests added, still need full integration tests that exercise real network/pagination

- NOTE: Per owner preference, do NOT add CI workflows. Keep tests local and lightweight; run with `pytest` locally. If you want CI later, open a new TODO.

- [ ] (Todo) Improve extraction path when `py7zr` is missing (document and optionally auto-install or warn clearly)
- [x] (Completed) Add small test harness for `run_vimms.py --dry-run` behavior — 2026-01-24
- [x] (Completed) Allow `src_root` to be read from `vimms_config.json` and ignore obvious non-console folders when scanning workspace root — 2026-01-24

---

Feature: Popularity categorization & Web UI (new)

- [x] (Completed) Implement popularity scraper & CLI to categorize downloads into star buckets — 2026-01-24
  - substeps:
    - added `src/metadata.py` with `get_game_popularity` extraction and caching
    - added CLI `scripts/categorize_by_popularity.py` (dry-run and apply modes)
    - added tests for HTML scraping and mapping (`tests/test_popularity_scrape.py`)
    - added caching support (`ROMs/metadata_cache.json` in ROMs folders)
    - integration into post-download implemented (moved files to `ROMs/stars/<n>/`)
- [~] (In Progress) Implement a local Web UI to browse games and queue downloads — started 2026-01-24
  - substeps:
    - small internal API exposing sections, games, presence, and queue actions (scaffolded in `archive/src/webapp.py`) ✅
    - Express API (`src/server/app.ts`) implemented with queue persistence and basic endpoints ✅
    - FastAPI server `src/webapp.py` and templates/static assets (basic template added `src/webui_templates/index.html`) ✅ (kept as canonical Python reference)
    - background worker for queued downloads (simple in-memory worker added) ✅
    - tests for endpoints and queue behavior (TS tests added; Python TestClient tests remain for archive)

---

Planned cleanup & simplification (detailed plan)

Priority A — Safe, low-risk, high-value (implement first)

- [~] (In Progress) Migrate implementation to TypeScript + Electron app — started 2026-01-24  - [~] (In Progress) Port runner features from `archive/run_vimms.py` to `src/cli/runVimms.ts` — plan: (1) add `--src` support and `vimms_config.json` parsing with whitelist/blacklist and per-folder mappings; (2) implement folder discovery and priority sorting respecting `priority` and `defaults.folder_priority`; (3) support forwarded flags (`extract_files`, `delete_duplicates`, `yes_delete`, `prompt`); (4) add `--report` generation and `--report-format` behavior; (5) add tests and update docs.  - substeps:
  - scaffold Vite + React + TypeScript app in repo root (index.html, `src/main.tsx`, `src/renderer/` components) ✅
  - get `npm run dev` to launch Vite and Electron in dev mode and load the app ✅
  - port backend endpoints to an Express adapter (`src/server/app.ts`) ✅
  - convert legacy implementation into TypeScript modules under `src/` incrementally, adding small unit tests
  - wire the Electron preload bridge for filesystem access where appropriate
  - add project docs in `.github/*` describing the new structure and run/dev commands

  - detailed migration tasks (first pass):
    1. Create `src/api/` placeholder and copy endpoint contracts from `archive/src/webapp.py` → create TypeScript `src/api/types.ts` and `src/api/index.ts` (stubs) ✅ — basic API client added (calls FastAPI if present)
    2. Port `archive/src/metadata.py` → `src/metadata.ts` (parsing/caching logic) ✅ — tests added & passing
    3. Port `archive/src/downloader_lib/parse.py` and `fetch.py` → `src/downloader_lib/parse.ts` and `fetch.ts` (network parsing, form resolution) ✅ — basic parsing & tests added
    4. Port small utilities from `archive/src/utils/` → `src/utils/` (`filenames.ts`, `constants.ts`) ✅ — tests added & passing
    5. Add unit tests in `tests/ts/` for each ported module using `vitest` — tests added & passing for current ports
    6. Implement bridge layer to call FastAPI (temporary) or write a small Express adapter to expose endpoints used by UI ✅ — Express API implemented (`src/server/app.ts`) with queue/processed persistence and basic endpoints
    7. Move UI logic from `archive/src/webui_templates/` into `src/renderer/` components incrementally (table, details, queue) — in progress
    8. Add packaging (electron-builder) config adjustments for produced App — todo

  - detailed downloader migration tasks:
    A. Port `get_game_list_from_section` from `archive/src/download_vimms.py` → `src/downloader/index.ts` (first) ✅
    B. Port local indexing and detection helper methods (`_build_local_index`, `find_all_matching_files`, `is_game_present`) ✅ — tests added & passing
    C. Port download orchestration (download_game, extraction, categorization) — in progress ✅ (basic download + categorization implemented; extraction + retries/backoff implemented; worker + CLI implemented)
  - next substeps:
    - Implement `.7z` extraction support with graceful fallback when `7z` is not available (Completed) — 2026-01-24
    - Add persistent popularity cache to reduce repeated fetches (Completed) — 2026-01-24 (disk-backed cache stored at `ROMs/metadata_cache.json`, TTL 24h, tested)
    - Add UI progress spinner for batch popularity fetch (Completed) — 2026-01-24
    D. Add unit tests & small integration tests for each step — in progress

  - scripts & helpers:
    - Port `scripts/categorize_by_popularity.py` → `src/scripts/categorizeByPopularity.ts` ✅
    - Port `fix_folder_names.py`, `clean_filenames.py` → `src/scripts` or `src/utils` — `clean_filenames` ported as `src/utils/filenames.ts`, `fix_folder_names` pending

  - detailed migration tasks (first pass):
    1. Create `src/api/` placeholder and copy endpoint contracts from `archive/src/webapp.py` → create TypeScript `src/api/types.ts` and `src/api/index.ts` (stubs) ✅ — basic API client added (calls FastAPI if present)
    2. Port `archive/src/metadata.py` → `src/metadata.ts` (parsing/caching logic) ✅ — tests added & passing
    3. Port `archive/src/downloader_lib/parse.py` and `fetch.py` → `src/downloader_lib/parse.ts` and `fetch.ts` (network parsing, form resolution) ✅ — basic parsing & tests added
    4. Port small utilities from `archive/src/utils/` → `src/utils/` (`filenames.ts`, `constants.ts`) ✅ — tests added & passing
    5. Add unit tests in `tests/ts/` for each ported module using `vitest` — tests added & passing for current ports
    6. Implement bridge layer to call FastAPI (temporary) or write a small Express adapter to expose endpoints used by UI ✅ — Express API implemented (`src/server/app.ts`) with queue/processed persistence and basic endpoints
    7. Move UI logic from `archive/src/webui_templates/` into `src/renderer/` components incrementally (table, details, queue) — in progress
    8. Add packaging (electron-builder) config adjustments for produced App — todo

  - milestones:
    - M1: Dev app loads and shows sections/games with presence via API (stubbed or Python FastAPI) ✅
    - M2: `src/metadata.ts` and `src/downloader_lib/*` parity tests pass
    - M3: UI functions without calling `archive/` Python code (full TypeScript stack)
    - M4: Release build with `npm run build` and packaged electron binary

---

Planned cleanup & simplification (detailed plan)

Priority A — Safe, low-risk, high-value (implement first)

- [x] (Completed) Centralize filename cleaning and normalization into `utils/filenames.py` (moved `_clean_filename` and `_normalize_for_match` and updated callers) — 2026-01-24
  - substeps:
    - added `utils/filenames.py` and exported `clean_filename`, `normalize_for_match`
    - updated `clean_filenames.py` to import and use `clean_filename`
    - updated `download_vimms.py` to use `normalize_for_match` and `clean_filename`
    - updated tests to target utilities and fixed regressions
- [x] (Completed) Centralize ROM/archive extension lists and defaults in `utils/constants.py` — 2026-01-24
  - substeps:
    - added `utils/constants.py` (ROM_EXTENSIONS, ARCHIVE_EXTENSIONS, USER_AGENTS)
    - replaced duplicated ROM extension lists in `download_vimms.py`
    - added `tests/test_constants.py` to validate basic coverage of constants

Priority B — Medium-risk refactors (after A, add tests)

- [x] (Completed) Extract HTML parsing & network helpers from `VimmsDownloader` into `downloader_lib` module — 2026-01-24
  - substeps:
    - added parsing helpers (`downloader_lib/parse.py`) and unit tests with saved HTML fixtures
    - added fetch helpers (`downloader_lib/fetch.py`)
    - refactored `VimmsDownloader` to call helpers from `downloader_lib`
    - removed duplicate `download_vimms/` package (clean up) — 2026-01-24
- [~] (In Progress) Move implementation into `src/` package and add compatibility shims — 2026-01-24
  - substeps:
    - create `src/` and move `download_vimms.py`, `downloader_lib/`, `utils/` there
    - add top-level shims to keep backward-compatible imports
    - update tests and add a CLI smoke test
    - run tests and fix regressions
- [ ] (Todo) Add targeted tests for retry/backoff and 429 handling
- [ ] (Todo) Add extraction tests (zip/.7z) using monkeypatch/stubs for `py7zr` and `zipfile`

Priority C — Nice-to-have / packaging / docs

- [ ] (Todo) Add minimal `pyproject.toml` and make package installable for better test isolation
- [ ] (Todo) Move CLI code to `cli.py` (thin wrapper) and expose library functions for programmatic use
- [ ] (Todo) Add optional integration harness for manual downloads (safe, header-only checks)

Notes & workflow:

- Before starting a task, mark it In Progress and post a short plan. After completing, mark Completed and keep only last 10 completed tasks.
- We'll do Priority A now. I'll update this TODOs file as we progress.

(End of list)
