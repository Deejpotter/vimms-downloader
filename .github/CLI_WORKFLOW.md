# CLI Workflow - Running Command-Line Scripts

> **Note**: CLI scripts have been reorganized into the `cli/` folder for better separation from the web interface.

The CLI scripts (`cli/run_vimms.py` and `cli/download_vimms.py`) are fully compatible with the console configuration system.

## What Changed

1. **CLI scripts moved to `cli/` folder** — all command-line tools are now in a dedicated directory
2. **Console folder names updated** to match Vimm's Lair system codes:
   - `GameGear` → `GG`
   - `Sega32X` → `32X`
   - `TurboGrafx16` → `TG16`
   - `TurboGrafxCD` → `TGCD`
   - `VirtualBoy` → `VB`

3. **`cli/run_vimms.py` reads `workspace_root`** from `vimms_config.json`:
   - The runner looks for console folders at the configured `workspace_root` location
   - No need to pass `--src` if `workspace_root` is set in the config

4. **Priority-based processing** — consoles are downloaded in priority order (lower number = first)

## Usage Examples

### View planned downloads (dry-run)

```bash
python cli/run_vimms.py --dry-run
```

### Start downloading all active consoles

```bash
python cli/run_vimms.py
```

### Download a single console

```bash
python cli/run_vimms.py --folder DS
```

### Download with specific options

```bash
# Extract files after download
python cli/run_vimms.py --folder GBA --extract-files

# Enable interactive prompts
python cli/run_vimms.py --folder GBA --prompt

# Both options together
python cli/run_vimms.py --folder GBA --extract-files --prompt
```

**Note**: Both `run_vimms.py` and `download_vimms.py` are non-interactive by default. Use `--prompt` to enable interactive mode when needed.

## Configuration

Edit `vimms_config.json` to control:

- Which consoles to download (`active: true/false`)
- Download priority order (`priority: 1, 2, 3, ...`)
- Per-console settings (extraction, prompts, etc.)
- Global defaults (section priority, network delays, etc.)

See [README_VIMMS.md](../README_VIMMS.md) for full configuration documentation.

## Console Detection

The downloader automatically detects the console type from folder names. Folder names should match the Vimm system codes for best results (see the table in README_VIMMS.md).

If you have existing folders with different names (e.g., `GameGear` instead of `GG`), the detection will still work via the CONSOLE_MAP, but it's recommended to rename folders to match the Vimm codes for clarity.
