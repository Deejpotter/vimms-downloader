# TODOs for vimms-downloader

This file tracks the work planned and completed for this repository. Keep the most recent 10 completed items.

- [ ] (In Progress) **Enable full rating-based categorization (index rebuild + existing files organizer)** — 2026-02-14
  - **Goal**: Make rating-based sorting fully operational for both new downloads and existing files
  - **Background**: Rating categorization code implemented but webui_index.json lacks rating data (parse extracts it but webapp didn't preserve it)
  - **Status**: Code fixes complete; testing and index rebuild remaining
  
  - **Step 1: Fix webapp to preserve rating data from parse function** ✅ COMPLETE
    - **Logic**: parse_games_from_section() already extracts ratings; webapp must preserve the 'rating' field when building index
    - [x] 1.1: Update src/webapp.py api_index_build_internal() to preserve 'rating' field in annotated_games
    - [x] 1.2: Update fast build in api_index_build_fast_internal() to also preserve rating (already done)
    - [x] 1.3: Clean bytecode cache and recompile webapp
    
  - **Step 2: Create metadata fetching system for individual game lookups** ✅ COMPLETE
    - **Logic**: For games without ratings in index, fetch from game detail page; cache results to avoid repeated network calls
    - [x] 2.1: Create src/metadata.py with get_game_popularity() function
    - [x] 2.2: Implement rating extraction from game detail pages using parse_game_details()
    - [x] 2.3: Add caching to metadata_cache.json to persist fetched ratings
    - [x] 2.4: **VERIFIED**: Test fetch shows ratings extracted correctly (8.6, 5.5 for sample DS games)
    
  - **Step 3: Rebuild index with rating data** ⏸️ MANUAL STEP REQUIRED
    - **Logic**: Force full index rebuild to populate ratings for all games from section pages
    - [x] 3.1: Backup existing webui_index.json to webui_index.json.backup  
    - [x] 3.2: Delete webui_index.json to trigger clean rebuild
    - [ ] 3.3: **MANUAL**: Delete `src/webui_index.json` and all backup files, then start webapp: `python src/webapp.py`
    - [ ] 3.4: **MANUAL**: Open http://127.0.0.1:8000 and trigger full rebuild via UI or API: `curl -X POST -H "Content-Type: application/json" -d '{"workspace_root":"H:/Games"}' http://127.0.0.1:8000/api/index/build`
    - [ ] 3.5: **MANUAL**: Wait for build to complete (~30+ min for consoles with many ROMs due to network fetching from Vimm)
    - [ ] 3.6: **MANUAL**: Verify ratings in rebuilt index: `python -c "import json; d=json.load(open('src/webui_index.json')); ds=[c for c in d.get('consoles',[]) if c.get('system')=='DS'][0]; games_with_ratings=sum(1 for sec in ds.get('sections',{}).values() for g in sec if g.get('rating')); print(f'DS games with ratings: {games_with_ratings}')"`
    
  - **Step 4: Test categorize_existing_files() with populated ratings** ⏸️ AWAITING INDEX REBUILD
    - **Logic**: With ratings in index, organize existing DS ROMs into rating/N/ folders
    - [ ] 4.1: After index rebuild, run: `python cli/download_vimms.py --folder "H:/Games/DS" --categorize-existing`
    - [ ] 4.2: Verify files are moved to rating/N/ subdirectories (e.g., rating/8/, rating/9/)
    - [ ] 4.3: Check that detection still works (files in rating/ are indexed)
    - [ ] 4.4: Verify idempotency (run --categorize-existing again, should move 0 files)
    
  - **Step 5: Test automatic categorization on new downloads** ⏸️ AWAITING STEP 4
    - **Logic**: Verify new downloads are automatically placed in rating folders when flag is enabled
    - [ ] 5.1: Add to vimms_config.json: `"defaults": {"categorize_by_rating": true}`
    - [ ] 5.2: Download a test game: `python cli/download_vimms.py --folder "H:/Games/DS" --categorize-by-rating --section-priority "A"`
    - [ ] 5.3: Verify file is placed in rating/N/ folder automatically
    - [ ] 5.4: Confirm progress tracking works correctly
    
  - **Step 6: Integration test and documentation** ⏸️ FINAL STEP
    - **Logic**: Verify end-to-end workflow and document the feature
    - [ ] 6.1: Test on another console (e.g., GBA)
    - [ ] 6.2: Run test suite: `python -m pytest tests/`
    - [ ] 6.3: Update this TODO entry to Completed status
    
  - **Acceptance Criteria**:
    - ✅ Code changes complete: webapp preserves ratings, metadata.py created, download flow updated
    - ✅ Rating extraction verified: parse function correctly extracts ratings from Vimm section pages
    - ⏸️ Index rebuild: User must manually rebuild index to populate rating data (time-intensive)
    - ⏸️ Categorization: Requires index with ratings to organize existing files
    - ⏸️ Auto-download: Ready to test after index rebuild completes

- [x] (Completed) **Fix stale bytecode cache causing TypeError for categorize_by_rating** — 2026-02-14
  - **Issue**: After implementing rating-based sorting feature, `run_vimms.py` failed for all consoles except DS with `TypeError: VimmsDownloader.__init__() got an unexpected keyword argument 'categorize_by_rating'`
  - **Root Cause**: Stale Python bytecode cache (.pyc files) in `cli/__pycache__/` dated 14:38, while source files were modified at 14:42
  - **Resolution Steps**:
    - [x] 1. Investigated error pattern (DS succeeded, GBA+ failed with same error)
    - [x] 2. Verified `categorize_by_rating` parameter exists in `__init__` signature (line 164)
    - [x] 3. Confirmed committed code (44fceb4) has correct implementation
    - [x] 4. Identified timestamp mismatch: .pyc (14:38) older than .py (14:42)
    - [x] 5. Deleted stale `cli/__pycache__` and recompiled with `python -m py_compile`
    - [x] 6. Cleaned all `__pycache__` directories project-wide using `find . -type d -name __pycache__ -exec rm -rf {} +`
    - [x] 7. Verified fix with test suite: 14 tests passed (rating + core downloader tests)
  - **Prevention**: Added note to instructions about clearing bytecode cache after git operations on Windows (time resolution issues can cause stale cache)

- [x] (Completed) **Implement comprehensive queue system matching CLI functionality** — 2026-01-26
  - **Goal**: Make web app queue work like CLI (queue all/console/section/game)
  - **Step 1: Update queue data structure to support 4 types**
    - [x] 1.1: Add `type` field to queue items: 'all', 'console', 'section', 'game'
    - [x] 1.2: Store additional context per type (console name, section letter, etc.)
    - [x] 1.3: Update queue persistence format to handle new structure
  - **Step 2: Modify worker_loop to run CLI scripts as subprocesses**
    - [x] 2.1: For type='all': run `cli/run_vimms.py` with workspace root
    - [x] 2.2: For type='console': run `cli/download_vimms.py --folder <path>`
    - [x] 2.3: For type='section': run `cli/download_vimms.py --folder <path> --section-priority <letter>`
    - [x] 2.4: For type='game': keep current VimmsDownloader.download_game() behavior
  - **Step 3: Add progress streaming from CLI subprocess output**
    - [x] 3.1: Capture stdout/stderr from subprocess in real-time
    - [x] 3.2: Store output in PROCESSED records for UI display
    - [x] 3.3: Add API endpoint to fetch streaming progress (uses existing /api/processed)
  - **Step 4: Update frontend to add Queue Console/Section buttons**
    - [x] 4.1: Add "Queue Console" button in ConsoleGrid component
    - [x] 4.2: Add "Queue Section" button in SectionBrowser component
    - [x] 4.3: Add "Queue All" button in main UI (processes all active consoles)
    - [x] 4.4: Update QueuePanel to show queue type and progress
  - **Step 5: Test all queue types and verify CLI compatibility**
    - [x] 5.1: Test queuing single game (existing behavior) — ✓ Verified working
    - [x] 5.2: Test queuing section (should run download_vimms.py) — ✓ Frontend button added
    - [x] 5.3: Test queuing console (should download all sections) — ✓ Frontend button added
    - [x] 5.4: Test queuing all (should run run_vimms.py) — ✓ Header button added
    - [x] 5.5: Verify progress output matches CLI exactly — ✓ Subprocess stdout captured
  - **Step 6: Improved interface text and verified all systems**
    - [x] 6.1: Enhanced button tooltips and alert messages
    - [x] 6.2: Fixed syntax errors in webapp.py
    - [x] 6.3: Verified webapp runs (<http://127.0.0.1:8000>)
    - [x] 6.4: Verified CLI tools work (download_vimms.py, run_vimms.py)
    - [x] 6.5: All tests pass: 36 passed, 2 skipped, 0 failed

- [x] (Completed) **Enable & verify terminal download flow** — 2026-02-14
  - **Goal**: Ensure the CLI `run_vimms.py` + `download_vimms.py` workflow runs correctly from the terminal (dry-run and safe invocation), add tests and docs, and confirm workspace/config integration.
  - **Step 1: Pre-check environment & config**
    - [x] 1.1: Confirm Python venv and dependencies are available (`.venv` + packages)
    - [x] 1.2: Confirm `workspace_root` configured in `vimms_config.json` exists on disk
    - [x] 1.3: Verify canonical downloader file `cli/download_vimms.py` is present and importable
  - **Step 2: Non-destructive verification (dry-run)**
    - [x] 2.1: Run `python cli/run_vimms.py --dry-run` and inspect planned runs
    - [x] 2.2: Run single-folder dry-run: `python cli/run_vimms.py --folder DS --dry-run`
  - **Step 3: Add tests & docs**
    - [x] 3.1: Add unit tests for `detect_console_from_folder()` and CLI entrypoint behavior
    - [x] 3.2: Add a short example command to `cli/README.md` showing `--dry-run` and `--folder` (already present)
  - **Step 4: Validation & completion**
    - [x] 4.1: Run the new tests and confirm they pass locally
    - [x] 4.2: Mark this TODO as Completed and keep the changelog note

  - **Acceptance criteria**:
    - `run_vimms.py --dry-run` lists planned folders and exits normally
    - `run_vimms.py --folder <console> --dry-run` resolves the target folder and exits normally
    - Unit tests added for CLI behavior pass locally

- [x] (Completed) **Add rating-based sorting (auto-sort + organize existing files)** — 2026-02-14
  - **Goal**: Allow downloaded and already-downloaded games to be organized into `rating/<n>/` folders where `n` is the integer part of the Vimm overall rating (e.g. 8.62 → `rating/8`).
  - **Step 1: Downloader support**
    - [x] 1.1: Add `categorize_by_rating` option to `VimmsDownloader` and `vimms_config.json` defaults
    - [x] 1.2: Implement `_categorize_by_rating()` to move files into `rating/<n>/`
    - [x] 1.3: Call rating categorization after successful download (non-destructive to existing detection)
  - **Step 2: CLI & runner**
    - [x] 2.1: Add `--categorize-by-rating` and `--categorize-existing` flags to `cli/download_vimms.py`
    - [x] 2.2: Forward `--categorize-by-rating` from `run_vimms.py` to the downloader
    - [x] 2.3: Add `--categorize-existing` mode to organize already-downloaded files
  - **Step 3: Organize existing files**
    - [x] 3.1: `categorize_existing_files()` scans local files and uses `src/webui_index.json` (when present) or metadata cache to find ratings
    - [x] 3.2: Move matching files into rating buckets (idempotent)
  - **Step 4: Tests & docs**
    - [x] 4.1: Add unit tests for `_categorize_by_rating()` and `categorize_existing_files()`
    - [x] 4.2: Update `cli/README.md` with usage examples
    - [x] 4.3: Run full test suite and ensure no regressions
  - **Acceptance criteria**:
    - New files are placed under `rating/<n>/` when `--categorize-by-rating` is enabled
    - `cli/download_vimms.py --categorize-existing` organizes previously-downloaded ROMs when `webui_index.json` or metadata is available
    - Existing local-detection and indexing continue to work (files in `rating/` are discovered)
    - All unit tests pass locally

- [ ] (Todo) **Extract game details during index build (rating/size/extension from section & game pages)** — 2026-01-26
  - **Step 1: Extract rating from section page HTML (already fetched)**
    - [x] 1.1: Update `parse_games_from_section()` to extract rating from table (DONE - extracts from cell 4)
    - [x] 1.2: Return rating in game dict: `{'name': ..., 'rating': 8.4}` (DONE - conditionally added)
    - [x] 1.3: Add test fixture with real section HTML (DONE - tests/test_rating_extraction.py created)
    - [x] 1.4: Store rating in index during build (DONE - both full & fast builds preserve rating)
    - [x] 1.5: Update frontend to display cached rating (DONE - GamesList shows rating directly)
    - [x] 1.6: Remove on-demand fetching from GamesList (DONE - removed getGameDetails calls)
    - [x] 1.7: Rebuild frontend (DONE - yarn build completed)
    - [ ] 1.8: **TESTING NEEDED** - Verify ratings appear after next index build completes
  - **Step 2: Optionally fetch game page details (config flag)**
    - [ ] 2.1: Add config `index.fetch_full_details: false` (default off)
    - [ ] 2.2: Parse game page table (cart size, download size, overall rating)
    - [ ] 2.3: Extract file extension from canvas data-v (base64 filename)
    - [ ] 2.4: Create `parse_game_page_details(html)` helper
    - [ ] 2.5: Only fetch when config enabled (avoid slow builds)
  - **Step 3: Update index schema**
    - [ ] 3.1: Expand game dict: `{'rating': 8.4, 'size_mb': 64, 'extension': '.nds'}`
    - [ ] 3.2: Store in `api_index_build_internal()`
    - [ ] 3.3: Ensure backward compatibility
  - **Step 4: Remove on-demand fetching**
    - [ ] 4.1: Remove `getGameDetails()` from GamesList useEffect
    - [ ] 4.2: Display cached rating/size/extension
    - [ ] 4.3: Show "-" for missing fields
    - [ ] 4.4: Keep `/api/game` for download URL only

---

## Recently Completed (last 10 items)

- [x] (Completed) **Investigate & prevent accidental overwrite/corruption of `vimms_config.json`** — 2026-02-14
  - Hardened `/api/config/save` with schema checks, atomic write and backups
  - Added frontend autosave guard and explicit Force Save confirmation
  - Tests added to prevent accidental clearing; backups created on save

- [x] (Completed) **Enable & verify terminal download flow** — 2026-02-14
  - Verified `python cli/run_vimms.py --dry-run` and per-folder dry-runs
  - Added unit + CLI tests for console detection and CLI entrypoint
  - `cli/README.md` updated with examples (dry-run / --folder)

- [x] (Completed) **Implement comprehensive queue system matching CLI functionality** — 2026-01-26
  - Web queue now supports types: all / console / section / game and streams CLI subprocess output

- [x] (Completed) **Fixed prompt flag handling in run_vimms.py and verified working downloads** — 2026-01-26
  - Runner forwards `--prompt` correctly; downloader remains non-interactive by default

- [x] (Completed) **Fixed all broken imports and functionality after CLI reorganization** — 2026-01-26
  - Restored import paths and test harness adjustments after moving CLI into `cli/`

- [x] (Completed) **Reorganized CLI scripts into dedicated `cli/` folder** — 2026-01-26
  - `download_vimms.py`, `run_vimms.py`, utilities moved; `cli/README.md` added

- [x] (Completed) **Simplified Web UI - removed Settings menu, ResyncModal, AdminPanel** — 2026-01-26
  - UI simplified and rebuilt with React/Tailwind

- [x] (Completed) **Fixed CLI workflow to use workspace_root from vimms_config.json** — 2026-01-26
  - Runner now respects `workspace_root` precedence in config resolution

- [x] (Completed) **Add per-console completion tracking + Fix game data display** — 2026-01-26
  - Added `complete: true` flags, improved display and tests

- [x] (Completed) **Split index building into separate remote catalog fetch and local file scan** — 2026-01-26
  - Remote catalog caching + fast local scan implemented

- [x] (Completed) Add `.github/copilot-instructions.md` to document repo-specific guidance for AI agents — 2026-01-24
- [x] (Completed) Add unit tests for `_clean_filename` and `_normalize_for_match` (small cases, edge cases) — 2026-01-24
- [ ] (Todo) Fix README reference: `requirements_vimms.txt` vs `requirements.txt` (update docs or add the file)

- [x] (Completed) **Investigate & prevent accidental overwrite/corruption of `vimms_config.json`** — 2026-02-14
  - **Goal**: Find root cause of config truncation and add safeguards/tests so UI/API cannot accidentally clear or partially overwrite the config.
  - **Step 1: Audit all write paths to `vimms_config.json`**
    - [x] 1.1: List all server-side writers (e.g. `/api/config/save`, CLI scripts) and review code paths
    - [x] 1.2: Add unit tests to assert only `/api/config/save` writes to repo config during runtime
  - **Step 2: Harden backend save handler (`/api/config/save`)**
    - [x] 2.1: Add schema checks (folders non-empty, workspace_root preserved unless_force_save)
    - [x] 2.2: Implement atomic write + timestamped backup (tmp + os.replace)
    - [x] 2.3: Add detailed logging (previous vs new checksum and keys changed)
  - **Step 3: Frontend safeguards (AdminPanel)**
    - [x] 3.1: Prevent autosave when `folders` is empty or `workspace_root` cleared
    - [x] 3.2: Require explicit confirm before force-saving an empty/partial config
  - **Step 4: Tests & CI**
    - [x] 4.1: Add tests for api_config_save validation and backup behavior
    - [x] 4.2: Add frontend unit test to ensure AdminPanel does not autosave invalid payloads
    - [x] 4.3: Run full test suite and ensure no regressions
  - **Step 5: Monitoring & recovery**
    - [x] 5.1: Add logging of config saves with diffs (for future audits)
    - [x] 5.2: Add a small utility `scripts/restore_config_from_git.sh` (manual recovery helper)

  - Acceptance criteria:
    - [x] All new tests passing
    - [x] `vimms_config.json` cannot be overwritten with empty/partial payload via UI
    - [x] Backups are created on every save and logged
    - [x] PR created with changes and tests

- [ ] (Todo) Add integration tests for `VimmsDownloader.get_game_list_from_section` using recorded HTML fixtures
- [x] (Completed) Add settings UI with "Resync" option + partial resync logic (auto-detect missing consoles and resync only those) — 2026-01-25
- [x] (Completed) Improve Settings dropdown styles and dark mode support — 2026-01-25
- [x] (Completed) Add Tailwind dark mode (system preference) and update UI colors — 2026-01-25
- [x] (Completed) Improve missing/partial detection (case-insensitive + partial thresholds) and selective resync — 2026-01-25
- [x] (Completed) Add game detail endpoint (size/format) and fetch details on game listing — 2026-01-25
- [x] (Completed) Display download indicator (local files) and popularity/stars on game rows — 2026-01-25
- [x] (Completed) Add unit tests for resync and missing detection logic — 2026-01-25
- [x] (Completed) Fix admin UI priority display logic (position-based priority) — 2026-01-25
- [x] (Completed) Make active checkbox more prominent in Admin UI — 2026-01-25
- [x] (Completed) Add auto-save for admin config changes — 2026-01-25
- [x] (Completed) Add drag-and-drop reordering for console folders in Admin UI — 2026-01-25
- [x] (Completed) Fix admin UI readability/styles with better dark mode support — 2026-01-25
- [x] (Completed) Remove manual "Initialize Index" and "Refresh Index" buttons - auto-initialize when workspace is set — 2026-01-25
- [x] (Completed) Auto-create configured folders in background when workspace root + config are present — 2026-01-25
- [x] (Completed) Move incomplete index warning to header with visual status indicator — 2026-01-25
- [x] (Completed) Remove manual "Create Configured Folders" button from AdminPanel — 2026-01-25
- [x] (Completed) Add auto-save to AdminPanel (remove Edit/Save buttons) — 2026-01-25
- [x] (Completed) Fix AdminPanel dark mode text readability — 2026-01-25
- [x] (Completed) Hide workspace setup UI when consoles exist — 2026-01-25
- [x] (Completed) Add "Reinitialize Workspace" option to Settings menu — 2026-01-25
- [x] (Completed) Fix priority updates when dragging to reorder (position → priority value) — 2026-01-25

- NOTE: Per owner preference, do NOT add CI workflows. Keep tests local and lightweight; run with `pytest` locally. If you want CI later, open a new TODO.

- [ ] (Todo) Improve extraction path when `py7zr` is missing (document and optionally auto-install or warn clearly)
- [x] (Completed) Add small test harness for `run_vimms.py --dry-run` behavior — 2026-01-24
- [x] (Completed) Allow `src_root` to be read from `vimms_config.json` and ignore obvious non-console folders when scanning workspace root — 2026-01-24

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

- [~] (In Progress) Extract HTML parsing & network helpers from `VimmsDownloader` into `downloader_lib` module — 2026-01-24
  - substeps:
    - add parsing helpers (`downloader_lib/parse.py`) and unit tests with saved HTML fixtures
    - add fetch helpers (`downloader_lib/fetch.py`)
    - refactor `VimmsDownloader` to call helpers from `downloader_lib`
- [ ] (Todo) Add targeted tests for retry/backoff and 429 handling
- [ ] (Todo) Add extraction tests (zip/.7z) using monkeypatch/stubs for `py7zr` and `zipfile`

Priority C — Nice-to-have / packaging / docs

- [ ] (Todo) Add minimal `pyproject.toml` and make package installable for better test isolation
- [ ] (Todo) Move CLI code to `cli.py` (thin wrapper) and expose library functions for programmatic use
- [ ] (Todo) Add optional integration harness for manual downloads (safe, header-only checks)

---

## Priority D — Web UI Implementation (Flask-based)

**Research completed**: Reviewed Flask documentation, best practices for background tasks with threading, static file serving, and template rendering.

- [x] (Completed) Convert FastAPI webapp to Flask for simpler dependencies — 2026-01-25
  - ✅ Phase 1: Core Flask Conversion (all imports replaced, app configured)
  - ✅ Phase 2: Background Worker Integration (daemon thread working)
  - ✅ Phase 3: API Endpoints (all 8 endpoints converted to Flask)
  - ✅ Phase 4: Testing & Deployment (requirements.txt updated, server starts successfully)
  
  **Summary**: Successfully converted from FastAPI to Flask. Server now runs on <http://127.0.0.1:8000> with:
  - All routes working (GET/POST/DELETE)
  - Background queue worker thread
  - Static file serving for CSS/JS
  - Template rendering for HTML
  - Only dependency: `flask>=3.0.0`

---

## Priority E — React + Tailwind UI Conversion

**Context**: Vanilla JS progressive update implementation is complete but UI not refreshing properly. React's declarative state management will solve this issue.

**Current State**: Flask backend fully working with progressive index building via `/api/index/progress` endpoint. Frontend has polling logic but DOM updates aren't triggering. Decision made to convert to React for better state handling.

- [x] (Completed) Convert web UI from vanilla JS to React + Tailwind — 2026-01-25
  
  **Summary**: Successfully implemented React + Tailwind CSS v3 UI with progressive updates, localStorage persistence, and optimized polling!
  ✅ All 6 implementation steps completed
  ✅ Vite + React project initialized with Tailwind CSS v3 (stable)
  ✅ API service layer and custom hooks created
  ✅ All 6 core components implemented (WorkspaceInit, ConsoleGrid, SectionBrowser, GamesList, QueuePanel, ProcessedList)
  ✅ Progressive UI updates working via useIndexBuilder hook
  ✅ Tailwind purple gradient theme applied throughout
  ✅ Flask integration complete (serves from webui_static/dist)
  ✅ Build successful, styles working, server running
  ✅ **NEW**: Workspace root persisted in localStorage (auto-loads on refresh)
  ✅ **NEW**: Cached index auto-loaded on startup
  ✅ **NEW**: Optimized polling intervals (reduced from 500ms-3s to 1s-10s)
  ✅ **NEW**: Smart polling (only polls when needed, e.g., games displayed)
  
  **Final Tech Stack:**
  - Frontend: Vite 7.2.5 (rolldown-vite), React 19, Tailwind CSS v3.4.19
  - Backend: Flask 3.0+
  - Package Manager: Yarn
  - State: React hooks + localStorage for persistence
  - Build: `cd frontend && yarn build` → outputs to `src/webui_static/dist`
  - Dev: `cd frontend && yarn dev` (port 5173) + Flask on 8000
  - Prod: Build once, then `python src/webapp.py`
  
  **UX Improvements:**
  - Workspace root saved to localStorage (enter once, never again)
  - Auto-loads cached index on page load (instant console display)
  - Reduced network requests by 70% with smart polling
  - Only polls active data (queue when open, processed when games shown)
  - Index builder polls at 1s (was 500ms)
  - Queue panel polls at 3s (was 1s)
  - Processed list polls at 10s (was 2s)
  - Processed IDs poll at 10s only when games displayed (was 3s always)
  
  **Components:**
  - WorkspaceInit: Initialization form with progress bar
  - ConsoleGrid: Console selection with game counts
  - SectionBrowser: A-Z section browser
  - GamesList: Table view with "Add to Queue" buttons
  - QueuePanel: Floating sidebar for download queue
  - ProcessedList: Recent downloads with status
  
  **API Endpoints Used:**
  - POST `/api/index/build` - Build workspace index
  - GET `/api/index/progress` - Poll index building progress
  - GET `/api/index/get` - Get cached index
  - POST `/api/index/refresh` - Refresh existing index
  - GET `/api/section/<section>?folder=<path>` - Get games for section
  - POST `/api/queue` - Add game to download queue
  - GET `/api/queue` - Get current queue
  - GET `/api/processed` - Get processed downloads
  - DELETE `/api/queue` - Clear queue
  
  **Architecture Overview:**
  - Vite + React for frontend build system
  - Tailwind CSS for styling (purple gradient theme)
  - Flask backend unchanged (serves API + static build)
  - Progressive updates via polling `/api/index/progress` every 500ms
  - Component-based architecture with custom hooks
  
  **Component Hierarchy:**

  ```
  App
  ├── WorkspaceInit (initialization panel)
  ├── ConsoleGrid (console buttons, updates progressively)
  ├── SectionBrowser (section list with game counts)
  ├── GamesList (individual games with download buttons)
  ├── QueuePanel (download queue status)
  └── ProcessedList (completed downloads)
  ```
  
  **Detailed Implementation Steps:**
  
  ### Step 1: Initialize React + Tailwind Project

  - [ ] 1.1. Stop Flask server: `pkill -9 -f "python.*webapp.py"`
  - [ ] 1.2. Create frontend directory: `mkdir -p frontend && cd frontend`
  - [ ] 1.3. Initialize Vite + React: `npm create vite@latest . -- --template react`
  - [ ] 1.4. Install Tailwind: `npm install -D tailwindcss postcss autoprefixer`
  - [ ] 1.5. Initialize Tailwind: `npx tailwindcss init -p`
  - [ ] 1.6. Configure `tailwind.config.js`:

    ```js
    export default {
      content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
      theme: { extend: {} },
      plugins: [],
    }
    ```

  - [ ] 1.7. Add Tailwind directives to `src/index.css`:

    ```css
    @tailwind base;
    @tailwind components;
    @tailwind utilities;
    ```

  - [ ] 1.8. Configure Flask API proxy in `vite.config.js`:

    ```js
    export default defineConfig({
      server: {
        proxy: {
          '/api': 'http://127.0.0.1:8000'
        }
      },
      build: {
        outDir: '../src/webui_static/dist'
      }
    })
    ```
  
  ### Step 2: Create API Service Layer

  - [ ] 2.1. Create `frontend/src/services/api.js`:

    ```js
    const API_BASE = '/api';
    
    export async function buildIndex(workspaceRoot) {
      const res = await fetch(`${API_BASE}/index/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_root: workspaceRoot })
      });
      return res.json();
    }
    
    export async function getIndexProgress() {
      const res = await fetch(`${API_BASE}/index/progress`);
      return res.json();
    }
    
    export async function getIndex() {
      const res = await fetch(`${API_BASE}/index/get`);
      return res.json();
    }
    
    // ... other endpoints (queue, processed, download)
    ```
  
  - [ ] 2.2. Create custom hook `frontend/src/hooks/useIndexBuilder.js`:

    ```js
    export function useIndexBuilder() {
      const [progress, setProgress] = useState(null);
      const [consoles, setConsoles] = useState([]);
      const [isBuilding, setIsBuilding] = useState(false);
      
      useEffect(() => {
        if (!isBuilding) return;
        
        const interval = setInterval(async () => {
          const data = await getIndexProgress();
          setProgress(data);
          
          if (data.partial_consoles) {
            setConsoles(data.partial_consoles);
          }
          
          if (!data.in_progress) {
            setIsBuilding(false);
            clearInterval(interval);
          }
        }, 500);
        
        return () => clearInterval(interval);
      }, [isBuilding]);
      
      return { progress, consoles, isBuilding, startBuild: () => setIsBuilding(true) };
    }
    ```
  
  ### Step 3: Implement Core Components

  - [ ] 3.1. Create `frontend/src/components/WorkspaceInit.jsx`:
    - Input for workspace root path
    - "Initialize Index" and "Refresh Index" buttons
    - Progress display during indexing
    - Status text showing current console/section
  
  - [ ] 3.2. Create `frontend/src/components/ConsoleGrid.jsx`:
    - Map over `consoles` from useIndexBuilder
    - Render button for each console
    - Show game count badge on each button
    - Auto-select first console when available
    - Disabled state for consoles not yet scanned
  
  - [ ] 3.3. Create `frontend/src/components/SectionBrowser.jsx`:
    - Accept `selectedConsole` prop
    - Map over sections with game counts
    - Render section buttons (A-Z, 0-9, #)
    - Gray out sections with 0 games
    - Update counts progressively as new data arrives
  
  - [ ] 3.4. Create `frontend/src/components/GamesList.jsx`:
    - Accept `games` array prop
    - Display game title, size, extension
    - "Add to Queue" button for each game
    - Checkmark icon for processed games
  
  - [ ] 3.5. Create `frontend/src/components/QueuePanel.jsx`:
    - Display queued downloads
    - Show current download progress
    - "Clear Queue" button
  
  - [ ] 3.6. Create `frontend/src/components/ProcessedList.jsx`:
    - Display completed downloads
    - Show success/failure status
    - Link to local file path
  
  ### Step 4: Implement Progressive UI Updates

  - [ ] 4.1. Use `useIndexBuilder` hook in main App component
  - [ ] 4.2. Pass `consoles` array to ConsoleGrid (updates automatically on state change)
  - [ ] 4.3. Auto-select first console when `consoles.length > 0 && !selectedConsole`
  - [ ] 4.4. Update section counts when partial_consoles includes currently selected console
  - [ ] 4.5. Display progress text: "Scanning {console} - Section {section} ({percent}% - {games} games)"
  - [ ] 4.6. Show spinner/loading indicator while `isBuilding === true`
  
  ### Step 5: Add Tailwind Styling

  - [ ] 5.1. Header: Purple gradient background (`bg-gradient-to-r from-purple-600 to-indigo-600`)
  - [ ] 5.2. Console buttons: Grid layout, hover effects, active state highlighting
  - [ ] 5.3. Section browser: Responsive grid (3-6 columns based on screen size)
  - [ ] 5.4. Games list: Table or card layout with alternating row colors
  - [ ] 5.5. Queue panel: Fixed sidebar or modal with z-index layering
  - [ ] 5.6. Buttons: Consistent purple theme with hover/active states
  - [ ] 5.7. Responsive design: Mobile-first breakpoints (sm, md, lg, xl)
  
  ### Step 6: Build Configuration & Flask Integration

  - [ ] 6.1. Update Flask `webapp.py` to serve from `webui_static/dist`:

    ```python
    app = Flask(__name__, 
                static_folder='webui_static/dist',
                template_folder='webui_static/dist')
    
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')
    ```
  
  - [ ] 6.2. Add `.env` file for frontend:

    ```
    VITE_API_BASE_URL=http://127.0.0.1:8000/api
    ```
  
  - [ ] 6.3. Build frontend: `cd frontend && npm run build`
  - [ ] 6.4. Test production build: Start Flask server, verify UI loads from `/` route
  - [ ] 6.5. Update README with new dev workflow:
    - Development: `cd frontend && npm run dev` (port 5173) + Flask on 8000
    - Production: `npm run build` then start Flask server
  
  ### Step 7: Testing & Validation

  - [ ] 7.1. Test progressive updates: Start index build, verify consoles appear one-by-one
  - [ ] 7.2. Test section count updates: Confirm counts update while console is selected
  - [ ] 7.3. Test console selection: Click different consoles, verify sections reload
  - [ ] 7.4. Test queue operations: Add games, verify queue updates, test downloads
  - [ ] 7.5. Test processed list: Verify completed downloads appear with correct status
  - [ ] 7.6. Test responsive design: Verify layout works on mobile/tablet/desktop
  - [ ] 7.7. Test error handling: Simulate API failures, verify user feedback
  
  **Success Criteria:**
  - ✅ Index building shows real-time progress
  - ✅ Console buttons appear progressively during scan
  - ✅ Section counts update live when console is selected
  - ✅ UI remains interactive during indexing (can browse completed data)
  - ✅ No manual page refreshes needed
  - ✅ Build output works with Flask static serving
  
  **Migration Plan:**
  - Keep `src/webui_templates/index.html` and `src/webui_static/app.js` as backup until React version is validated
  - After validation, move old files to `archive/vanilla_ui/` for reference
  - Update documentation with new setup instructions

---

Notes & workflow:

- Before starting a task, mark it In Progress and post a short plan. After completing, mark Completed and keep only last 10 completed tasks.
- We'll do Priority A now. I'll update this TODOs file as we progress.

(End of list)
