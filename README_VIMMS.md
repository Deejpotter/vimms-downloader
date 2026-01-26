# Vimm's Lair Downloader — Runner & Config

This repository contains a canonical downloader (`download_vimms.py`) and a small runner (`run_vimms.py`) to manage downloads for multiple console folders (DS, GBA, SNES, etc.).

This README highlights the runner and configuration options added to control which folders are processed and to tune downloader behavior.

## Quick Start

1. **Configure your workspace** — Edit `vimms_config.json` in the repository root:
   - Set `workspace_root` to your game folders location (e.g., `"H:\\Games"`)
   - Configure console folders under `folders` (see example below)
   - Adjust priorities to control download order

2. **Test with dry-run**:

   ```bash
   python run_vimms.py --dry-run
   ```

3. **Start downloads**:

   ```bash
   python run_vimms.py
   ```

## Key points

- `run_vimms.py` is a top-level runner that can iterate your workspace's console folders and invoke the canonical downloader for each one.
- A single top-level config file `vimms_config.json` (repository root) controls which folders to process and provides defaults.
- The config `workspace_root` setting points to where your game folders live (e.g., `H:\Games`)
- Console folders are processed in priority order (lower number = higher priority)
- Two config styles are supported (backwards-compatible):
  - Legacy: `folders.whitelist` / `folders.blacklist` (lists of folder names)
  - Preferred: `folders` mapping where each key is a folder name and value is the per-folder config object
- Per-folder file `vimms_folder.json` inside a console folder is still supported as a fallback when top-level mapping is not present.

## `vimms_config.json` (recommended)

Place `vimms_config.json` at the repository root. Example structure:

```json
{
  "workspace_root": "H:\\Games",
  
  "folders": {
    "DS": {
      "active": true,
      "extract_files": true,
      "priority": 1
    },
    "GBA": {
      "active": true,
      "priority": 2
    },
    "N64": {
      "active": true,
      "priority": 3
    }
  },

  "defaults": {
    "detect_existing": true,
    "pre_scan": true,
    "section_priority": ["L", "M", "K", "O"]
  },

  "limits": {
    "index_max_files": 20000,
    "match_threshold": 0.65
  },

  "network": {
    "delay_between_page_requests": [1, 2],
    "delay_between_downloads": [1, 2],
    "retry_delay": 5,
    "max_retries": 3
  }
}
```

### Console Folder Names

Use these folder names to match Vimm's Lair system codes:

| Folder Name | Vimm Code | Console |
|-------------|-----------|---------|
| DS | DS | Nintendo DS |
| GBA | GBA | Game Boy Advance |
| N64 | N64 | Nintendo 64 |
| GBC | GBC | Game Boy Color |
| GB | GB | Game Boy |
| SNES | SNES | Super Nintendo |
| NES | NES | Nintendo Entertainment System |
| GC | GameCube | Nintendo GameCube |
| Wii | Wii | Nintendo Wii |
| WiiWare | WiiWare | Nintendo WiiWare |
| 3DS | 3DS | Nintendo 3DS |
| VB | VB | Virtual Boy |
| PS1 | PS1 | PlayStation |
| PS2 | PS2 | PlayStation 2 |
| PSP | PSP | PlayStation Portable |
| Genesis | Genesis | Sega Genesis |
| SMS | SMS | Sega Master System |
| GG | GG | Game Gear |
| SegaCD | SegaCD | Sega CD |
| 32X | 32X | Sega 32X |
| Saturn | Saturn | Sega Saturn |
| Dreamcast | Dreamcast | Sega Dreamcast |
| Xbox | Xbox | Xbox |
| Xbox360 | Xbox360 | Xbox 360 |
| Atari2600 | Atari2600 | Atari 2600 |
| Atari5200 | Atari5200 | Atari 5200 |
| Atari7800 | Atari7800 | Atari 7800 |
| Jaguar | Jaguar | Atari Jaguar |
| JaguarCD | JaguarCD | Atari Jaguar CD |
| Lynx | Lynx | Atari Lynx |
| TG16 | TG16 | TurboGrafx-16 |
| TGCD | TGCD | TurboGrafx-CD |
| CDi | CDi | CD-i |

Per-folder settings available in the top-level `folders` mapping (short list):

- `active` (bool): whether to process this folder. `false` → skip.
- `priority` (int): download order (lower = earlier). Useful for prioritizing favorite consoles.
- `extract_files` (bool): whether archives should be extracted after download.
- `allow_prompt` (bool): enable interactive prompts for that folder (default: non-interactive).
- `delete_duplicates` / `yes_delete` (bool): duplicate handling behavior.

Notes:

- The runner prefers the top-level `folders` mapping. If a folder is not present there, it will look for a `vimms_folder.json` file inside that folder as a fallback.
- Legacy `whitelist`/`blacklist` arrays are still accepted and are automatically converted into per-folder entries internally.
- Both `run_vimms.py` and `download_vimms.py` are non-interactive by default. Use `--prompt` to enable interactive mode.

## Runner usage (`run_vimms.py`)

- Dry-run (lists planned runs, safe):

```bash
python cli/run_vimms.py --dry-run
```

- Run all active folders (non-interactive by default):

```bash
python cli/run_vimms.py
```

- Run a single folder:

```bash
python cli/run_vimms.py --folder DS
```

- Enable interactive prompts:

```bash
python cli/run_vimms.py --prompt
```

- Run with custom workspace location:

```bash
python cli/run_vimms.py --src "H:\Games" --dry-run
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
