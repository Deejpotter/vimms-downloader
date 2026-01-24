# Vimm's Lair Downloader — Games Workspace

Brief: a small toolset to download and clean ROMs from Vimm's Lair.

Getting started ✅

- The canonical Python implementation has been moved to `archive/` for reference and is run using a Python venv as before. See `README_VIMMS.md` inside `archive/` for Python-specific instructions.

- New Desktop UI (Electron + Vite + React + TypeScript): install Node deps and run in dev mode:

```bash
npm install
npm run dev
```

- Python-only workflows (downloader/tests) still use a venv and `requirements.txt` inside the repo root and/or `archive/requirements.txt`:

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash / WSL on Windows
pip install --upgrade pip
pip install -r requirements.txt
```

Running downloads 🔧

- TypeScript / Desktop workflow (current development target):
  - The Electron UI + Express API provide a local interface to browse, inspect, and queue games for download. To start the development stack:
    - `npm install`
    - `npm run dev:all` (starts the Express API, Vite dev server, and Electron)
  - CLI: The former `run_vimms.py` runner is being replaced by a TypeScript CLI. Run the CLI to perform downloads from the command line:
    - Dry run (no downloads): `npm run run:cli -- --folder "C:/path/to/console" --dry-run`
    - Default (perform downloads): `npm run run:cli -- --folder "C:/path/to/console"`
  - Note: The Express API worker processes queue items sequentially (no concurrency) and `downloadGame` performs downloads, extraction for `.zip` and `.7z` (uses system `7z` for `.7z` archives when available), and optional categorization. A disk-backed popularity cache is stored at `ROMs/metadata_cache.json` for each target folder (TTL default 24h). To clear the cache for a folder, delete `ROMs/metadata_cache.json`.

- Python archive (canonical reference / fallback):
  - The original Python downloader remains the canonical reference implementation under `archive/` and supports the full download workflow today. If you need to perform actual downloads while the TypeScript port is in progress, run the Python runner:
    - Create and activate a venv and install Python deps: `python -m venv .venv && source .venv/Scripts/activate && pip install -r archive/requirements.txt`
    - Run a folder: `python run_vimms.py --folder "G:/My Drive/Games/PS2" --apply`
  - When the TypeScript downloader reaches parity, the Python archive will be kept for reference and tests but the default developer flow will use the TypeScript/Express stack.

Notes about detection 💡

- The downloader normalizes and fuzzy-matches game titles against files already
  present in the target folder. It will skip titles it believes you already
  have (and mark them in `download_progress.json`). The comparison:
  - cleans filenames (removes tags/region markers), normalizes punctuation and case,
  - compares containment (A in B or B in A), then falls back to a fuzzy ratio (>= 0.75).

Repository layout 🔍

- `download_vimms.py` — canonical downloader at the workspace root (used by the runner)
- `run_vimms.py` — small wrapper to call `download_vimms.py` against any folder
- `downloader_lib/` — parsing and network helpers used by `download_vimms.py` (e.g., `parse.py`, `fetch.py`)
- `clean_filenames.py` — filename cleaner; runs on the folder it's executed within
- `requirements.txt` — pip requirements used by the downloader

Testing ✅

- Run unit tests locally:

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash / WSL on Windows
pip install --upgrade pip
pip install -r requirements.txt
pytest
```

- CI: a minimal GitHub Actions workflow runs the test suite on push and pull requests (`.github/workflows/python-tests.yml`) and executes `pytest`.

Notes on running from a separate workspace root

- If you keep source/config files in a separate project folder (for example, `H:/Repos/vimms-downloader/src`), both `run_vimms.py` and `download_vimms.py` accept a `--src` option to point at your project root so they can locate `vimms_config.json`, scripts, and logs. Example:

```bash
python run_vimms.py --src "H:/Repos/vimms-downloader/src" --dry-run
```

- Absolute paths are supported for the `--folder`/`--src` options (e.g., `H:/Games` or `C:/Games`). The downloader will create the target `ROMs` subfolder and write `download_progress.json` there when performing downloads.

If you'd like any behavior changed (different fuzzy threshold, different matching rules,
or automated cleaning of filenames before detection), I can implement that quickly.

---
Updated: added fuzzy-local-file detection and `--no-detect-existing` flag; consolidated
canonical scripts at workspace root.

New utilities

- `scripts/categorize_by_popularity.py` — Categorize your downloaded ROMs into buckets based on Vimm popularity. Run in dry-run mode first to preview moves:
  - `python scripts/categorize_by_popularity.py --folder G:/Games/DS --dry-run`
  - Two modes are supported with `--mode`: `stars` (default) buckets into `ROMs/stars/<n>/` (1..5) or `score` buckets into `ROMs/score/<n>/` (rounded 0..10).
  - Example (score mode apply): `python scripts/categorize_by_popularity.py --folder G:/Games/DS --apply --mode score`

- Experimental Web UI — local web interface to browse sections, view popularity, queue games and monitor processed tasks.
  - Two ways to run the API during migration:
    - Python (FastAPI): the canonical Python implementation remains under `archive/` and can be started with a venv:
      - Activate venv and run: `python -m uvicorn src.webapp:app --reload --port 8000`
      - Or on Windows use the bundled script: `.venv\Scripts\uvicorn.exe src.webapp:app --reload --port 8000`
    - TypeScript (Express): the new Express API (in `src/server/`) can be started during migration:
      - Install node deps: `npm install`
      - Run: `npm run start:api` (or `npm run dev:all` to start API, Vite and Electron together)
  - UI basics:
    - Set the folder path (console folder) in the Folder field and click **Init** to initialize a downloader instance for that folder.
    - Click a section (A, B, C, ...) to list games. Use **Details** to view the game's title and raw popularity data (score, votes) and **Queue** to queue it for download.
    - The UI shows the current queue and a list of recently processed tasks.
  - Persistence & files:
    - The in-memory queue is saved to `src/webui_queue.json` so queued jobs survive server restarts (Express and FastAPI variants are supported during migration).
    - Processed task history is saved to `src/webui_processed.json` and visible via the UI.
  - Server logs and per-folder downloader logs:
    - UI process logs appear in the terminal running the API process.
    - Per-folder downloader logs are written to `ROMs/vimms_downloader.log` in the target folder.

Notes:

- The Web UI is experimental and intended for local use only (binds to localhost). If you want real-time progress bars or authentication, I can add SSE/WebSocket and auth in a follow-up.
