# Vimm's Lair Downloader — Runner & Config

This repository contains a canonical downloader (`download_vimms.py`) and a small runner (`run_vimms.py`) to manage downloads for multiple console folders (DS, GBA, SNES, etc.).

This README highlights the runner and configuration options added to control which folders are processed and to tune downloader behavior.

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
python "g:/My Drive/Games/run_vimms.py" --folder "G:/My Drive/Games/GBA" --apply --no-prompt
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

## License

MIT — use responsibly.
