#!/usr/bin/env python3
"""
Vimm's Lair Vault Downloader (canonical runner)

This script downloads ROMs from Vimm's Lair (https://vimm.net/vault/).

Usage notes:
- This file is the canonical downloader and is intended to live at the workspace root
    (e.g., `g:/My Drive/Games/download_vimms.py`). Use `run_vimms.py` as a convenience
    wrapper to call this script against any target folder.
- It auto-detects the console type from the target folder name (e.g., `DS`, `PS1`).

Configuration note:
- The downloader reads an optional workspace-level `vimms_config.json` file (if present)
    to obtain defaults for delays, retries, indexing behavior, and whether to extract
    archives by default. When running via `run_vimms.py`, per-folder settings declared
    in the top-level `vimms_config.json` are preferred; per-folder `vimms_folder.json`
    files are used as a fallback when no top-level mapping exists for a folder.

Key features:
- Auto-detects console based on the target folder name (DS, PS1, N64, etc.)
- Can be run for any folder using `--folder <path>` or run interactively from inside a console folder
- Tracks progress in a JSON file (resume capability)
- Detects local ROM files by fuzzy name matching and skips duplicates (useful when filenames vary)
    - Toggle local detection with `--no-detect-existing`
- Skips games already present in the progress file
- Respects rate limits and uses randomized delays to be courteous to the server
- Automatic extraction and filename cleanup after download
"""

import os
import re
import json
import time
import random
import requests
import zipfile
import shutil
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Optional
import difflib
import argparse
from datetime import datetime
import urllib3
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from downloader_lib.fetch import fetch_section_page, fetch_game_page
from downloader_lib.parse import parse_games_from_section, resolve_download_form

# Disable SSL warnings
urllib3.disable_warnings()

# Configuration
BASE_URL = "https://vimm.net"
VAULT_BASE = f"{BASE_URL}/vault"
DOWNLOAD_BASE = "https://dl2.vimm.net"

# Mapping of common folder names to Vimm's Lair system codes
CONSOLE_MAP = {
    'DS': 'DS',
    'NDS': 'DS',
    'NES': 'NES',
    'SNES': 'SNES',
    'N64': 'N64',
    'GC': 'GameCube',
    'GAMECUBE': 'GameCube',
    'WII': 'Wii',
    'WIIWARE': 'WiiWare',
    'GB': 'GB',
    'GAMEBOY': 'GB',
    'GBC': 'GBC',
    'GBA': 'GBA',
    'PS1': 'PS1',
    'PSX': 'PS1',
    'PLAYSTATION': 'PS1',
    'PS2': 'PS2',
    'PS3': 'PS3',
    'PSP': 'PSP',
    'GENESIS': 'Genesis',
    'MEGADRIVE': 'Genesis',
    'SMS': 'SMS',
    'MASTERSYSTEM': 'SMS',
    'SATURN': 'Saturn',
    'DREAMCAST': 'Dreamcast',
    'DC': 'Dreamcast',
    'XBOX': 'Xbox',
    'ATARI2600': 'Atari2600',
    'ATARI7800': 'Atari7800',
}

# Default archive extension when Content-Disposition filename is missing.
# Many disc-based systems on Vimm use .7z archives.
SYSTEM_DEFAULT_ARCHIVE_EXT = {
    'Dreamcast': '.7z',
    'Saturn': '.7z',
    'PS2': '.7z',
    'PS1': '.7z',
    'GameCube': '.7z',
    'Wii': '.7z',
}

