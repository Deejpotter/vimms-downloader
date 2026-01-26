#!/usr/bin/env python3
"""
Scan top-level folders in the workspace, detect which console they contain (by extensions
and by looking inside .zip files), and rename folders when the detected console name
doesn't match the folder name. Operates safely: won't overwrite existing targets and
will skip folders that look non-console (e.g., scripts, saves).

Usage: python fix_folder_names.py [--root ROOT] [--yes]
  --root: workspace root (defaults to current working dir)
  --yes: perform renames; otherwise runs in dry-run mode and prints proposed changes
"""
from pathlib import Path
import zipfile
import argparse
import os
import shutil
import tempfile
from collections import Counter, defaultdict

ROM_EXT_TO_CONSOLE = {
    'nds': 'DS',
    'gba': 'GBA',
    'gb': 'GB',
    'gbc': 'GBC',
    'nes': 'NES',
    'sfc': 'SNES',
    'smc': 'SNES',
    'n64': 'N64',
    'z64': 'N64',
    'v64': 'N64',
    'iso': 'PS1_PS2',
    'bin': 'PS1_PS2',
    'cue': 'PS1_PS2',
    'cso': 'PS1_PS2',
    'gba.zip': 'GBA',
    'zip': None,  # zip is inspected
}

SKIP_FOLDER_NAMES = {
    'scripts', 'saves', '__pycache__', 'game card files', 'gamecard files', 'downloads'
}

def detect_console_in_file(path: Path):
    name = path.name.lower()
    if path.is_dir():
        return None
    ext = path.suffix.lower().lstrip('.')
    if ext in ROM_EXT_TO_CONSOLE and ROM_EXT_TO_CONSOLE[ext]:
        return ROM_EXT_TO_CONSOLE[ext]
    if ext == 'zip':
        # inspect zip contents for inner extensions
        try:
            with zipfile.ZipFile(path, 'r') as z:
                counts = Counter()
                for zi in z.namelist():
                    inner_ext = Path(zi).suffix.lower().lstrip('.')
                    if inner_ext in ROM_EXT_TO_CONSOLE and ROM_EXT_TO_CONSOLE[inner_ext]:
                        counts[ROM_EXT_TO_CONSOLE[inner_ext]] += 1
                if counts:
                    return counts.most_common(1)[0][0]
        except Exception:
            return None
    return None


def detect_console_in_tree(folder: Path, max_files=2000):
    # Prefer scanning a `ROMs` subfolder when present (users keep ROMs there)
    search_root = folder / 'ROMs'
    if not search_root.exists() or not search_root.is_dir():
        search_root = folder

    # Walk folder shallowly to count matches; limit scanning to avoid long runs
    counts = Counter()
    total_checked = 0
    for root, dirs, files in os.walk(search_root):
        for f in files:
            p = Path(root) / f
            console = detect_console_in_file(p)
            if console:
                counts[console] += 1
            total_checked += 1
            if total_checked >= max_files:
                break
        if total_checked >= max_files:
            break
    return counts


def choose_console_from_counts(counts: Counter):
    if not counts:
        return None
    total = sum(counts.values())
    console, cnt = counts.most_common(1)[0]
    # Heuristic: require at least 3 matches OR >50% of matched files
    if cnt >= 3 or (cnt / total) > 0.5:
        return console
    return None


def safe_rename(src: Path, dst: Path):
    # On Windows, renaming only case may be non-trivial; use temp rename when needed.
    if src.samefile(dst) if dst.exists() else False:
        return False, 'samefile'
    if dst.exists():
        return False, 'exists'
    try:
        # If only case differs on same filesystem, attempt a two-step rename
        if src.exists() and src.parent == dst.parent and src.name.lower() == dst.name.lower():
            tmp = src.parent / (dst.name + '.tmp.rename')
            src.rename(tmp)
            tmp.rename(dst)
        else:
            src.rename(dst)
        return True, 'renamed'
    except Exception as e:
        return False, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', '-r', help='Workspace root (default cwd)', default='.')
    ap.add_argument('--yes', action='store_true', help='Perform renames (default: dry-run)')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print('Root does not exist:', root)
        return 1

    top_folders = [p for p in root.iterdir() if p.is_dir()]
    proposed = []

    for folder in sorted(top_folders):
        name_lower = folder.name.strip().lower()
        if name_lower in SKIP_FOLDER_NAMES:
            # skip known non-console folders
            continue
        # detect console by content
        counts = detect_console_in_tree(folder)
        detected = choose_console_from_counts(counts)
        if not detected:
            # no clear console detected
            continue
        # If folder name already matches (case-insensitive) the detected console, skip
        if folder.name.strip().lower() == detected.lower():
            continue

        # propose rename to detected
        dst = folder.parent / detected
        proposed.append((folder, detected, dst, counts))

    if not proposed:
        print('No folder renames proposed.')
        return 0

    print('Proposed renames:')
    for src, detected, dst, counts in proposed:
        print(f'  {src} -> {dst}  (detected counts: {dict(counts)})')

    if not args.yes:
        print('\nDry-run mode. Re-run with --yes to apply changes.')
        return 0

    print('\nApplying renames...')
    applied = []
    skipped = []
    for src, detected, dst, counts in proposed:
        ok, msg = safe_rename(src, dst)
        if ok:
            applied.append((src, dst))
            print(f' RENAMED: {src} -> {dst}')
        else:
            skipped.append((src, dst, msg))
            print(f' SKIPPED: {src} -> {dst}  ({msg})')

    print('\nSummary:')
    print(' Applied:', len(applied))
    print(' Skipped:', len(skipped))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
