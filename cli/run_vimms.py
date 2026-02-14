#!/usr/bin/env python3
"""
Top-level runner to invoke the canonical `download_vimms.py` for one or more folders.

Behavior summary:
- Can run a single folder via `--folder` or iterate top-level console folders when
    `--folder` is omitted.
- Uses a top-level meta-config file `vimms_config.json` (workspace root) to control
    which folders are processed and to provide defaults.
- Supports two config styles:
    - Preferred: a `folders` mapping where each key is a folder name and the value
        is a per-folder config object (recommended).
    - Legacy: `folders.whitelist` / `folders.blacklist` lists — still supported and
        automatically converted to the preferred mapping internally.
- If a top-level `folders` mapping does not define a folder, the runner falls back
    to a per-folder `vimms_folder.json` file inside the folder (if present).

Flags and precedence:
- CLI flags (explicitly passed to `run_vimms.py`) take precedence over per-folder
    settings. Top-level `folders` entries take precedence over per-folder files.

Typical usage:
        # Dry-run: list planned folders (use --dry-run)
        python run_vimms.py --dry-run

        # Default: actually invoke the downloader for selected folders (no flag required)
        python run_vimms.py

        # Run a single folder immediately
        python run_vimms.py --folder "G:/My Drive/Games/GBA" --apply --no-prompt
"""
import argparse
import subprocess
from pathlib import Path
import sys
import json
from datetime import datetime

# ROOT points to the repository root (parent of cli/)
ROOT = Path(__file__).parent.parent

# Folders to ignore when scanning workspace root for console folders
SKIP_FOLDER_NAMES = {
    '.git', '.github', '.venv', '.pytest_cache', '.vscode', 'tests', '__pycache__', 'scripts', 'saves'
}


