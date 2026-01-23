# Vimm's Lair Downloader — Games Workspace

Brief: a small toolset to download and clean ROMs from Vimm's Lair.

Getting started ✅

- Dependencies are listed in `requirements_vimms.txt`. Install them in a venv:

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash / WSL on Windows
pip install --upgrade pip
pip install -r requirements_vimms.txt
```

Running downloads 🔧

- Preferred entrypoint: `run_vimms.py`.
  - Example: `python run_vimms.py --folder "G:/My Drive/Games/PS2"`
  - Pass `--no-prompt` to run non-interactively.
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
- `clean_filenames.py` — filename cleaner; runs on the folder it's executed within
- `requirements_vimms.txt` — pip requirements used by the downloader

If you'd like any behavior changed (different fuzzy threshold, different matching rules,
or automated cleaning of filenames before detection), I can implement that quickly.

---
Updated: added fuzzy-local-file detection and `--no-detect-existing` flag; consolidated
canonical scripts at workspace root.