SECTIONS = ['number', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

from utils.constants import ROM_EXTENSIONS, ARCHIVE_EXTENSIONS, USER_AGENTS  # centralized constants
from utils.filenames import clean_filename as util_clean_filename, normalize_for_match as util_normalize_for_match

# Timing configuration (in seconds)
DELAY_BETWEEN_PAGE_REQUESTS = (1, 2)  # Random delay between list page requests
DELAY_BETWEEN_DOWNLOADS = (1, 2)      # Random delay between actual downloads
RETRY_DELAY = 5                      # Delay before retrying failed download
MAX_RETRIES = 3                       # Maximum number of retry attempts


class VimmsDownloader:
    """Main downloader class for Vimm's Lair"""
    
    def __init__(self, download_dir: str, system: str, progress_file: str = "download_progress.json", detect_existing: bool = True, delete_duplicates: bool = False, auto_confirm_delete: bool = False, pre_scan: bool = True, extract_files: Optional[bool] = None, section_priority_override: Optional[List[str]] = None, project_root: Optional[str] = None, allow_prompt: bool = False, categorize_by_popularity: bool = False, categorize_by_popularity_mode: str = 'stars'):
        """
        Initialize the downloader
        
        Args:
            download_dir: Directory to save downloaded files
            system: Console system code (e.g., 'DS', 'PS1', 'N64')
            progress_file: JSON file to track download progress
            project_root: Optional path to the repository or "src" root where config files live
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.system = system
        self.progress_file = Path(download_dir) / progress_file
        self.progress = self._load_progress()
        # Whether to attempt to detect local copies of ROMs and skip downloads
        self.detect_existing = detect_existing
        # Whether to offer to delete duplicate local files (prompts per-game)
        self.delete_duplicates = delete_duplicates
        # If True, confirmations to delete duplicates are auto-accepted
        self.auto_confirm_delete = auto_confirm_delete
        # Whether to pre-scan the download directory once and build an index of local files
        # This makes repeated presence checks much faster when iterating large game lists.
        self.pre_scan = pre_scan
        # Will be populated by `_build_local_index()` when pre_scan is enabled
        self.local_index = None  # type: Optional[Dict[str, List[Path]]]
        self._local_index_keys = None  # cached list of normalized keys
        # Project root (useful when running scripts from a separate working directory)
        self.project_root = Path(project_root).resolve() if project_root else Path(__file__).parent

        # Load optional top-level config (vimms_config.json) to override defaults
        cfg_path = self.project_root / 'vimms_config.json'
        cfg = {}
        if cfg_path.exists():
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}

        # Whether to extract archive files after download.
        # Priority: explicit `extract_files` argument > config file > default (DS=True)
        cfg_extract = cfg.get('defaults', {}).get('extract_files', None)
        if extract_files is None:
            if cfg_extract is None:
                self.extract_files = (str(system).upper() == 'DS')
            else:
                self.extract_files = bool(cfg_extract)
        else:
            self.extract_files = bool(extract_files)

        # Whether to categorize downloaded files into star buckets by popularity
        cfg_cat = cfg.get('defaults', {}).get('categorize_by_popularity', None)
        if categorize_by_popularity is None:
            self.categorize_by_popularity = bool(cfg_cat) if cfg_cat is not None else False
        else:
            self.categorize_by_popularity = bool(categorize_by_popularity)

        # Categorization mode: 'stars' or 'score'
        cfg_cat_mode = cfg.get('defaults', {}).get('categorize_by_popularity_mode', None)
        if categorize_by_popularity_mode is None:
            self.categorize_by_popularity_mode = cfg_cat_mode if cfg_cat_mode in ('stars', 'score') else 'stars'
        else:
            self.categorize_by_popularity_mode = categorize_by_popularity_mode if categorize_by_popularity_mode in ('stars', 'score') else 'stars'
        # Keep the inverse property for compatibility with older naming in code paths
        self.keep_archives = not self.extract_files

        # Network/delay and limit overrides
        net = cfg.get('network', {})
        self.delay_between_page_requests = tuple(net.get('delay_between_page_requests', DELAY_BETWEEN_PAGE_REQUESTS))
        self.delay_between_downloads = tuple(net.get('delay_between_downloads', DELAY_BETWEEN_DOWNLOADS))
        self.retry_delay = net.get('retry_delay', RETRY_DELAY)
        self.max_retries = net.get('max_retries', MAX_RETRIES)

        limits = cfg.get('limits', {})
        self.index_max_files = int(limits.get('index_max_files', 20000))
        self.match_threshold = float(limits.get('match_threshold', 0.75))

        self.session = requests.Session()
        # Optional override for section ordering (list of section codes, e.g., ['D','L','C'])
        self.section_priority_override = section_priority_override
        # Whether to allow interactive prompts inside the downloader (default False)
        self.allow_prompt = bool(allow_prompt)
        # Set up a per-download-directory logger to capture detailed events
        try:
            log_path = self.download_dir / 'vimms_downloader.log'
            self.logger = logging.getLogger(f'VimmsDownloader:{self.download_dir}')
            # Avoid adding duplicate handlers when reusing the same logger
            if not self.logger.handlers:
                handler = RotatingFileHandler(str(log_path), maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
                fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
                handler.setFormatter(fmt)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        except Exception:
            # Logging should never block downloader operation
            self.logger = None

    def __del__(self):
        """Cleanup logging handlers to avoid file locks (important for tests/temporary dirs)."""
        try:
            if getattr(self, 'logger', None):
                for h in list(self.logger.handlers):
                    try:
                        h.close()
                        self.logger.removeHandler(h)
                    except Exception:
                        pass
        except Exception:
            pass
        
    def _load_progress(self) -> Dict:
        """Load progress from JSON file"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'completed': [],
            'failed': [],
            'last_section': None,
            'total_downloaded': 0
        }
    
    def _save_progress(self):
        """Save progress to JSON file"""
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress, f, indent=2, ensure_ascii=False)
    
    def _get_random_user_agent(self) -> str:
        """Return a random user agent"""
        return random.choice(USER_AGENTS)
    
    def _random_delay(self, delay_range: tuple):
        """Sleep for a random amount of time within the given range"""
        delay = random.uniform(delay_range[0], delay_range[1])
        time.sleep(delay)
    
    def _clean_filename(self, filename: str) -> str:
        """Delegate to the canonical cleaning utility."""
        return util_clean_filename(filename)
    
    def _extract_and_cleanup(self, archive_path: Path):
        """
        Extract archive contents to the same folder and clean up
        
        Args:
            archive_path: Path to the downloaded archive file
        """
        try:
            print(f"  📦 Extracting archive...")
            
            # Determine archive type and extract
            suffix = archive_path.suffix.lower()
            extracted_files = []
            if suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    # Extract all files to download directory
                    zip_ref.extractall(self.download_dir)
                    extracted_files = zip_ref.namelist()
            elif suffix == '.7z':
                try:
                    import py7zr  # type: ignore
                except Exception:
                    print(f"    ⚠️  Skipping extraction (.7z) — 'py7zr' not installed. Keep archive or install py7zr to enable extraction.")
                    return
                with py7zr.SevenZipFile(archive_path, mode='r') as z:
                    z.extractall(path=self.download_dir)
                    try:
                        extracted_files = list(z.getnames())  # may not always be available
                    except Exception:
                        extracted_files = []
            else:
                print(f"    ⚠️  Skipping extraction (not a ZIP file)")
                return
            
            print(f"  ✓ Extracted {len(extracted_files)} file(s)")
            
            # Delete the archive
            archive_path.unlink()
            print(f"  🗑️  Deleted archive: {archive_path.name}")
            
            # Find and delete "Vimm's Lair.txt" if it exists
            vimms_txt = self.download_dir / "Vimm's Lair.txt"
            if vimms_txt.exists():
                vimms_txt.unlink()
                print(f"  🗑️  Deleted: Vimm's Lair.txt")
            
            # Find and clean up any single-file folders
            # (e.g., if extracted into a folder with just the ROM file)
            for item in self.download_dir.iterdir():
                if item.is_dir():
                    # Check if folder contains only 1-2 files (likely just ROM and maybe readme)
                    contents = list(item.iterdir())
                    
                    # Look for ROM files in the folder (use centralized extensions list)
                    rom_extensions = ROM_EXTENSIONS
                    rom_files = [f for f in contents if f.suffix.lower() in rom_extensions]
                    
                    if rom_files:
                        # Move ROM files to parent directory with cleaned names
                        for rom_file in rom_files:
                            # Clean the filename
                            cleaned_name = self._clean_filename(rom_file.name)
                            dest = self.download_dir / cleaned_name
                            
                            # Avoid overwriting if file already exists
                            if not dest.exists():
                                shutil.move(str(rom_file), str(dest))
                                if cleaned_name != rom_file.name:
                                    print(f"  📁 Moved & cleaned: {rom_file.name} → {cleaned_name}")
                                else:
                                    print(f"  📁 Moved: {rom_file.name}")
                        
                        # Delete the now-empty (or nearly empty) folder
                        try:
                            shutil.rmtree(item)
                            print(f"  🗑️  Deleted folder: {item.name}")
                        except:
                            # Folder might not be empty, that's okay
                            pass
            
            # Also clean filenames of any ROM files directly in the download directory
            rom_extensions = ROM_EXTENSIONS
            for item in self.download_dir.iterdir():
                if item.is_file() and item.suffix.lower() in rom_extensions:
                    cleaned_name = self._clean_filename(item.name)
                    if cleaned_name != item.name:
                        new_path = self.download_dir / cleaned_name
                        if not new_path.exists():
                            item.rename(new_path)
                            print(f"  ✨ Cleaned filename: {item.name} → {cleaned_name}")
            
        except zipfile.BadZipFile:
            print(f"  ⚠️  Archive appears corrupted, keeping file for manual inspection")
        except Exception as e:
            print(f"  ⚠️  Extraction error: {e}")
            print(f"     Keeping archive for manual extraction")
    
    def get_game_list_from_section(self, section: str) -> List[Dict[str, str]]:
        """
        Get list of games from a specific section (A-Z or number)
        Handles pagination automatically.
        
        Args:
            section: Section identifier (A, B, C, etc., or 'number')
            
        Returns:
            List of dictionaries with game info (name, page_url, game_id)
        """
        games = []
        page_num = 1
        
        print(f"\n📋 Fetching game list for section '{section}'...")
        
        while True:
            try:
                response = fetch_section_page(self.session, self.system, section, page_num)
                games_on_page = parse_games_from_section(response.text, section)
                
                if not games_on_page:
                    break
                
                games.extend(games_on_page)
                
                soup = BeautifulSoup(response.content, 'html.parser')
                next_link = soup.find('a', text=re.compile(r'Next', re.IGNORECASE))
                if not next_link:
                    break

                print(f"  ✓ Page {page_num}: Found {len(games_on_page)} games")
                page_num += 1
                self._random_delay(self.delay_between_page_requests)
                
            except Exception as e:
                print(f"  ✗ Error fetching section '{section}' page {page_num}: {e}")
                break
        
        print(f"  ✓ Total: Found {len(games)} games in section '{section}'")
        
        return games

    def _normalize_for_match(self, s: str) -> str:
        """Delegate normalization to shared utility for consistent behavior."""
        return util_normalize_for_match(s)

    def _build_local_index(self):
        """Build an in-memory index of local ROM filenames to avoid repeated directory scans.

        The index maps a normalized filename (from `_normalize_for_match(_clean_filename(name))`)
        to a list of Path objects that have that normalized key. This is used by
        `find_all_matching_files` and `is_game_present` when present to speed up matching.
        """
        rom_extensions = [
            '.nds', '.sav', '.n64', '.z64', '.v64', '.iso', '.bin', '.cue',
            '.gba', '.gbc', '.gb', '.smc', '.sfc', '.nes', '.gcm', '.wbfs'
        ]

        index: Dict[str, List[Path]] = {}

        try:
            # Walk the download directory recursively to capture files stored in
            # subfolders (common for large collections where users keep one folder
            # per game). Limit the total number of files inspected to avoid very
            # long indexing on huge archives/folders.
            total_checked = 0
            max_files = 20000

            for root, dirs, files in os.walk(self.download_dir):
                # Index directories by name as well (helps detect per-title folders)
                for d in dirs:
                    p = Path(root) / d
                    key = self._normalize_for_match(self._clean_filename(d))
                    index.setdefault(key, []).append(p)

                for f in files:
                    item = Path(root) / f
                    ext = item.suffix.lower()

                    # Include archives when we are keeping archives (i.e., not extracting files)
                    if ext in ('.zip', '.7z') and not self.extract_files:
                        key = self._normalize_for_match(self._clean_filename(item.name))
                        index.setdefault(key, []).append(item)
                        total_checked += 1
                        if total_checked >= self.index_max_files:
                            break
                        continue

                    if ext in rom_extensions:
                        key = self._normalize_for_match(self._clean_filename(item.name))
                        index.setdefault(key, []).append(item)
                        total_checked += 1
                        if total_checked >= self.index_max_files:
                            break

                if total_checked >= self.index_max_files:
                    break

        except Exception:
            # If anything goes wrong building the index, fall back to per-item checks
            self.local_index = None
            self._local_index_keys = None
            return

        self.local_index = index
        self._local_index_keys = list(index.keys())


    def is_game_present(self, game_name: str) -> Optional[Path]:
        """Check for a likely local match for `game_name`.

        Why this exists: users often already have ROMs but with slightly different
        names (different punctuation, region tags, underscores, or minor title
        differences). Rather than redownloading duplicates, we attempt to detect
        an existing file and skip the download.

        Matching strategy (in order):
        1. Normalize both the candidate name and local filenames using
           `_normalize_for_match` and `_clean_filename` (so region tags are removed and
           formatting is standardized).
        2. If the normalized strings contain each other (A in B or B in A), treat it as a match.
        3. Otherwise, compute a fuzzy sequence ratio and accept matches >= 0.75.

        Returns:
            Path to the matching local file, or None if nothing matches.
        """

        rom_extensions = list(ROM_EXTENSIONS)
        # When keeping archives, consider archives as present matches too
        if not self.extract_files:
            rom_extensions = rom_extensions + list(ARCHIVE_EXTENSIONS)

        # Use the cleaned, normalized title as the comparison target
        target = self._normalize_for_match(self._clean_filename(game_name))

        # If we built an index, use it (much faster). Otherwise, fall back to directory scan.
        if self.local_index is not None and self._local_index_keys is not None:
            # Check direct containment against keys first, then fuzzy match
            for key in self._local_index_keys:
                if target in key or key in target:
                    # Return the first file found for this key
                    return self.local_index[key][0]

            for key in self._local_index_keys:
                ratio = difflib.SequenceMatcher(None, target, key).ratio()
                if ratio >= self.match_threshold:
                    return self.local_index[key][0]

            return None

        # Fallback: iterate directory (original behavior)
        target = self._normalize_for_match(self._clean_filename(game_name))

        for item in self.download_dir.iterdir():
            if not item.is_file():
                continue

            if item.suffix.lower() not in rom_extensions:
                # Skip non-ROM files (saves, images, etc.)
                continue

            cand = self._normalize_for_match(self._clean_filename(item.name))

            # Direct substring containment catches simple formatting differences
            if target in cand or cand in target:
                return item

            # Fallback to a fuzzy ratio to handle small title differences
            ratio = difflib.SequenceMatcher(None, target, cand).ratio()
            if ratio >= self.match_threshold:
                return item

        return None

    def find_all_matching_files(self, game_name: str) -> List[Path]:
        """Return all local ROM files that likely match `game_name`.

        This uses the same normalization and fuzzy matching logic as
        `is_game_present` but collects all candidates rather than returning
        the first match.
        """
        rom_extensions = list(ROM_EXTENSIONS)
        if not self.extract_files:
            rom_extensions = rom_extensions + list(ARCHIVE_EXTENSIONS)

        target = self._normalize_for_match(self._clean_filename(game_name))
        matches: List[Path] = []

        # If we have a local index, use it to gather candidates
        if self.local_index is not None and self._local_index_keys is not None:
            for key in self._local_index_keys:
                if target in key or key in target:
                    matches.extend(self.local_index[key])
                    continue

            for key in self._local_index_keys:
                ratio = difflib.SequenceMatcher(None, target, key).ratio()
                if ratio >= self.match_threshold:
                    matches.extend(self.local_index[key])

            return matches

        # Fallback to directory scan (original behavior)
        for item in self.download_dir.iterdir():
            if not item.is_file() or item.suffix.lower() not in rom_extensions:
                continue

            cand = self._normalize_for_match(self._clean_filename(item.name))

            if target in cand or cand in target:
                matches.append(item)
                continue

            ratio = difflib.SequenceMatcher(None, target, cand).ratio()
            if ratio >= self.match_threshold:
                matches.append(item)

        return matches

    def _choose_preferred_file(self, files: List[Path], game_name: str) -> Path:
        """Pick the preferred file to keep from `files` for `game_name`.

        Scoring heuristic (higher is better):
        - exact normalized equality vs target (+3)
        - no parentheses/brackets in filename (+2)
        - shorter filename (+1)
        """
        target = self._normalize_for_match(self._clean_filename(game_name))

        def score(p: Path) -> int:
            s = self._normalize_for_match(self._clean_filename(p.name))
            sc = 0
            if s == target:
                sc += 3
            if '(' not in p.name and '[' not in p.name:
                sc += 2
            sc += max(0, 10 - len(p.name)) // 10  # small bonus for shorter names
            return sc

        return max(files, key=score)

    def _confirm_and_remove_duplicates(self, keep: Path, extras: List[Path]):
        """Prompt to remove `extras`, moving them to a backup folder if confirmed."""

    def _categorize_downloaded_file(self, filepath: Path, game_id: str) -> None:
        """Categorize a downloaded file into a star bucket folder based on Vimm popularity.

        Moves the file into `ROMs/stars/<n>/` where <n> is 1..5.
        """
        try:
            from src.metadata import get_game_popularity, score_to_stars
        except Exception:
            # Fallback import path
            from metadata import get_game_popularity, score_to_stars

        url = f"https://vimm.net/vault/{game_id}"
        pop = get_game_popularity(url, session=self.session, cache_path=self.download_dir / 'metadata_cache.json', logger=getattr(self, 'logger', None))
        if not pop:
            if getattr(self, 'logger', None):
                self.logger.info(f"No popularity data for {game_id}; skipping categorization")
            return
        score, votes = pop
        if self.categorize_by_popularity_mode == 'score':
            # bucket by rounded integer score (0..10)
            bucket = int(round(score))
            dst = self.download_dir / f"score/{bucket}"
            label = f"score/{bucket}"
        else:
            stars = score_to_stars(score)
            dst = self.download_dir / f"stars/{stars}"
            label = f"stars/{stars}"

        dst.mkdir(parents=True, exist_ok=True)
        target = dst / filepath.name
        try:
            shutil.move(str(filepath), str(target))
            if getattr(self, 'logger', None):
                self.logger.info(f"Categorized {filepath} -> {target} (score={score}, votes={votes})")
            else:
                print(f"  ➤ Categorized: {filepath.name} -> {label}/")
        except Exception as e:
            if getattr(self, 'logger', None):
                self.logger.exception(f"Could not move file to stars folder: {e}")
            else:
                print(f"  ✗ Could not categorize file: {e}")

        # Close and remove logger handlers for this downloader instance to avoid leaving
        # the log file locked (important for tests that use temporary directories).
        try:
            if getattr(self, 'logger', None):
                for h in list(self.logger.handlers):
                    try:
                        h.close()
                        self.logger.removeHandler(h)
                    except Exception:
                        pass
        except Exception:
            pass

    
    def get_download_url(self, game_page_url: str, game_id: str) -> Optional[str]:
        """
        Extract the download URL from a game's page
        
        Args:
            game_page_url: URL of the game's detail page
            game_id: Game ID for referer
            
        Returns:
            Download URL or None if not found
        """
        try:
            response = fetch_game_page(self.session, game_page_url)
            # Some test stubs may return objects without a .text property; prefer .text but fall back to decoding .content if needed
            page_text = getattr(response, 'text', None)
            if page_text is None and getattr(response, 'content', None) is not None:
                try:
                    page_text = response.content.decode('utf-8', errors='replace')
                except Exception:
                    page_text = str(response.content)
            return resolve_download_form(page_text, self.session, game_page_url, game_id, getattr(self, 'logger', None))
            
        except Exception as e:
            msg = f"Error getting download URL: {e}"
            print(f"    ✗ {msg}")
            if getattr(self, 'logger', None):
                self.logger.exception(msg)
            return None

    def _save_failed_response(self, game_id: str, response: requests.Response):
        """Save a small snippet of a failed HTTP response for debugging."""
        try:
            out_dir = self.download_dir / 'failed_responses'
            out_dir.mkdir(parents=True, exist_ok=True)
            # Prefer .html when content-type is text/html, otherwise save raw bytes
            ctype = response.headers.get('Content-Type', '')
            safe_id = re.sub(r'[^A-Za-z0-9_-]', '_', game_id)
            if 'text' in ctype or 'html' in ctype:
                path = out_dir / f"{safe_id}.html"
                # Write up to 256KB to avoid huge files
                text = response.text
                with open(path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(text[:256 * 1024])
            else:
                path = out_dir / f"{safe_id}.bin"
                # Write up to 256KB
                with open(path, 'wb') as f:
                    for i, chunk in enumerate(response.iter_content(chunk_size=8192)):
                        if chunk:
                            f.write(chunk)
                        # limit total
                        if f.tell() >= 256 * 1024:
                            break

            if getattr(self, 'logger', None):
                self.logger.info(f"Saved failed response for {game_id} to {path}")
        except Exception as e:
            if getattr(self, 'logger', None):
                self.logger.exception(f"Could not save failed response for {game_id}: {e}")
    
    def download_game(self, game: Dict[str, str]) -> bool:
        """
        Download a single game
        
        Args:
            game: Dictionary with game info
            
        Returns:
            True if successful, False otherwise
        """
        game_name = game['name']
        game_id = game['game_id']
        
        # Check if already recorded as downloaded; verify presence to catch manual deletions
        if game_id in self.progress['completed']:
            matches = self.find_all_matching_files(game_name)
            if matches:
                print(f"  ⏭️  Skipping '{game_name}' (already downloaded)")
                return True  # Return True but mark as "skipped" so we don't delay
            else:
                print(f"  ⚠️  Previously recorded as downloaded but no local file present; will re-download '{game_name}'")
                try:
                    self.progress['completed'].remove(game_id)
                except ValueError:
                    pass
                self._save_progress()
                # proceed with download flow
        
        print(f"\n🎮 Processing: {game_name}")
        
        # Get download URL
        print(f"  📡 Fetching download link...")
        download_url = self.get_download_url(game['page_url'], game_id)
        
        if not download_url:
            print(f"  ✗ Failed to get download URL")
            self.progress['failed'].append({
                'game_id': game_id,
                'name': game_name,
                'error': 'Could not find download URL',
                'timestamp': datetime.now().isoformat()
            })
            self._save_progress()
            return False
        
        # Attempt download with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                headers = {
                    'User-Agent': self._get_random_user_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    # Use the actual game page as Referer to match site behavior
                    'Referer': game.get('page_url') or f"{BASE_URL}/vault/{game_id}",
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate'
                }
                
                print(f"  ⬇️  Downloading (attempt {attempt}/{self.max_retries})...")
                
                response = self.session.get(
                    download_url,
                    headers=headers,
                    verify=False,
                    allow_redirects=True,
                    stream=True
                )
                
                if response.status_code != 200:
                    print(f"    ⚠️  HTTP {response.status_code}")
                    print(f"    Response headers: {dict(response.headers)}")
                    if getattr(self, 'logger', None):
                        self.logger.warning(f"HTTP {response.status_code} for {game_name} ({game_id}) on attempt {attempt} URL={download_url}")
                        # Log headers at debug level
                        self.logger.debug(f"Response headers: {dict(response.headers)}")

                    # Handle explicit rate limiting politely
                    if response.status_code == 429:
                        # Respect Retry-After header if present (seconds or HTTP date)
                        wait_seconds = None
                        ra = response.headers.get('Retry-After')
                        if ra:
                            try:
                                # If integer seconds
                                wait_seconds = int(ra)
                            except Exception:
                                # Try HTTP-date format
                                try:
                                    from email.utils import parsedate_to_datetime
                                    retry_dt = parsedate_to_datetime(ra)
                                    now = datetime.utcnow().replace(tzinfo=retry_dt.tzinfo)
                                    delta = (retry_dt - now).total_seconds()
                                    if delta > 0:
                                        wait_seconds = int(delta)
                                except Exception:
                                    wait_seconds = None
                        # Fallback/backoff: exponential based on attempt
                        if wait_seconds is None:
                            base = max(5, int(self.retry_delay))
                            wait_seconds = min(300, base * (2 ** (attempt - 1)))

                        print(f"    ⏳ Rate limited (429). Waiting {wait_seconds}s before retry...")
                        if getattr(self, 'logger', None):
                            self.logger.info(f"Rate limited for {game_name} ({game_id}); sleeping {wait_seconds}s before retry")

                        time.sleep(wait_seconds)

                        # Nudge future pacing upwards to reduce further 429s
                        try:
                            lo, hi = self.delay_between_downloads
                            lo = min(60, max(lo, 5) * 1.5)
                            hi = min(180, max(hi, lo + 1) * 1.5)
                            self.delay_between_downloads = (lo, hi)
                            if getattr(self, 'logger', None):
                                self.logger.info(f"Adjusted delay_between_downloads to {self.delay_between_downloads} after 429")
                        except Exception:
                            pass

                        continue

                    # Treat 404 as permanent (non-retriable) — save response snippet for debugging
                    if response.status_code == 404:
                        if getattr(self, 'logger', None):
                            self.logger.info(f"Non-retriable 404 for {game_name} ({game_id}); recording failure")
                        # Save response body for inspection (if present)
                        try:
                            self._save_failed_response(game_id, response)
                        except Exception:
                            pass
                        # Record failure and return
                        self.progress['failed'].append({
                            'game_id': game_id,
                            'name': game_name,
                            'error': f'HTTP {response.status_code}',
                            'response_headers': dict(response.headers),
                            'timestamp': datetime.now().isoformat()
                        })
                        self._save_progress()
                        return False

                    if attempt < self.max_retries:
                        print(f"    ⏳ Waiting {self.retry_delay}s before retry...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        raise Exception(f"HTTP {response.status_code}")
                
                # Extract filename from Content-Disposition header
                content_disp = response.headers.get('Content-Disposition', '')
                filename_match = re.findall(r'filename="([^"]*)"', content_disp)
                
                if filename_match:
                    filename = filename_match[0]
                else:
                    # Fallback filename: choose extension per system default
                    default_ext = SYSTEM_DEFAULT_ARCHIVE_EXT.get(self.system, '.zip')
                    filename = f"{game_name}{default_ext}"

                # If we are NOT extracting files (keeping archives), normalize archive filename but retain ext
                if not self.extract_files:
                    base, ext = os.path.splitext(filename)
                    # If ext is missing, apply default per system
                    if not ext:
                        ext = SYSTEM_DEFAULT_ARCHIVE_EXT.get(self.system, '.zip')
                    cleaned_base = self._clean_filename(base)
                    filename = f"{cleaned_base}{ext}"

                filepath = self.download_dir / filename
                
                # Get file size for progress tracking
                total_size = int(response.headers.get('content-length', 0))
                
                # Download with progress tracking
                downloaded = 0
                chunk_size = 8192
                last_print_time = time.time()
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress display (throttle to once per second)
                            current_time = time.time()
                            if current_time - last_print_time >= 0.5 or downloaded == total_size:
                                last_print_time = current_time
                                downloaded_mb = downloaded / (1024 * 1024)
                                
                                if total_size > 0:
                                    total_mb = total_size / (1024 * 1024)
                                    percent = (downloaded / total_size) * 100
                                    # Create progress bar
                                    bar_length = 40
                                    filled = int(bar_length * downloaded / total_size)
                                    bar = '█' * filled + '░' * (bar_length - filled)
                                    print(f"\r    [{bar}] {percent:.1f}% ({downloaded_mb:.2f}/{total_mb:.2f} MB)", end='', flush=True)
                                else:
                                    # Unknown size, just show downloaded amount with spinner
                                    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                                    spin_char = spinner[int(current_time * 10) % len(spinner)]
                                    print(f"\r    {spin_char} Downloaded: {downloaded_mb:.2f} MB", end='', flush=True)
                
                print()  # New line after progress
                
                # Verify file was actually written
                if not filepath.exists() or filepath.stat().st_size == 0:
                    raise Exception("Downloaded file is empty or missing")
                
                file_size_mb = filepath.stat().st_size / (1024 * 1024)
                print(f"  ✅ Downloaded successfully: {filename} ({file_size_mb:.2f} MB)")
                
                # Either extract & cleanup, or keep the archive for systems that support
                # playing zipped ROMs (e.g., GBA). When keeping archives we do not
                # extract or remove the archive.
                if not self.extract_files:
                    # Report cleaned archive name if needed
                    if filepath.exists():
                        file_size_mb = filepath.stat().st_size / (1024 * 1024)
                        print(f"  ✅ Saved archive: {filepath.name} ({file_size_mb:.2f} MB)")
                    else:
                        print(f"  ✅ Saved archive: {filename}")
                else:
                    # Extract the archive (original behavior)
                    self._extract_and_cleanup(filepath)
                
                # Update progress
                self.progress['completed'].append(game_id)
                self.progress['total_downloaded'] += 1
                self._save_progress()

                # Optionally categorize the downloaded file by popularity
                if self.categorize_by_popularity:
                    try:
                        self._categorize_downloaded_file(filepath, game_id)
                    except Exception:
                        if getattr(self, 'logger', None):
                            self.logger.exception(f'Failed to categorize downloaded file {filepath} for {game_id}')
                # Respect configured delay between downloads
                self._random_delay(self.delay_between_downloads)

                return True
                
            except Exception as e:
                msg = f"Download failed for {game_name} ({game_id}): {e}"
                print(f"    ✗ {msg}")
                if getattr(self, 'logger', None):
                    self.logger.exception(msg)

                # If we have a response object for debugging, attempt to save it
                try:
                    # If `response` exists in this scope and is a Response, save its body
                    if 'response' in locals() and isinstance(response, requests.Response):
                        try:
                            self._save_failed_response(game_id, response)
                        except Exception:
                            pass
                except Exception:
                    pass

                if attempt < self.max_retries:
                    print(f"    ⏳ Waiting {self.retry_delay}s before retry...")
                    time.sleep(self.retry_delay)
                else:
                    # Final failure
                    self.progress['failed'].append({
                        'game_id': game_id,
                        'name': game_name,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    self._save_progress()
                    return False
        
        return False
    
    def download_all_games(self):
        """Main method to download all games for the configured system"""
        print("=" * 80)
        print(f"Vimm's Lair {self.system} Vault Downloader")
        print("=" * 80)
        print(f"\nConsole: {self.system}")
        print(f"Download directory: {self.download_dir}")
        print(f"Progress file: {self.progress_file}")
        print(f"Previously downloaded: {len(self.progress['completed'])} games")
        print(f"Previously failed: {len(self.progress['failed'])} games")
        print("\n⚠️  IMPORTANT: This script respects Vimm's rate limits.")
        print("   Downloads are throttled to one at a time with delays.")
        print("   This process will take a long time. You can stop and resume anytime.")
        print("\n" + "=" * 80)
        
        # Interactive prompt is disabled by default. If enabled, prompt before starting.
        if getattr(self, 'allow_prompt', False):
            input("\nPress Enter to start downloading...")
        else:
            print("\n(Non-interactive run — proceeding without prompting)")
        
        start_time = datetime.now()
        total_games_processed = 0
        total_games_downloaded = 0

        # If pre-scan is enabled, build the in-memory index once to speed up detection
        if self.detect_existing and self.pre_scan:
            self._build_local_index()
            if self.local_index is not None:
                count_files = sum(len(v) for v in self.local_index.values())
                print(f"\n  ✓ Pre-scanned local files: {count_files} ROM(s) indexed for quick matching")
                # Inform user when extraction is disabled (we will keep archives)
                if not self.extract_files:
                    print(f"  ⚠️  extract_files is disabled: .zip archives will be retained and not extracted")
                
                # Rebuild progress['completed'] based on actual filesystem state
                print(f"  🔄 Rebuilding progress list based on actual files...")
                old_completed = set(self.progress.get('completed', []))
                self.progress['completed'] = []
                self._save_progress()
                removed = len(old_completed) - len(self.progress['completed'])
                if removed > 0:
                    print(f"  ✓ Cleared {removed} stale entries from progress")
        
        # Determine section order. If an override was provided (either via the
        # downloader constructor or CLI), use that ordering first and then append
        # remaining default sections in order.
        ordered_sections = []
        if self.section_priority_override is not None:
            for s in self.section_priority_override:
                if s in SECTIONS and s not in ordered_sections:
                    ordered_sections.append(s)
        
        

        for s in SECTIONS:
            if s not in ordered_sections:
                ordered_sections.append(s)

        # Find starting section if resuming (respect the ordered_sections)
        # If a section_priority_override is provided for this run, ignore the saved
        # resume point and start at the beginning of the prioritized ordering so
        # the user's requested order is applied immediately.
        start_section_idx = 0
        if not self.section_priority_override and self.progress.get('last_section'):
            try:
                start_section_idx = ordered_sections.index(self.progress['last_section'])
            except ValueError:
                pass

        # Process each section
        for section_idx, section in enumerate(ordered_sections[start_section_idx:], start=start_section_idx):
            print(f"\n{'='*80}")
            print(f"SECTION: {section} ({section_idx + 1}/{len(SECTIONS)})")
            print(f"{'='*80}")
            
            # Get list of games in this section
            games = self.get_game_list_from_section(section)
            
            if not games:
                print(f"  No games found in section '{section}', skipping...")
                continue

            # Fast-skip pre-scan: if requested, scan this section's titles against the
            # in-memory index to find the first missing title and start from there.
            # This avoids iterating and checking thousands of earlier titles one-by-one.
            section_start_idx = 0
            if self.detect_existing and self.pre_scan and self.local_index is not None:
                # Walk titles until we find the first that does NOT match any local file
                for i, g in enumerate(games):
                    matches = self.find_all_matching_files(g['name'])
                    if matches:
                        # Mark as completed (skip) if not already recorded
                        if g['game_id'] not in self.progress['completed']:
                            self.progress['completed'].append(g['game_id'])
                            self._save_progress()
                        continue

                    # Found the first missing title — start downloads at this index
                    section_start_idx = i
                    break

                # If we finished the loop without breaking, all titles were present locally
                # and we can skip the entire section
                else:
                    print(f"  ⏭️  All {len(games)} titles in section '{section}' appear present locally — skipping section")
                    # Update last_section and continue
                    self.progress['last_section'] = section
                    self._save_progress()
                    continue
            
            # Download each game (start at `section_start_idx` if we fast-skipped)
            for rel_idx, game in enumerate(games[section_start_idx:], 1):
                game_idx = section_start_idx + rel_idx
                print(f"\n[{game_idx}/{len(games)}] in section '{section}'")
                
                # Attempt to detect a local copy (fuzzy name match) before calling download_game
                if self.detect_existing:
                    matches = self.find_all_matching_files(game['name'])
                    if matches:
                        # If multiple matches, pick a preferred and optionally offer to remove extras
                        if len(matches) > 1 and self.delete_duplicates:
                            preferred = self._choose_preferred_file(matches, game['name'])
                            extras = [m for m in matches if m != preferred]
                            # Ask for confirmation before moving duplicates
                            self._confirm_and_remove_duplicates(preferred, extras)
                            found_local = preferred
                        else:
                            # Single match or no-deletion path: pick the first match
                            found_local = matches[0]

                        print(f"  ⏭️  Skipping '{game['name']}' (local file found: {found_local.name})")
                        if game['game_id'] not in self.progress['completed']:
                            self.progress['completed'].append(game['game_id'])
                            self._save_progress()
                        continue

                # Check if already downloaded before calling download_game
                was_already_downloaded = game['game_id'] in self.progress['completed']
                
                success = self.download_game(game)
                total_games_processed += 1
                
                if success and not was_already_downloaded:
                    # Only count if just downloaded (not skipped)
                    total_games_downloaded += 1
                
                # Update last section
                self.progress['last_section'] = section
                self._save_progress()
                
                # Delay between downloads (respect rate limits)
                # Skip delay if the game was already downloaded
                if game_idx < len(games) and not was_already_downloaded:  # Don't delay after last game or if skipped
                    delay = random.uniform(self.delay_between_downloads[0], self.delay_between_downloads[1])
                    print(f"\n  ⏳ Waiting {delay:.0f}s before next download (rate limit compliance)...")
                    time.sleep(delay)
            
            # Delay between sections
            if section_idx < len(SECTIONS) - 1:
                delay = random.uniform(self.delay_between_page_requests[0], self.delay_between_page_requests[1])
                print(f"\n⏸️  Section complete. Waiting {delay:.0f}s before next section...")
                time.sleep(delay)
        
        # Final summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 80)
        print("DOWNLOAD COMPLETE!")
        print("=" * 80)
        print(f"Total games processed: {total_games_processed}")
        print(f"New downloads: {total_games_downloaded}")
        print(f"Total completed: {len(self.progress['completed'])}")
        print(f"Failed downloads: {len(self.progress['failed'])}")
        print(f"Time elapsed: {duration}")
        print(f"\nFiles saved to: {self.download_dir}")
        print(f"Progress saved to: {self.progress_file}")
        
        if self.progress['failed']:
            print(f"\n⚠️  {len(self.progress['failed'])} games failed to download.")
            print("   Check the progress file for details.")


def detect_console_from_folder(folder_path: Path) -> Optional[str]:
    """
    Detect console type from folder name
    
    Args:
        folder_path: Path to the folder
        
    Returns:
        Console code for Vimm's Lair, or None if not recognized
    """
    folder_name = folder_path.name.upper()
    
    # Try exact match first
    if folder_name in CONSOLE_MAP:
        return CONSOLE_MAP[folder_name]
    
    # Try partial match (e.g., "Nintendo DS" contains "DS")
    for key, value in CONSOLE_MAP.items():
        if key in folder_name:
            return value
    
    return None


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Vimm's Lair downloader — run for a specific folder")
    parser.add_argument('--folder', '-f', help='Path to the target folder to run the downloader in (overrides auto-detect)')
    parser.add_argument('--prompt', action='store_true', help='Allow interactive prompts (default: non-interactive)')
    parser.add_argument('--section-priority', type=str, help='Comma-separated section order (e.g. "D,L,C") to prioritize specific sections first')
    parser.add_argument('--no-detect-existing', action='store_true', help='Do not attempt to detect local ROM files and skip them')
    parser.add_argument('--no-pre-scan', action='store_true', help='Do not pre-scan the target folder for local ROM files (use per-item checks)')
    parser.add_argument('--extract-files', action='store_true', help='Extract archive files after download (default: only DS extracts unless overridden)')
    parser.add_argument('--delete-duplicates', action='store_true', help='When multiple local matches are found for a title, offer to remove redundant files (prompts per-title)')
    parser.add_argument('--yes-delete', action='store_true', help='Auto-confirm deletion of duplicates (use with caution)')
    parser.add_argument('--categorize-by-popularity', action='store_true', help='Move downloaded files into stars/<n> or score/<n> based on Vimm popularity (uses metadata cache)')
    parser.add_argument('--categorize-by-popularity-mode', choices=['stars','score'], default='stars', help='Categorization mode: stars (default) or score (integer)')
    parser.add_argument('--src', help='Path to the project/src root where `vimms_config.json` and scripts live (useful when running from a different CWD)')
    args = parser.parse_args()

    # Parse optional section-priority override passed from runner
    sections_override = None
    if getattr(args, 'section_priority', None):
        sp_raw = str(args.section_priority)
        sections_override = [s.strip().upper() for s in sp_raw.split(',') if s.strip()]

    # Get target directory: either supplied or the directory where this script lives
    if args.folder:
        script_dir = Path(args.folder).expanduser().resolve()
    else:
        # Allow running from a different working directory by passing --src
        script_dir = Path(args.src).expanduser().resolve() if args.src else Path(__file__).parent

    # Auto-detect console from folder name
    console = detect_console_from_folder(script_dir)
    
    if not console:
        print("=" * 80)
        print("⚠️  Could not auto-detect console from folder name!")
        print("=" * 80)
        print(f"\nCurrent folder: {script_dir.name}")
        print("\nSupported console folder names:")
        print("  - DS, NDS (Nintendo DS)")
        print("  - NES (Nintendo Entertainment System)")
        print("  - SNES (Super Nintendo)")
        print("  - N64 (Nintendo 64)")
        print("  - GC, GameCube (Nintendo GameCube)")
        print("  - Wii, WiiWare")
        print("  - GB, GameBoy (Game Boy)")
        print("  - GBC (Game Boy Color)")
        print("  - GBA (Game Boy Advance)")
        print("  - PS1, PSX, PlayStation (PlayStation 1)")
        print("  - PS2 (PlayStation 2)")
        print("  - PS3 (PlayStation 3)")
        print("  - PSP (PlayStation Portable)")
        print("  - Genesis, MegaDrive")
        print("  - SMS, MasterSystem")
        print("  - Saturn, Dreamcast, DC")
        print("  - Xbox")
        print("  - Atari2600, Atari7800")
        print("\nPlease rename your folder to match one of these names, or")
        print("manually specify the console in the script.")
        return
    
    print(f"✅ Auto-detected console: {console}")
    print(f"   Based on folder name: {script_dir.name}\n")
    
    # Prefer a `ROMs` subfolder for downloads. Create it if missing.
    roms_dir = script_dir / 'ROMs'
    try:
        roms_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # If we cannot create it for any reason, fall back to the folder itself
        roms_dir = script_dir

    # Create downloader
    # By default the downloader is non-interactive. Use `--prompt` to allow interactive prompts.
    if args.prompt:
        input("\nPress Enter to start downloading...")

    downloader = VimmsDownloader(
        download_dir=str(roms_dir),
        system=console,
        detect_existing=not args.no_detect_existing,
        pre_scan=not args.no_pre_scan,
        extract_files=args.extract_files,
        delete_duplicates=args.delete_duplicates,
        auto_confirm_delete=args.yes_delete,
        section_priority_override=sections_override,
        allow_prompt=args.prompt,
        categorize_by_popularity=args.categorize_by_popularity,
    )

    # Start downloading
    try:
        # If interactive prompts are allowed, run normally (prompts will be emitted).
        # Otherwise run non-interactively (default behavior).
        downloader.download_all_games()
    except KeyboardInterrupt:
        print("\n\n⏸️  Download interrupted by user.")
        print("   Progress has been saved. Run the script again to resume.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        print("   Progress has been saved. Run the script again to resume.")


if __name__ == "__main__":
    main()
