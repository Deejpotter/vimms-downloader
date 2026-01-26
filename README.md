# Vimm's Lair Downloader — Games Workspace

Brief: a small toolset to download and clean ROMs from Vimm's Lair.

**Two ways to use:**

- 🌐 **Web Interface** — Modern React UI with progressive scanning and download queue → [Jump to Web UI](#quick-start---web-interface-)
- 🔧 **Command Line** — Batch processing and automation → [Jump to CLI](#command-line-usage-) or see [cli/README.md](cli/README.md)

---

## Quick Start - Web Interface 🌐

**Modern React + Tailwind CSS UI** with progressive workspace scanning and real-time download queue!

**1. Set up virtual environment and install dependencies:**

```bash
# Create virtual environment
python -m venv .venv

# Activate it (Windows Git Bash / WSL)
source .venv/Scripts/activate

# OR activate it (Windows CMD)
.venv\Scripts\activate.bat

# OR activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**2. Run the web interface:**

```bash
# Make sure venv is activated first!
python src/webapp.py
```

**3. Open browser:**

- Navigate to: **<http://127.0.0.1:8000>**

**4. Use the interface:**

- Enter your workspace root path (e.g., `C:\ROMs` or `H:/Games`)
- Index builds automatically when workspace is set (watch yellow indicator in header)
- Consoles appear progressively as they're scanned (real-time updates)
- Index resumes from completed consoles on restart (only re-indexes incomplete ones)
- Select a console to browse sections (A-Z, 0-9, #)
- Click sections to view games with local presence detection and ratings
- Click **Add to Queue** on games you want to download
- Downloads run in background worker thread
- Check the floating **Queue** button (bottom-right) for download status and progress

**5. Stop the server:**

- Press `Ctrl+C` in terminal

---

### Frontend Development Mode

**Only needed if you want to modify the React UI with hot reload:**

```bash
# Terminal 1: Flask backend (API server)
python src/webapp.py

# Terminal 2: Vite dev server (React hot reload)
cd frontend
yarn install  # first time only
yarn dev
```

- Development server: <http://localhost:5173> (hot reload enabled)
- Flask API: <http://127.0.0.1:8000/api/>*
- Vite automatically proxies API calls to Flask

**Building for production:**

```bash
cd frontend
yarn build
```

This compiles React app to `src/webui_static/dist` which Flask serves automatically.

See [frontend/README.md](frontend/README.md) for detailed frontend development documentation.

---

## Command Line Usage 🔧

All CLI tools are organized in the `cli/` folder. See [cli/README.md](cli/README.md) for detailed documentation.

Getting started ✅

- Dependencies are listed in `requirements.txt`. Install them in a venv:

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash / WSL on Windows
pip install --upgrade pip
pip install -r requirements.txt
```

**Configuration with `vimms_config.json`:**

- Create `vimms_config.json` in the repository root to configure your workspace and console folders:

```json
{
  "workspace_root": "H:/Games",
  "folders": {
    "DS": {"priority": 1, "active": true, "extract_files": true},
    "GBA": {"priority": 2, "active": true},
    "PS2": {"priority": 3, "active": true}
  }
}
```

- See [README_VIMMS.md](README_VIMMS.md) for complete console names and configuration options.
- See [cli/README.md](cli/README.md) for CLI usage examples.

Running downloads 🔧

- Preferred entrypoint: `cli/run_vimms.py` (processes all active consoles in priority order).
  - Preview what will run: `python cli/run_vimms.py --dry-run`
  - Run all active consoles: `python cli/run_vimms.py` (non-interactive by default)
  - Run single console: `python cli/run_vimms.py --folder "DS"`
  - Enable interactive prompts: `python cli/run_vimms.py --prompt`
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

- `cli/` — Command-line tools (see [cli/README.md](cli/README.md))
  - `download_vimms.py` — canonical downloader
  - `run_vimms.py` — orchestrator for multiple consoles
  - `clean_filenames.py` — filename cleaner
  - `fix_folder_names.py` — console folder name fixer
- `src/` — Web interface
  - `webapp.py` — Flask backend
  - `webui_static/` — React frontend build output
- `frontend/` — React source code
- `downloader_lib/` — Shared parsing/fetching modules (see [downloader_lib/README.md](downloader_lib/README.md))
  - `fetch.py` — Network fetching utilities
  - `parse.py` — HTML parsing utilities
  - Used by both CLI and web interface
- `utils/` — Shared utilities (filenames, constants)
- `tests/` — Unit tests
- `vimms_config.json` — Console configuration
- `requirements.txt` — Python dependencies

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
