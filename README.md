# Vimm's Lair Downloader — Games Workspace

Brief: a small toolset to download and clean ROMs from Vimm's Lair.

Getting started ✅

- Dependencies are listed in `requirements.txt`. Install them in a venv:

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash / WSL on Windows
pip install --upgrade pip
pip install -r requirements.txt
```

Running downloads 🔧

- Preferred entrypoint: `run_vimms.py`.
  - Example: `python run_vimms.py --folder "G:/My Drive/Games/PS2"`
  - By default runner/downloader are non-interactive. Use `--prompt` to allow interactive prompts.
  - Pass `--no-detect-existing` to disable fuzzy-local-file detection (force downloads).
    - Pass `--delete-duplicates` to enable prompting to remove redundant local files when multiple matches are found.
    - Add `--yes-delete` to auto-confirm deletion of duplicates (use with caution; duplicates are moved to `scripts/deleted_duplicates/` timestamped folders).

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

- Experimental Web UI (FastAPI) — local web interface to browse sections, view popularity, queue games and monitor processed tasks.
  - Start the server (preferred, cross-shell):
    - Activate venv and run: `python -m uvicorn src.webapp:app --reload --port 8000`
    - Or on Windows use the bundled script: `.venv\Scripts\uvicorn.exe src.webapp:app --reload --port 8000`
  - By default the UI listens on http://127.0.0.1:8000/ (open in your browser).
  - UI basics:
    - Set the folder path (console folder) in the Folder field and click **Init** to initialize a downloader instance for that folder.
    - Click a section (A, B, C, ...) to list games. Use **Details** to view the game's title and raw popularity data (score, votes) and **Queue** to queue it for download.
    - The UI shows the current queue and a list of recently processed tasks.
  - Persistence & files:
    - The in-memory queue is saved to `src/webui_queue.json` so queued jobs survive server restarts.
    - Processed task history is saved to `src/webui_processed.json` and visible via the UI.
  - Server logs and per-folder downloader logs:
    - UI process logs appear in the terminal running uvicorn.
    - Per-folder downloader logs are written to `ROMs/vimms_downloader.log` in the target folder.

Notes:
- The Web UI is experimental and intended for local use only (binds to localhost). If you want real-time progress bars or authentication, I can add SSE/WebSocket and auth in a follow-up.

