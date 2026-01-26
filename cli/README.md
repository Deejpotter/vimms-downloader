# CLI Tools

Command-line scripts for downloading and managing ROMs from Vimm's Lair.

## Main Scripts

### `download_vimms.py`

Canonical downloader - fetches games from Vimm's Lair.

```bash
# Download to specific folder (non-interactive by default)
python cli/download_vimms.py --folder "H:/Games/DS"

# With extraction
python cli/download_vimms.py --folder "H:/Games/DS" --extract-files

# With interactive prompts (if needed)
python cli/download_vimms.py --folder "H:/Games/DS" --prompt
```

### `run_vimms.py`

Orchestrator - processes multiple consoles using `vimms_config.json`.

```bash
# Preview what will run
python cli/run_vimms.py --dry-run

# Run all active consoles in priority order (non-interactive by default)
python cli/run_vimms.py

# Run single console
python cli/run_vimms.py --folder "DS"

# With interactive prompts (if needed)
python cli/run_vimms.py --prompt
```

See [vimms_config.json](../vimms_config.json) for configuration.

## Utility Scripts

### `clean_filenames.py`

Cleans ROM filenames by removing tags, region codes, and version numbers.

```bash
# Preview changes
python cli/clean_filenames.py --dry-run

# Apply changes
python cli/clean_filenames.py
```

### `fix_folder_names.py`

Infers console types from file extensions and proposes folder renames.

```bash
python cli/fix_folder_names.py
```

## Configuration

All CLI scripts read from `vimms_config.json` in the repository root:

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

See [README_VIMMS.md](../README_VIMMS.md) for complete console names and options.

## Runtime Root Resolution

`run_vimms.py` resolves the workspace root in this order:

1. CLI flag: `--src <path>`
2. Config: `vimms_config.json` → `workspace_root`
3. Config (legacy): `vimms_config.json` → `src`
4. Script location: repository root (parent of `cli/`)

**Note**: After reorganization, `run_vimms.py` now correctly uses the repository root for finding `vimms_config.json` and `download_vimms.py`, even though it's located in the `cli/` subdirectory.
