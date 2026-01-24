"""Categorize downloaded games into star buckets based on Vimm popularity.

Usage:
    python scripts/categorize_by_popularity.py --folder G:/Games/DS --dry-run
    python scripts/categorize_by_popularity.py --folder G:/Games/DS --apply
"""
import argparse
from pathlib import Path
import sys
# Ensure repo root on sys.path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shutil
from src.download_vimms import VimmsDownloader
from src.metadata import get_game_popularity, score_to_stars
from typing import Optional

parser = argparse.ArgumentParser(description='Categorize downloaded ROMs by popularity stars')
parser.add_argument('--folder', '-f', required=True, help='Path to console folder (contains ROMs subfolder)')
parser.add_argument('--cache', help='Optional path to metadata cache (default: ROMs/metadata_cache.json)')
parser.add_argument('--dry-run', action='store_true', help='Show actions without moving files')
parser.add_argument('--apply', action='store_true', help='Actually move files into star buckets')
parser.add_argument('--mode', choices=['stars','score'], default='stars', help='Categorization mode: stars (default) or score (integer)')
args = parser.parse_args()

root = Path(args.folder)
if not root.exists() or not root.is_dir():
    print(f"Folder not found: {root}")
    raise SystemExit(1)

roms_dir = root / 'ROMs'
if not roms_dir.exists() or not roms_dir.is_dir():
    roms_dir = root

# Default cache path under ROMs
cache_path = Path(args.cache) if args.cache else roms_dir / 'metadata_cache.json'

# Load downloader so we can use presence detection helpers
dl = VimmsDownloader(str(roms_dir), system='UNKNOWN', detect_existing=True, pre_scan=True)
# Ensure we build the local index
dl._build_local_index()

# Read progress file
progress_file = roms_dir / 'download_progress.json'
if not progress_file.exists():
    print(f"No progress file found at {progress_file}; nothing to categorize")
    raise SystemExit(1)

import json
with open(progress_file, 'r', encoding='utf-8') as f:
    progress = json.load(f)
completed = progress.get('completed', []) or []

moved = []
failed = []

for game_id in completed:
    url = f"https://vimm.net/vault/{game_id}"
    pop = get_game_popularity(url, session=dl.session, cache_path=cache_path, logger=getattr(dl, 'logger', None))
    if not pop:
        failed.append((game_id, 'no popularity data'))
        continue
    score, votes = pop
    # Determine destination label based on mode
    if args.mode == 'score':
        bucket = int(round(score))
        dst_label = f"score/{bucket}"
    else:
        stars = score_to_stars(score)
        dst_label = f"stars/{stars}"

    # find local files matching game name(s)
    found_files = []
    for k, entries in (dl.local_index or {}).items():
        for p in entries:
            if str(game_id) in p.name or str(game_id) in k:
                found_files.append(p)

    # If not found, just attempt fuzzy lookup by calling find_all_matching_files on a best-effort name
    if not found_files:
        # Try extracting title from the URL or cache entry
        # Fallback: try scanning all entries and pick ones that have same mediaId in filename
        # For now we'll call find_all_matching_files for every cached key; this may be slow but acceptable for MVP
        # Note: the progress file doesn't store the game name; we can't robustly map ID->name without fetching page. Fetch page now.
        try:
            from metadata import _parse_popularity_from_html
            # fetch page title
            resp = dl.session.get(url, timeout=10)
            resp.raise_for_status()
            # Try to extract title tag
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            title_el = soup.find('title')
            title = title_el.text.strip() if title_el else ''
        except Exception:
            title = ''
        if title:
            found_files = dl.find_all_matching_files(title)

    if not found_files:
        failed.append((game_id, 'no local file found'))
        continue

    # Move files into bucket determined by mode
    dst_dir = roms_dir / dst_label
    if not args.apply:
        print(f"[DRY] Would move {found_files} -> {dst_dir}  (score={score}, votes={votes})")
        moved.append((game_id, found_files, dst_label))
    else:
        dst_dir.mkdir(parents=True, exist_ok=True)
        for p in found_files:
            try:
                target = dst_dir / p.name
                shutil.move(str(p), str(target))
                print(f"Moved: {p} -> {target}  (score={score}, votes={votes})")
                moved.append((game_id, [target], dst_label))
            except Exception as e:
                print(f"Failed to move {p}: {e}")
                failed.append((game_id, str(e)))

print('\nSummary:')
print(f'  Processed: {len(completed)}')
print(f'  Moved (or would move): {len(moved)}')
print(f'  Failed: {len(failed)}')
if failed:
    for f in failed:
        print(f'   - {f}')