def resolve_target(folder_arg: str, root: Path) -> Path:
    """Resolve a user-supplied folder argument to an absolute Path.

    Behavior:
    - If `folder_arg` is an absolute path, return its resolved Path.
    - If `root / folder_arg` exists, return that (so users can pass `DS`).
    - If `cwd / folder_arg` exists, return that (support running from other CWDs).
    - Try a case-insensitive match among `root` children.
    - Otherwise attempt to resolve the argument relative to the current cwd.

    Raises SystemExit(1) with a helpful message when the final path is missing.
    """
    raw = folder_arg
    p = Path(raw)

    # Absolute path provided
    if p.is_absolute():
        target = p.expanduser().resolve()
    else:
        # Prefer workspace-root subfolder (allows `--folder DS`)
        cand = root / raw
        if cand.exists() and cand.is_dir():
            target = cand.resolve()
        else:
            # Next prefer cwd-relative
            cwd_cand = Path.cwd() / raw
            if cwd_cand.exists() and cwd_cand.is_dir():
                target = cwd_cand.resolve()
            else:
                # Try case-insensitive name match under workspace root
                target = None
                try:
                    for child in root.iterdir():
                        if child.is_dir() and child.name.lower() == raw.lower():
                            target = child.resolve()
                            break
                except FileNotFoundError:
                    # root may not exist (defensive)
                    pass

                if target is None:
                    # Fallback: try to resolve the original path relative to cwd
                    try:
                        target = Path(raw).expanduser().resolve()
                    except Exception:
                        target = Path(raw).expanduser()

    if not target.exists() or not target.is_dir():
        # Provide a helpful listing of similar folder names under workspace root
        suggestions = []
        try:
            for child in root.iterdir():
                if child.is_dir() and raw.lower() in child.name.lower():
                    suggestions.append(child.name)
        except Exception:
            pass

        print(f"Target folder does not exist: {target}")
        if suggestions:
            print("Did you mean one of:")
            for s in suggestions:
                print(f"  - {s}")
        raise SystemExit(1)

    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run Vimm's Lair downloader for a specific folder or iterate workspace folders")
    parser.add_argument('--folder', '-f', required=False,
                        help='Path to the target folder or a workspace subfolder name (e.g. "DS"); omit to iterate folders from config')
    # By default the runner will not prompt (non-interactive). Use --prompt to allow prompts.
    parser.add_argument('--no-prompt', action='store_true', help='Skip interactive prompts in the target script (explicit)')
    parser.add_argument('--prompt', action='store_true', help='Allow interactive prompts in the target script (overrides defaults)')
    parser.add_argument('--delete-duplicates', action='store_true', help='Enable prompt-based removal of redundant local files when duplicates are found')
    parser.add_argument('--yes-delete', action='store_true', help='Auto-confirm deletion of duplicates (moves duplicates to scripts/deleted_duplicates/)')
    parser.add_argument('--extract-files', action='store_true', help='Extract archive files after download (forwarded to downloader)')
    parser.add_argument('--python', default=sys.executable, help='Python executable to use')
    parser.add_argument('--config', '-c', help='Path to vimms_config.json (default: workspace root or --src location)')
    parser.add_argument('--dry-run', action='store_true', help='List planned folders without invoking downloads (default: invoke downloads)')
    # Reporting options
    parser.add_argument('--report', action='store_true', help='Generate a progress report per console instead of running downloads')
    parser.add_argument('--report-format', choices=['json', 'csv'], default='json', help='Report file format (default: json)')
    parser.add_argument('--report-aggregate', action='store_true', help='Also write an overall summary under reports/overall_progress.json')
    parser.add_argument('--categorize-by-rating', action='store_true', help='Forward --categorize-by-rating to the downloader (organize by Vimm rating)')
    parser.add_argument('--src', help='Path to the project/src root where the downloader script and config live (useful when running the runner from a different CWD)')

    args = parser.parse_args(argv)
    def _read_progress_summary(folder: Path):
        """Read progress info for a console folder to report what's already done.

        Looks for a download_progress.json inside a preferred ROMs subfolder,
        falling back to the folder root if needed. Returns a small dict with
        counts and last_section information. All fields are safe-defaulted.
        """
        progress_paths = [folder / 'ROMs' / 'download_progress.json', folder / 'download_progress.json']
        prog = {
            'completed': 0,
            'failed': 0,
            'last_section': None,
        }
        for p in progress_paths:
            try:
                if p.exists():
                    with open(p, 'r', encoding='utf-8') as f:
                        j = json.load(f)
                    # handle both list or dict formats defensively
                    compl = j.get('completed', []) if isinstance(j, dict) else []
                    failed = j.get('failed', []) if isinstance(j, dict) else []
                    prog['completed'] = len(compl) if isinstance(compl, list) else int(compl or 0)
                    prog['failed'] = len(failed) if isinstance(failed, list) else int(failed or 0)
                    prog['last_section'] = j.get('last_section') if isinstance(j, dict) else None
                    break
            except Exception:
                # If the file is malformed or locked, just ignore and keep defaults
                pass
        return prog

    # Determine runtime_root early so we can use it for config resolution
    # Precedence: CLI --src > config.workspace_root > config.src > script ROOT
    # Note: We need to load config first to check workspace_root, creating a chicken-egg situation.
    # Solution: Load config from --config path if absolute, otherwise try both ROOT and --src locations.
    
    cfg_path_arg = Path(args.config) if args.config else None
    
    # If --config is relative and --src is provided, prefer config from --src location
    if args.src and (cfg_path_arg is None or not cfg_path_arg.is_absolute()):
        src_config = Path(args.src) / 'vimms_config.json'
        if src_config.exists():
            cfg_path = src_config
        elif cfg_path_arg and cfg_path_arg.exists():
            cfg_path = cfg_path_arg
        else:
            cfg_path = src_config  # Use src path even if doesn't exist
    elif cfg_path_arg:
        cfg_path = cfg_path_arg
    else:
        cfg_path = ROOT / 'vimms_config.json'
    
    # Load config for whitelist/blacklist
    import json
    cfg = {}
    if cfg_path.exists():
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception as e:
            print('Warning: could not read config:', e)

    cfg_folders = cfg.get('folders', {}) or {}

    # Backwards-compatible support:
    # - If cfg_folders contains 'whitelist' or 'blacklist' keys, treat it as the older format.
    # - Otherwise treat cfg_folders as a mapping of folder-name -> per-folder-config.
    whitelist = set()
    blacklist = set()
    per_folder_map = {}

    if isinstance(cfg_folders, dict) and (('whitelist' in cfg_folders) or ('blacklist' in cfg_folders)):
        whitelist = set(cfg_folders.get('whitelist', []))
        blacklist = set(cfg_folders.get('blacklist', []))
        # Convert legacy whitelist/blacklist into top-level per-folder mapping
        # so downstream logic can uniformly consult `per_folder_map`.
        for name in whitelist:
            per_folder_map.setdefault(str(name), {})
            per_folder_map[str(name)]['active'] = True
        for name in blacklist:
            per_folder_map.setdefault(str(name), {})
            per_folder_map[str(name)]['active'] = False
    else:
        # Interpret each key as a folder name mapping to per-folder config
        for k, v in cfg_folders.items():
            # Skip comment/metadata keys beginning with underscore and legacy whitelist/blacklist
            if k.startswith('_') or k in ('whitelist', 'blacklist'):
                continue
            per_folder_map[str(k)] = v if isinstance(v, dict) else {}

    # If a single folder was provided, just run that one
    # Determine runtime_root: CLI --src > config.workspace_root > config.src > workspace ROOT
    cfg_workspace_root = None
    cfg_src_root = None
    try:
        # Prefer 'workspace_root' (where the game folders live), fall back to 'src' (where scripts live)
        cfg_workspace_root = cfg.get('workspace_root')
        cfg_src_root = cfg.get('src') or cfg.get('src_root') or cfg.get('project_root')
    except Exception:
        pass

    # Resolve runtime_root with precedence: CLI --src > workspace_root > src/project_root > script ROOT
    if args.src:
        runtime_root = Path(args.src).resolve()
    elif cfg_workspace_root:
        runtime_root = Path(cfg_workspace_root).resolve()
    elif cfg_src_root:
        runtime_root = Path(cfg_src_root).resolve()
    else:
        runtime_root = ROOT

    if args.folder:
        target = resolve_target(args.folder, runtime_root)
        run_list = [target]
    else:
        # If a top-level `folders` mapping is present, prefer using it as authoritative
        run_candidates = []
        try:
            if per_folder_map:
                # Use per-folder entries to resolve paths (support `path` override)
                for idx, (name, pf) in enumerate(per_folder_map.items()):
                    if pf.get('active') is False:
                        continue
                    # If a specific path is provided in the per-folder config, use it
                    pf_path = pf.get('path')
                    if pf_path:
                        p = Path(pf_path).expanduser()
                        if not p.is_absolute():
                            p = runtime_root / p
                    else:
                        # Default: runtime_root / name
                        p = runtime_root / name

                    # Try to resolve case-insensitive if missing
                    if not p.exists():
                        try:
                            for child in runtime_root.iterdir():
                                if child.is_dir() and child.name.lower() == name.lower():
                                    p = child
                                    break
                        except Exception:
                            pass

                    if p.exists() and p.is_dir():
                        run_candidates.append((p, idx))
                    else:
                        # Skip but note for visibility
                        print(f"  • Skipping configured folder '{name}': path not found ({p})")
            else:
                # No per-folder mapping: iterate workspace folders but skip obvious non-console dirs
                for idx, child in enumerate(sorted(runtime_root.iterdir())):
                    if not child.is_dir():
                        continue
                    name = child.name
                    # Skip hidden/system and known non-console folders
                    if name.startswith('.') or name.lower() in SKIP_FOLDER_NAMES:
                        continue

                    # Fall back to whitelist/blacklist behavior when present
                    if whitelist and name not in whitelist:
                        continue
                    if name in blacklist:
                        continue

                    run_candidates.append((child, idx))
        except Exception as e:
            print('Error listing workspace folders:', e)
            raise SystemExit(1)

        # Determine folder priorities. Precedence: per-folder mapping 'priority' >
        # top-level defaults 'folder_priority' > unspecified (treated as large).
        top_defaults = cfg.get('defaults', {}) if isinstance(cfg, dict) else {}
        default_folder_priority = top_defaults.get('folder_priority')

        def _folder_priority(name, idx):
            # Check per-folder map first
            pf = per_folder_map.get(name, {})
            if 'priority' in pf and isinstance(pf.get('priority'), int):
                return (pf.get('priority'), idx)
            # Next, check top-level default
            if isinstance(default_folder_priority, int):
                return (default_folder_priority, idx)
            # Unspecified => low priority (large number)
            return (10**6, idx)

        # Sort candidates by priority (ascending), then by original index to preserve order
        sorted_candidates = sorted(run_candidates, key=lambda ci: _folder_priority(ci[0].name, ci[1]))
        run_list = [c[0] for c in sorted_candidates]

    # Decide which canonical downloader to invoke.
    # Default behavior: use the repo-local canonical downloader (in cli/ folder)
    # because `--src` typically points at a data/download root (e.g., H:/Games).
    # If the user explicitly requests using external scripts in the src (`--use-external-scripts`),
    # use the canonical under runtime_root and fail if missing.
    # Always use the repository-local canonical downloader (in cli/ folder).
    canonical = ROOT / 'cli' / 'download_vimms.py'
    if not canonical.exists():
        print(f"Repository-local canonical downloader not found at: {canonical}")
        raise SystemExit(1)

    # Read top-level defaults from the config (if present)
    top_defaults = cfg.get('defaults', {}) if isinstance(cfg, dict) else {}

    # Decide default prompting behavior. The user's request: runner should NOT prompt by
    # default unless the config explicitly allows prompting. We'll support a top-level
    # `defaults.allow_prompt` boolean (False => non-interactive by default).
    default_allow_prompt = bool(top_defaults.get('allow_prompt', False))
    default_no_prompt = not default_allow_prompt

    # Build the set of common forwarded flags (these act as global defaults; per-folder
    # config and CLI flags may override on a per-folder basis).
    global_forward = {}
    # Determine global no-prompt with precedence: CLI (--prompt/--no-prompt) > top-level default
    if args.prompt:
        global_forward['no_prompt'] = False
    elif args.no_prompt:
        global_forward['no_prompt'] = True
    else:
        global_forward['no_prompt'] = default_no_prompt

    global_forward['extract_files'] = args.extract_files
    global_forward['delete_duplicates'] = args.delete_duplicates
    global_forward['yes_delete'] = args.yes_delete
    # Forward rating categorization flag to downloader
    global_forward['categorize_by_rating'] = bool(args.categorize_by_rating)

    # Dry-run when --dry-run is passed; otherwise invoke downloads by default
    if args.dry_run:
        print('Dry-run mode: planned runs:')
        for t in run_list:
            name = t.name
            # Prefer top-level per-folder mapping when present
            top_cfg = per_folder_map.get(name) if 'per_folder_map' in locals() else None
            pf_file = t / 'vimms_folder.json'
            parts = []
            if top_cfg is not None:
                # show summary of top-level config keys we care about
                parts.append('top')
                if top_cfg.get('active') is False:
                    parts.append('inactive')
                else:
                    parts.append('active')
                if 'extract_files' in top_cfg:
                    parts.append(f"extract_files={bool(top_cfg.get('extract_files'))}")
            elif pf_file.exists():
                try:
                    with open(pf_file, 'r', encoding='utf-8') as f:
                        pfj = json.load(f)
                    parts.append('file')
                    parts.append('active' if pfj.get('active', True) else 'inactive')
                except Exception:
                    parts.append('file:error')
            else:
                parts.append('no config')

            print(f'  - {t}  [{", ".join(parts)}]')
        print('\nRun without --dry-run to actually invoke downloads (or pass --folder to run a single folder).')
        return

    total_consoles = len(run_list)
    if total_consoles:
        print(f"\nPlanned consoles to process: {total_consoles}")
        print('-' * 80)

    overall_before_completed = 0
    overall_after_completed = 0

    # If reporting is requested, generate reports and exit
    if args.report:
        try:
            # Local import to avoid importing when running as pure subprocess runner
            from download_vimms import VimmsDownloader, SECTIONS, detect_console_from_folder
        except Exception as e:
            print('Error importing downloader for reporting:', e)
            raise SystemExit(1)

        overall = []
        all_rows = []
        reports_dir = ROOT / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)

        for idx, t in enumerate(run_list, start=1):
            console = detect_console_from_folder(t) or t.name
            roms_dir = t / 'ROMs'
            if not roms_dir.exists():
                roms_dir.mkdir(parents=True, exist_ok=True)

            # Read progress
            pre = _read_progress_summary(t)

            # Build a downloader for listing and local detection
            dl = VimmsDownloader(str(roms_dir), system=console, detect_existing=True, pre_scan=True, extract_files=False)
            # Build local index for presence detection
            dl._build_local_index()

            # Fetch all available games across sections
            all_games = []
            print('\n' + '=' * 80)
            print(f"Collecting game list for {console} ({idx}/{len(run_list)})...")
            for s in SECTIONS:
                games = dl.get_game_list_from_section(s)
                if games:
                    all_games.extend(games)

            # Determine status per game
            completed_ids = set()
            failed_ids = set()
            try:
                # Load the full progress JSON if present
                for pp in [roms_dir / 'download_progress.json', t / 'download_progress.json']:
                    if pp.exists():
                        with open(pp, 'r', encoding='utf-8') as f:
                            pj = json.load(f)
                        completed_ids = set(pj.get('completed', []) or [])
                        # failed can be a list of dicts; accept both list of ids or list of entries
                        raw_failed = pj.get('failed', []) or []
                        if raw_failed and isinstance(raw_failed[0], dict):
                            failed_ids = {x.get('game_id') for x in raw_failed if isinstance(x, dict) and x.get('game_id')}
                        else:
                            failed_ids = set(raw_failed)
                        break
            except Exception:
                pass

            rows = []
            present_local = 0
            for g in all_games:
                gid = g.get('game_id')
                name = g.get('name')
                if gid in completed_ids:
                    status = 'completed'
                elif gid in failed_ids:
                    status = 'failed'
                else:
                    # Detect local presence with fuzzy matching
                    matches = dl.find_all_matching_files(name)
                    if matches:
                        status = 'present_local'
                        present_local += 1
                    else:
                        status = 'pending'
                rows.append({'game_id': gid, 'name': name, 'status': status, 'section': g.get('section')})

            totals = {
                'console': console,
                'available': len(all_games),
                'completed': len(completed_ids),
                'failed': len(failed_ids),
                'present_local': present_local,
                'pending': sum(1 for r in rows if r['status'] == 'pending'),
                'downloaded_including_local': len(completed_ids) + present_local,
                'last_section': pre.get('last_section'),
            }

            # Output per-console report
            if args.report_format == 'json':
                out_path = roms_dir / 'progress_report.json'
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump({'summary': totals, 'entries': rows}, f, indent=2, ensure_ascii=False)
            else:
                import csv
                out_path = roms_dir / 'progress_report.csv'
                with open(out_path, 'w', encoding='utf-8', newline='') as f:
                    w = csv.writer(f)
                    w.writerow(['game_id', 'name', 'section', 'status'])
                    for r in rows:
                        w.writerow([r['game_id'], r['name'], r.get('section'), r['status']])

            print(f"Report written: {out_path}")
            print(f"Summary: available={totals['available']} completed={totals['completed']} present_local={totals['present_local']} pending={totals['pending']} failed={totals['failed']} downloaded_total={totals['downloaded_including_local']}")

            overall.append(totals)
            # Accumulate for combined CSV output
            for r in rows:
                row_copy = dict(r)
                row_copy['console'] = console
                all_rows.append(row_copy)

        if args.report_aggregate:
            agg = {
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'consoles': overall,
                'totals': {
                    'available': sum(c['available'] for c in overall),
                    'completed': sum(c['completed'] for c in overall),
                    'failed': sum(c['failed'] for c in overall),
                    'present_local': sum(c['present_local'] for c in overall),
                    'pending': sum(c['pending'] for c in overall),
                    'downloaded_including_local': sum(c['downloaded_including_local'] for c in overall),
                }
            }
            agg_path = reports_dir / 'overall_progress.json'
            with open(agg_path, 'w', encoding='utf-8') as f:
                json.dump(agg, f, indent=2, ensure_ascii=False)
            print(f"\nAggregate summary written: {agg_path}")

            # Also write a combined CSV of all entries across consoles
            try:
                import csv
                combined_csv = reports_dir / 'all_entries.csv'
                with open(combined_csv, 'w', encoding='utf-8', newline='') as f:
                    w = csv.writer(f)
                    w.writerow(['console', 'game_id', 'name', 'section', 'status'])
                    for r in all_rows:
                        w.writerow([r.get('console'), r.get('game_id'), r.get('name'), r.get('section'), r.get('status')])
                print(f"Combined entries CSV written: {combined_csv}")
            except Exception as e:
                print(f"Could not write combined CSV: {e}")

        return

    # Execute downloads sequentially
    for idx, t in enumerate(run_list, start=1):
        # Per-folder config priority:
        # 1) top-level `vimms_config.json` under `folders` mapping (preferred)
        # 2) fallback to a per-folder `vimms_folder.json` file if present
        per_cfg = {}
        pf_top = per_folder_map.get(t.name) if 'per_folder_map' in locals() else None
        if pf_top is not None:
            per_cfg = pf_top
        else:
            # Fallback to per-folder file
            per_cfg_path = t / 'vimms_folder.json'
            if per_cfg_path.exists():
                try:
                    with open(per_cfg_path, 'r', encoding='utf-8') as f:
                        per_cfg = json.load(f)
                except Exception as e:
                    print(f' Warning: could not read per-folder config for {t.name}: {e}')

        # Check 'active' property (default True)
        if per_cfg.get('active') is False:
            print(f"Skipping {t} (per-folder config: active=false)")
            continue

        # Compute flags for this folder. Precedence: CLI args > per-folder config > top-level defaults
        flags = []

        # Effective prompting behavior for this folder
        # Check explicit CLI overrides first
        if args.prompt:
            effective_no_prompt = False
        elif args.no_prompt:
            effective_no_prompt = True
        else:
            # Next check per-folder config for explicit keys. Support both `no_prompt` (bool)
            # and `allow_prompt` (bool) for backwards/forward compatibility.
            if 'no_prompt' in per_cfg:
                effective_no_prompt = bool(per_cfg.get('no_prompt'))
            elif 'allow_prompt' in per_cfg:
                effective_no_prompt = not bool(per_cfg.get('allow_prompt'))
            else:
                # Fall back to global default decided from top-level `defaults`.
                effective_no_prompt = global_forward.get('no_prompt', default_no_prompt)

        # The downloader uses --prompt to enable prompts; by default it's non-interactive
        # So we only add --prompt if we want prompting enabled (effective_no_prompt=False)
        if not effective_no_prompt:
            flags.append('--prompt')

        # extract_files: per-folder true -> add flag; CLI --extract-files overrides
        if global_forward.get('extract_files'):
            flags.append('--extract-files')
        elif per_cfg.get('extract_files'):
            flags.append('--extract-files')

        # Section priority: allow per-folder override or top-level config 'section_priority'
        # Accept lists in config; forward as comma-separated string to downloader
        section_priority = None
        # top-level section priority may be provided as cfg['section_priority'] or in defaults
        top_section_priority = None
        if isinstance(cfg, dict):
            top_section_priority = cfg.get('section_priority') or top_defaults.get('section_priority')

        if 'section_priority' in per_cfg:
            section_priority = per_cfg.get('section_priority')
        elif top_section_priority:
            section_priority = top_section_priority

        if section_priority:
            # Accept either list or comma-separated string
            if isinstance(section_priority, list):
                sp_str = ','.join(str(s).upper() for s in section_priority)
            else:
                sp_str = str(section_priority)
            flags.append('--section-priority')
            flags.append(sp_str)

        if global_forward.get('delete_duplicates'):
            flags.append('--delete-duplicates')
        elif per_cfg.get('delete_duplicates'):
            flags.append('--delete-duplicates')

        if global_forward.get('yes_delete'):
            flags.append('--yes-delete')
        elif per_cfg.get('yes_delete'):
            flags.append('--yes-delete')

        # Forward categorize-by-rating to downloader when requested globally or per-folder
        if global_forward.get('categorize_by_rating'):
            flags.append('--categorize-by-rating')
        elif per_cfg.get('categorize_by_rating'):
            flags.append('--categorize-by-rating')

        # Pre-run summary (what's already done)
        pre = _read_progress_summary(t)
        overall_before_completed += pre.get('completed', 0)
        last_sec = pre.get('last_section') or '-'
        print('\n' + '=' * 80)
        print(f"Console {idx}/{total_consoles}: {t.name}")
        print(f"  Already completed: {pre['completed']}  |  Failed: {pre['failed']}  |  Last section: {last_sec}")
        print('-' * 80)

        cmd = [args.python, str(canonical), '--folder', str(t)] + flags
        # If the canonical downloader lives in a different directory add src to ensure it uses the same project root
        if args.src:
            cmd.extend(['--src', str(args.src)])
        print('Running:', ' '.join(f'"{c}"' if ' ' in c else c for c in cmd))
        ret = subprocess.call(cmd)
        if ret != 0:
            print(f"Downloader exited with code {ret} for folder {t}")
            # continue to next folder rather than aborting all
            continue

        # Post-run summary (what changed)
        post = _read_progress_summary(t)
        added = max(0, post.get('completed', 0) - pre.get('completed', 0))
        overall_after_completed += post.get('completed', 0)
        print(f"\nSummary for {t.name}:")
        print(f"  New downloads this run: {added}")
        print(f"  Total completed now:   {post.get('completed', 0)}")
        print(f"  Total failed recorded: {post.get('failed', 0)}")
        print('-' * 80)

    if total_consoles:
        print('\n' + '=' * 80)
        print('All consoles processed')
        print('=' * 80)
        print(f"Consoles run: {total_consoles}")
        if overall_after_completed >= overall_before_completed:
            print(f"New downloads across all consoles: {overall_after_completed - overall_before_completed}")
        print("Tip: You can re-run with --dry-run to preview planned folders, or --folder <name> to run one.")


if __name__ == '__main__':
    main()
