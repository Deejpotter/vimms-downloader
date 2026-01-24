# Vimm's Lair Downloader — Runner & Config

This repository contains a canonical Python downloader (archived under `archive/`) and a new Desktop UI (Electron + Vite + React + TypeScript) in active development under `src/`.

This README documents the Python runner and configuration options (kept in `archive/`) for reference. The TypeScript desktop UI and Express API are the recommended developer flow going forward; see the top-level `README.md` for how to run the dev stack (`npm run dev:all`).

## Key points

- `run_vimms.py` is a top-level runner that can iterate your workspace's console folders and invoke the canonical downloader for each one.
- A single top-level config file `vimms_config.json` (workspace root) controls which folders to process and provides defaults.
- Two config styles are supported (backwards-compatible):
  - Legacy: `folders.whitelist` / `folders.blacklist` (lists of folder names)
  - Preferred: `folders` mapping where each key is a folder name and value is the per-folder config object
- Per-folder file `vimms_folder.json` inside a console folder is still supported as a fallback when top-level mapping is not present.

## `vimms_config.json` (recommended)

Place `vimms_config.json` at the workspace root (`g:/My Drive/Games/vimms_config.json`). Example structure:

```json
{
  "folders": {
    "DS": {
      "active": true,
      "extract_files": true
    },
    "GBA": {
      "active": false
    }
  },

  "defaults": {
    "detect_existing": true,
    "pre_scan": true
  },

  "limits": {
    "index_max_files": 20000,
    "match_threshold": 0.75
  },

  "network": {
    "delay_between_page_requests": [1, 2],
    "delay_between_downloads": [1, 2],
    "retry_delay": 5,
    "max_retries": 3
  }
}
```

Per-folder settings available in the top-level `folders` mapping (short list):

- `active` (bool): whether to process this folder. `false` → skip.
- `extract_files` (bool): whether archives should be extracted after download.
- `no_prompt` (bool): skip interactive prompts for that folder.
- `delete_duplicates` / `yes_delete` (bool): duplicate handling behavior.

Notes:

- The runner prefers the top-level `folders` mapping. If a folder is not present there, it will look for a `vimms_folder.json` file inside that folder as a fallback.
- Legacy `whitelist`/`blacklist` arrays are still accepted and are automatically converted into per-folder entries internally.

## Runner usage (`run_vimms.py`)

- Dry-run (lists planned runs, safe):

```bash
python "g:/My Drive/Games/run_vimms.py"
```

- Apply (actually invoke downloads for selected folders):

```bash
python "g:/My Drive/Games/run_vimms.py" --apply
```

- Run a single folder immediately:

```bash
python "g:/My Drive/Games/run_vimms.py" --folder "G:/My Drive/Games/GBA" --apply --no-prompt  # legacy example; use no flag for non-interactive by default or --prompt to enable prompts
```

## Per-folder file fallback

If you prefer to keep per-folder JSON files (for manual editing inside each folder), create `vimms_folder.json` inside the folder with the same keys as the top-level mapping:

```json
{
  "active": true,
  "extract_files": false,
  "no_prompt": true
}
```

The runner will use the top-level mapping if present; otherwise it will fall back to this file.

## Tips

- Use `folders` mapping for clarity and central control.
- Start with a dry-run (`--apply` omitted) to ensure you won't start downloads unexpectedly.
- Tune `limits.match_threshold` and `limits.index_max_files` if detection is too aggressive or indexing takes too long.

## Web UI (experimental)

- A minimal FastAPI-based web UI is available under `archive/` for the canonical Python implementation (requires `fastapi`, `uvicorn`, `jinja2`). During migration, a TypeScript/Express API is being developed under `src/server/`.

### Starting the UI

- Python FastAPI (legacy/canonical):
  - Activate your venv then run:

    python -m uvicorn src.webapp:app --reload --port 8000

  - On Windows you can also run the packaged uvicorn binary:

    .venv\Scripts\uvicorn.exe src.webapp:app --reload --port 8000

- TypeScript Express (migration):
  - Install node dependencies: `npm install`
  - Run the API: `npm run start:api` (Express API binds to port 3000 by default)

- The web UI can use either API depending on which you start; the desktop app (Electron) uses `VITE_API_BASE` environment variable to select the API base URL.

### What the UI provides (MVP)

- Initialize a downloader for a local folder (click **Init** after specifying the folder path).
- Browse sections (A..Z, number), view game details (title + raw popularity score & votes), and queue games for download.
- Monitor the queue and see recent processed items (success/failure timestamps).

### Persistence & files

- Queue is persisted to `src/webui_queue.json` so it survives restarts.
- Processed tasks (recent history) saved to `src/webui_processed.json`.
- Per-folder downloader logs are written to `ROMs/vimms_downloader.log` inside each target folder.

### Popularity categorization & score mode

- You can categorize downloads either by `stars` (1–5) or by raw integer `score` (0–10):
  - CLI: `scripts/categorize_by_popularity.py --mode stars|score` (use `--dry-run` first).
  - Downloader CLI: pass `--categorize-by-popularity` and `--categorize-by-popularity-mode score` to automatically move downloaded files into `ROMs/score/<n>/` or `ROMs/stars/<n>/`.

### Notes & next steps

- The current UI uses polling for queue/processed refresh; real-time progress via SSE/WebSocket is planned for a follow-up.
- The server binds to localhost only by default. If you need remote access, we should add authentication and an explicit bind option.

## License

MIT — use responsibly.
