"""Minimal Flask web UI for browsing and queuing Vimm downloads."""
from flask import Flask, request, jsonify, render_template, send_from_directory
from threading import Thread
import queue
import time
from datetime import datetime
import sys
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import json

# Add repository root to path for shared libraries (downloader_lib, utils)
# and cli directory for CLI tool imports
repo_root = Path(__file__).parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

cli_dir = repo_root / 'cli'
if str(cli_dir) not in sys.path:
    sys.path.insert(0, str(cli_dir))

from download_vimms import VimmsDownloader, CONSOLE_MAP, SECTIONS
from downloader_lib.parse import parse_game_details

# Try to import metadata functionality (optional)
try:
    from src.metadata import get_game_popularity, score_to_stars
except ImportError:
    get_game_popularity = None
    score_to_stars = None

app = Flask(__name__, 
            static_folder='webui_static/dist',
            static_url_path='',
            template_folder='webui_static/dist')
app.secret_key = 'vimms-downloader-secret-key-change-in-production'

BASE_DIR = Path(__file__).resolve().parent

# Helper: infer console/system from a folder Path
from download_vimms import CONSOLE_MAP

def detect_system_from_path(p: Path) -> str:
    """Return a console key inferred from a path's name or its parent."""
    for part in [p.name, p.parent.name]:
        if part in CONSOLE_MAP:
            return part
    return 'UNKNOWN'

# Configure logging for web UI
logger = logging.getLogger('webui')
if not logger.handlers:
    try:
        log_path = BASE_DIR / 'webui.log'
        handler = RotatingFileHandler(str(log_path), maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
        fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        # Log to console too when in debug
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        logger.setLevel(logging.INFO)
    except Exception:
        # Fallback: ensure logger exists
        logging.basicConfig(level=logging.INFO)

# Simple in-memory queue for download tasks
task_q = queue.Queue()
worker_thread = None
worker_running = False
QUEUE_FILE = BASE_DIR / 'webui_queue.json'
PROCESSED_FILE = BASE_DIR / 'webui_processed.json'
INDEX_FILE = BASE_DIR / 'webui_index.json'

# Simple global state for downloader instance per-root folder
DL_INSTANCES = {}

# Keep recent processed records in memory for quick access
PROCESSED = []

# Store current system/console globally (inferred from folder path)
CURRENT_SYSTEM = 'UNKNOWN'

# Cached index loaded at startup
CACHED_INDEX = None

# Progress tracking for index build
INDEX_PROGRESS = {
    'in_progress': False,
    'current_console': '',
    'current_section': '',
    'consoles_done': 0,
    'consoles_total': 0,
    'sections_done': 0,
    'sections_total': 0,
    'games_found': 0,
    'partial_consoles': []  # Consoles completed so far
}

def _save_processed_to_disk():
    try:
        import json
        with open(PROCESSED_FILE, 'w', encoding='utf-8') as f:
            json.dump(PROCESSED, f, indent=2)
    except Exception:
        logger.exception('Could not save processed list to disk')


def _load_processed_from_disk():
    try:
        import json
        if PROCESSED_FILE.exists():
            with open(PROCESSED_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            PROCESSED.clear()
            PROCESSED.extend(data)
    except Exception:
        logger.exception('Could not load processed list from disk')

def _save_queue_to_disk():
    try:
        import json
        items = list(task_q.queue)
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2)
    except Exception:
        logger.exception('Could not save queue to disk')


def _load_queue_from_disk():
    try:
        import json
        if QUEUE_FILE.exists():
            with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                items = json.load(f)
            for it in items:
                task_q.put(it)
    except Exception:
        logger.exception('Could not load queue from disk')

logger = logging.getLogger('webui')


@app.route('/')
def index():
    """Serve React app from dist folder."""
    dist_folder = BASE_DIR / 'webui_static' / 'dist'
    index_path = dist_folder / 'index.html'
    
    if not index_path.exists():
        return jsonify({
            'error': 'React build not found. Please run: cd frontend && yarn build'
        }), 404
    
    return send_from_directory(str(dist_folder), 'index.html')


@app.route('/api/index/build', methods=['POST'])
def api_index_build():
    """Build complete index of all consoles and games in workspace root."""
    global CACHED_INDEX, DL_INSTANCES, INDEX_PROGRESS
    data = request.json or {}
    workspace_root = data.get('workspace_root')
    
    if not workspace_root:
        return jsonify({'error': 'workspace_root required'}), 400
    
    root_path = Path(workspace_root)
    if not root_path.exists():
        return jsonify({'error': 'workspace_root not found'}), 404
    
    logger.info(f"api_index_build: starting full scan of '{workspace_root}'")
    
    # Scan for console folders - both on disk and in config
    from download_vimms import CONSOLE_MAP
    console_folders_set = set()
    
    # STEP 1: Create ALL configured folders FIRST
    logger.info("api_index_build: STEP 1 - Creating all configured console folders...")
    try:
        config_path = Path('vimms_config.json')
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for folder_key in config.get('folders', {}).keys():
                if folder_key in CONSOLE_MAP:
                    console_folder = root_path / folder_key
                    if not console_folder.exists():
                        try:
                            console_folder.mkdir(parents=True, exist_ok=True)
                            logger.info(f"api_index_build: created folder '{folder_key}' at '{console_folder}'")
                        except Exception as e:
                            logger.warning(f"api_index_build: failed to create '{folder_key}': {e}")
                    # Also create ROMs subfolder
                    roms_folder = console_folder / 'ROMs'
                    if not roms_folder.exists():
                        try:
                            roms_folder.mkdir(parents=True, exist_ok=True)
                            logger.info(f"api_index_build: created ROMs subfolder for '{folder_key}'")
                        except Exception as e:
                            logger.warning(f"api_index_build: failed to create ROMs subfolder for '{folder_key}': {e}")
                    console_folders_set.add(folder_key)
    except Exception as e:
        logger.warning(f"api_index_build: could not load vimms_config.json: {e}")
    
    # STEP 2: Scan for any additional physical folders not in config
    logger.info("api_index_build: STEP 2 - Scanning for additional physical folders...")
    for child in root_path.iterdir():
        if child.is_dir() and child.name in CONSOLE_MAP:
            if child.name not in console_folders_set:
                logger.info(f"api_index_build: found additional physical folder '{child.name}'")
            console_folders_set.add(child.name)
    
    console_folders = sorted(list(console_folders_set))
    
    if not console_folders:
        return jsonify({'error': 'No console folders found in workspace root or config'}), 404
    
    # Initialize progress
    INDEX_PROGRESS['in_progress'] = True
    INDEX_PROGRESS['consoles_total'] = len(console_folders)
    INDEX_PROGRESS['consoles_done'] = 0
    INDEX_PROGRESS['sections_total'] = len(SECTIONS)
    INDEX_PROGRESS['sections_done'] = 0
    INDEX_PROGRESS['games_found'] = 0
    INDEX_PROGRESS['partial_consoles'] = []
    
    logger.info(f"api_index_build: found {len(console_folders)} console folders: {console_folders}")
    
    # Load existing index to preserve completed consoles
    existing_index = {}
    index_file_path = BASE_DIR / 'webui_index.json'
    if index_file_path.exists():
        try:
            with open(index_file_path, 'r', encoding='utf-8') as f:
                existing_index = json.load(f)
            logger.info(f"api_index_build: loaded existing index with {len(existing_index.get('consoles', []))} consoles")
        except Exception as e:
            logger.warning(f"api_index_build: could not load existing index: {e}")
    
    # Build index - preserve only COMPLETED consoles from existing index
    # Incomplete consoles need to be re-indexed to get latest data (ratings, etc.)
    index_data = {
        'workspace_root': str(root_path),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'consoles': [c for c in existing_index.get('consoles', []) if c.get('complete') == True],
        'complete': False  # Mark as incomplete until build finishes
    }
    
    if index_data['consoles']:
        logger.info(f"api_index_build: preserved {len(index_data['consoles'])} completed consoles from previous index")
    
    total_games = 0
    for console_name in console_folders:
        system = CONSOLE_MAP.get(console_name, console_name)
        
        # Check if this console is already complete (resuming interrupted build)
        already_complete = False
        for existing_console in index_data.get('consoles', []):
            if existing_console.get('name') == console_name and existing_console.get('complete') == True:
                already_complete = True
                total_games += sum(len(s) for s in existing_console.get('sections', {}).values())
                INDEX_PROGRESS['consoles_done'] += 1
                logger.info(f"api_index_build: skipping '{console_name}' (already complete)")
                break
        
        if already_complete:
            continue
        
        # Update progress
        INDEX_PROGRESS['current_console'] = console_name
        INDEX_PROGRESS['sections_done'] = 0
        
        # Check if folder exists on disk
        console_folder = root_path / console_name
        if not console_folder.exists():
            # Auto-create missing console folders
            try:
                console_folder.mkdir(parents=True, exist_ok=True)
                logger.info(f"api_index_build: created missing folder '{console_folder}'")
                # Also create ROMs subfolder
                roms_folder = console_folder / 'ROMs'
                roms_folder.mkdir(parents=True, exist_ok=True)
                logger.info(f"api_index_build: created ROMs subfolder '{roms_folder}'")
            except Exception as e:
                logger.warning(f"api_index_build: could not create folder '{console_folder}': {e}")
                # Create placeholder entry for folders we couldn't create
                console_entry = {
                    'name': console_name,
                    'system': system,
                    'folder': str(console_folder),
                    'sections': {},
                    'total_games': 0,
                    'exists': False,
                    'complete': True  # Mark as complete even if folder doesn't exist
                }
                # Remove any old entry for this console
                index_data['consoles'] = [c for c in index_data.get('consoles', []) if c.get('name') != console_name]
                index_data['consoles'].append(console_entry)
                INDEX_PROGRESS['consoles_done'] += 1
                continue
        
        # Prefer ROMs subfolder
        roms_folder = console_folder / 'ROMs'
        target_folder = roms_folder if roms_folder.exists() else console_folder
        
        logger.info(f"api_index_build: scanning console '{console_name}' at '{target_folder}'")
        logger.info(f"api_index_build: console_folder exists={console_folder.exists()}, roms_folder exists={roms_folder.exists()}")
        
        # Log what's actually in the folder for debugging
        try:
            if target_folder.exists():
                file_count = sum(1 for _ in target_folder.iterdir())
                logger.info(f"api_index_build: target_folder '{target_folder}' contains {file_count} items")
        except Exception as e:
            logger.warning(f"api_index_build: error counting items in '{target_folder}': {e}")
        
        try:
            # Create downloader with pre_scan to build local index
            dl = VimmsDownloader(str(target_folder), system=system, detect_existing=True, pre_scan=True)
            DL_INSTANCES[str(target_folder)] = dl
            
            # Manually trigger local index build since we're not calling download_games_from_sections
            if dl.detect_existing and dl.pre_scan:
                dl._build_local_index()
                if dl.local_index is not None:
                    count_files = sum(len(v) for v in dl.local_index.values())
                    count_keys = len(dl.local_index.keys())
                    logger.info(f"api_index_build: pre-scanned {count_files} files ({count_keys} unique keys) for '{console_name}' in '{target_folder}'")
                    # Log first few index keys for debugging
                    sample_keys = list(dl.local_index.keys())[:5]
                    logger.info(f"api_index_build: sample index keys: {sample_keys}")
                else:
                    logger.warning(f"api_index_build: local_index is None for '{console_name}' - pre_scan may have failed")
            
            # Scan all sections
            sections_data = {}
            for idx, section in enumerate(SECTIONS):
                INDEX_PROGRESS['current_section'] = section
                INDEX_PROGRESS['sections_done'] = idx
                try:
                    games = dl.get_game_list_from_section(section)
                    
                    # Annotate with local presence
                    annotated_games = []
                    debug_count = 0
                    for game in games:
                        present = False
                        try:
                            if dl.local_index is not None:
                                matches = dl.find_all_matching_files(game['name'])
                                present = bool(matches)
                                # Debug log first few games in each section to see matching behavior
                                if debug_count < 3:
                                    logger.info(f"api_index_build: game='{game['name']}' present={present} matches={len(matches) if matches else 0}")
                                    debug_count += 1
                        except Exception as e:
                            logger.exception(f"api_index_build: error checking '{game['name']}': {e}")
                            pass
                        
                        game_entry = {
                            'id': game.get('game_id', ''),
                            'name': game.get('name', ''),
                            'url': game.get('page_url', ''),
                            'present': present
                        }
                        
                        # Preserve rating if extracted from section page
                        if 'rating' in game:
                            game_entry['rating'] = game['rating']
                        
                        annotated_games.append(game_entry)
                        total_games += 1
                        INDEX_PROGRESS['games_found'] = total_games
                    
                    sections_data[section] = annotated_games
                    logger.info(f"api_index_build: section '{section}' for '{console_name}': {len(annotated_games)} games")
                    
                except Exception as e:
                    logger.warning(f"api_index_build: error scanning section '{section}' for '{console_name}': {e}")
                    sections_data[section] = []
            
            console_entry = {
                'name': console_name,
                'system': system,
                'folder': str(target_folder),
                'sections': sections_data,
                'complete': True  # Mark this console as complete
            }
            
            # Remove any old incomplete entry for this console
            index_data['consoles'] = [c for c in index_data.get('consoles', []) if c.get('name') != console_name]
            
            index_data['consoles'].append(console_entry)
            INDEX_PROGRESS['consoles_done'] += 1
            INDEX_PROGRESS['partial_consoles'].append(console_entry)  # Add to partial list for progressive UI
            logger.info(f"api_index_build: completed '{console_name}' with {sum(len(s) for s in sections_data.values())} total games")
            
            # Save incrementally after each console to avoid data loss
            try:
                with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, indent=2)
            except Exception as e:
                logger.exception(f"api_index_build: error saving incremental progress: {e}")
            
        except Exception as e:
            logger.exception(f"api_index_build: error scanning console '{console_name}': {e}")
    
    # Mark as complete and save final version
    index_data['complete'] = True
    try:
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        logger.info(f"api_index_build: saved complete index with {len(index_data['consoles'])} consoles, {total_games} total games")
    except Exception as e:
        logger.exception(f"api_index_build: error saving index file: {e}")
        return jsonify({'error': 'Failed to save index file'}), 500
    
    CACHED_INDEX = index_data
    INDEX_PROGRESS['in_progress'] = False
    INDEX_PROGRESS['current_console'] = 'Complete'
    INDEX_PROGRESS['current_section'] = ''
    INDEX_PROGRESS['partial_consoles'] = []  # Clear partial data
    
    return jsonify({
        'status': 'ok',
        'consoles_count': len(index_data['consoles']),
        'total_games': total_games,
        'timestamp': index_data['timestamp']
    })


@app.route('/api/index/progress', methods=['GET'])
def api_index_progress():
    """Get current progress of index build operation and resync status."""
    # Ensure resync keys exist
    prog = dict(INDEX_PROGRESS)
    prog.setdefault('resync_in_progress', False)
    prog.setdefault('resync_partial_consoles', [])
    return jsonify(prog)


@app.route('/api/index/get', methods=['GET'])
def api_index_get():
    """Get cached index data."""
    global CACHED_INDEX
    
    # Try to load from memory first
    if CACHED_INDEX:
        return jsonify(CACHED_INDEX)
    
    # Load from file
    if not INDEX_FILE.exists():
        # Return empty index instead of 404 to avoid UI errors
        return jsonify({
            'workspace_root': '',
            'timestamp': '',
            'consoles': [],
            'complete': False
        })
    
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            CACHED_INDEX = json.load(f)
        
        # Add 'complete' flag if missing (legacy indexes)
        if 'complete' not in CACHED_INDEX:
            CACHED_INDEX['complete'] = True  # Assume old indexes are complete
        
        # Compute missing consoles for convenience
        missing = _find_missing_consoles(CACHED_INDEX.get('workspace_root', ''), CACHED_INDEX)
        CACHED_INDEX['missing_consoles'] = missing
        return jsonify(CACHED_INDEX)
    except Exception as e:
        logger.exception(f"api_index_get: error loading index file: {e}")
        return jsonify({'error': 'Failed to load index file'}), 500


# Global paths for catalog cache
REMOTE_CATALOG_FILE = BASE_DIR / 'webui_remote_catalog.json'
REMOTE_CATALOG_PROGRESS = {
    'in_progress': False,
    'consoles_total': 0,
    'consoles_done': 0,
    'current_console': '',
    'sections_done': 0,
    'sections_total': len(SECTIONS),
    'percent_complete': 0
}


@app.route('/api/catalog/remote/get', methods=['GET'])
def api_catalog_remote_get():
    """Return cached remote catalog if it exists."""
    if not REMOTE_CATALOG_FILE.exists():
        return jsonify({'error': 'No remote catalog cached. Please build it first.'}), 404
    
    try:
        with open(REMOTE_CATALOG_FILE, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        return jsonify(catalog)
    except Exception as e:
        logger.exception(f"api_catalog_remote_get: error: {e}")
        return jsonify({'error': 'Failed to load remote catalog'}), 500


@app.route('/api/catalog/remote/progress', methods=['GET'])
def api_catalog_remote_progress():
    """Return progress of remote catalog building."""
    return jsonify(REMOTE_CATALOG_PROGRESS)


@app.route('/api/catalog/remote/build', methods=['POST'])
def api_catalog_remote_build():
    """Build remote game catalog by fetching from Vimm's Lair (one-time, slow operation).
    
    This fetches ALL game lists from Vimm's Lair and caches them locally.
    Takes 15-30 minutes due to network requests but only needs to run once.
    """
    global REMOTE_CATALOG_PROGRESS
    
    if REMOTE_CATALOG_PROGRESS['in_progress']:
        return jsonify({'error': 'Remote catalog build already in progress'}), 409
    
    logger.info("api_catalog_remote_build: starting remote catalog fetch")
    
    def build_remote_catalog():
        """Background thread to fetch remote game catalog."""
        global REMOTE_CATALOG_PROGRESS
        from download_vimms import CONSOLE_MAP
        
        try:
            REMOTE_CATALOG_PROGRESS['in_progress'] = True
            REMOTE_CATALOG_PROGRESS['consoles_total'] = len(CONSOLE_MAP)
            REMOTE_CATALOG_PROGRESS['consoles_done'] = 0
            
            catalog = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'consoles': {}
            }
            
            console_keys = sorted(CONSOLE_MAP.keys())
            
            for console_idx, console_name in enumerate(console_keys):
                system = CONSOLE_MAP[console_name]
                REMOTE_CATALOG_PROGRESS['current_console'] = console_name
                REMOTE_CATALOG_PROGRESS['sections_done'] = 0
                
                logger.info(f"api_catalog_remote_build: fetching '{console_name}' (system={system})")
                
                # Create temporary downloader just for fetching (no local folder needed)
                temp_dir = BASE_DIR / 'temp_catalog'
                temp_dir.mkdir(exist_ok=True)
                dl = VimmsDownloader(str(temp_dir), system=system, detect_existing=False, pre_scan=False)
                
                sections_data = {}
                for section_idx, section in enumerate(SECTIONS):
                    REMOTE_CATALOG_PROGRESS['sections_done'] = section_idx
                    REMOTE_CATALOG_PROGRESS['percent_complete'] = int(
                        (console_idx * len(SECTIONS) + section_idx) / (len(CONSOLE_MAP) * len(SECTIONS)) * 100
                    )
                    
                    try:
                        games = dl.get_game_list_from_section(section)
                        # Store game metadata without local presence info
                        sections_data[section] = [
                            {
                                'id': g.get('game_id', ''),
                                'name': g.get('name', ''),
                                'url': g.get('page_url', '')
                            }
                            for g in games
                        ]
                        logger.info(f"api_catalog_remote_build: section '{section}' for '{console_name}': {len(games)} games")
                    except Exception as e:
                        logger.exception(f"api_catalog_remote_build: error fetching section '{section}' for '{console_name}': {e}")
                        sections_data[section] = []
                
                catalog['consoles'][console_name] = {
                    'name': console_name,
                    'system': system,
                    'sections': sections_data
                }
                
                REMOTE_CATALOG_PROGRESS['consoles_done'] = console_idx + 1
                REMOTE_CATALOG_PROGRESS['percent_complete'] = int((console_idx + 1) / len(CONSOLE_MAP) * 100)
            
            # Save catalog to disk
            with open(REMOTE_CATALOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(catalog, f, indent=2)
            
            logger.info(f"api_catalog_remote_build: saved remote catalog with {len(catalog['consoles'])} consoles")
            
        except Exception as e:
            logger.exception(f"api_catalog_remote_build: failed: {e}")
        finally:
            REMOTE_CATALOG_PROGRESS['in_progress'] = False
    
    # Start background thread
    thread = Thread(target=build_remote_catalog, daemon=True)
    thread.start()
    
    return jsonify({'status': 'started', 'message': 'Remote catalog build started in background'})


@app.route('/api/index/build_fast', methods=['POST'])
def api_index_build_fast():
    """Fast index build using cached remote catalog + local file scan.
    
    This is the FAST path - loads remote catalog from cache (instant) and only
    scans local files for presence detection (milliseconds). Should complete in <1 second.
    
    Requires: Remote catalog must exist (build it once with /api/catalog/remote/build)
    """
    global CACHED_INDEX, DL_INSTANCES, INDEX_PROGRESS
    
    data = request.json or {}
    workspace_root = data.get('workspace_root')
    
    if not workspace_root:
        return jsonify({'error': 'workspace_root required'}), 400
    
    root_path = Path(workspace_root)
    if not root_path.exists():
        return jsonify({'error': f"Workspace root '{workspace_root}' not found"}), 404
    
    # Check if remote catalog exists
    if not REMOTE_CATALOG_FILE.exists():
        return jsonify({
            'error': 'No remote catalog cached. Please build it first with /api/catalog/remote/build',
            'hint': 'This is a one-time operation that takes 15-30 minutes.'
        }), 404
    
    logger.info(f"api_index_build_fast: starting FAST scan of '{workspace_root}' using cached catalog")
    
    # Start build in background thread
    def build_fast():
        with app.app_context():
            try:
                api_index_build_fast_internal(workspace_root)
            except Exception as e:
                logger.exception(f"api_index_build_fast: error: {e}")
    
    thread = Thread(target=build_fast, daemon=True)
    thread.start()
    
    return jsonify({'status': 'started', 'message': 'Fast index build started'})


def api_index_build_fast_internal(workspace_root):
    """Internal helper for fast index build using cached remote catalog."""
    global CACHED_INDEX, DL_INSTANCES, INDEX_PROGRESS
    from download_vimms import CONSOLE_MAP
    
    root_path = Path(workspace_root)
    
    # Load remote catalog
    logger.info("api_index_build_fast_internal: loading cached remote catalog")
    with open(REMOTE_CATALOG_FILE, 'r', encoding='utf-8') as f:
        remote_catalog = json.load(f)
    
    # STEP 1: Create ALL configured console folders FIRST
    logger.info("api_index_build_fast_internal: STEP 1 - Creating all configured console folders...")
    folders_created = 0
    folders_existed = 0
    console_folders_set = set()
    
    try:
        config_path = Path('vimms_config.json')
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for folder_key in config.get('folders', {}).keys():
                if folder_key in CONSOLE_MAP:
                    console_folder = root_path / folder_key
                    if not console_folder.exists():
                        try:
                            console_folder.mkdir(parents=True, exist_ok=True)
                            folders_created += 1
                            logger.info(f"api_index_build_fast_internal: created folder '{folder_key}'")
                        except Exception as e:
                            logger.warning(f"api_index_build_fast_internal: failed to create '{folder_key}': {e}")
                    else:
                        folders_existed += 1
                    # Create ROMs subfolder
                    roms_folder = console_folder / 'ROMs'
                    if not roms_folder.exists():
                        try:
                            roms_folder.mkdir(parents=True, exist_ok=True)
                        except Exception as e:
                            logger.warning(f"api_index_build_fast_internal: failed to create ROMs for '{folder_key}': {e}")
                    console_folders_set.add(folder_key)
    except Exception as e:
        logger.warning(f"api_index_build_fast_internal: could not load config: {e}")
    
    logger.info(f"api_index_build_fast_internal: Folders: {folders_created} created, {folders_existed} already existed")
    
    # STEP 2: Scan for additional physical folders
    logger.info("api_index_build_fast_internal: STEP 2 - Scanning for additional physical folders...")
    for child in root_path.iterdir():
        if child.is_dir() and child.name in CONSOLE_MAP:
            if child.name not in console_folders_set:
                logger.info(f"api_index_build_fast_internal: found additional folder '{child.name}'")
            console_folders_set.add(child.name)
    
    console_folders = sorted(list(console_folders_set))
    
    # Initialize progress
    INDEX_PROGRESS['in_progress'] = True
    INDEX_PROGRESS['consoles_total'] = len(console_folders)
    INDEX_PROGRESS['consoles_done'] = 0
    INDEX_PROGRESS['sections_total'] = len(SECTIONS)
    INDEX_PROGRESS['sections_done'] = 0
    INDEX_PROGRESS['games_found'] = 0
    INDEX_PROGRESS['partial_consoles'] = []
    
    logger.info(f"api_index_build_fast_internal: STEP 3 - Fast scanning {len(console_folders)} consoles")
    
    # Build index (or load partial progress if resuming)
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            if index_data.get('workspace_root') != str(root_path):
                logger.info(f"api_index_build_fast_internal: existing index is for different workspace, starting fresh")
                index_data = {
                    'workspace_root': str(root_path),
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'consoles': [],
                    'complete': False
                }
            else:
                logger.info(f"api_index_build_fast_internal: resuming with {len(index_data.get('consoles', []))} consoles already complete")
                index_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'
                index_data['complete'] = False
        except Exception as e:
            logger.warning(f"api_index_build_fast_internal: error loading partial index: {e}")
            index_data = {
                'workspace_root': str(root_path),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'consoles': [],
                'complete': False
            }
    else:
        index_data = {
            'workspace_root': str(root_path),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'consoles': [],
            'complete': False
        }
    
    total_games = 0
    for console_name in console_folders:
        system = CONSOLE_MAP.get(console_name, console_name)
        
        # Check if this console is already complete
        already_complete = False
        for existing_console in index_data.get('consoles', []):
            if existing_console.get('name') == console_name and existing_console.get('complete') == True:
                already_complete = True
                total_games += existing_console.get('total_games', 0)
                INDEX_PROGRESS['consoles_done'] += 1
                logger.info(f"api_index_build_fast_internal: skipping '{console_name}' (already complete)")
                break
        
        if already_complete:
            continue
        
        INDEX_PROGRESS['current_console'] = console_name
        INDEX_PROGRESS['sections_done'] = 0
        
        # Get console folder
        console_folder = root_path / console_name
        roms_folder = console_folder / 'ROMs'
        target_folder = roms_folder if roms_folder.exists() else console_folder
        
        logger.info(f"api_index_build_fast_internal: scanning '{console_name}' at '{target_folder}'")
        
        try:
            # Create downloader ONLY for local file scanning (FAST)
            dl = VimmsDownloader(str(target_folder), system=system, detect_existing=True, pre_scan=True)
            DL_INSTANCES[str(target_folder)] = dl
            
            # Build local index (FAST - milliseconds for thousands of files)
            if dl.detect_existing and dl.pre_scan:
                dl._build_local_index()
                if dl.local_index is not None:
                    count_files = sum(len(v) for v in dl.local_index.values())
                    logger.info(f"api_index_build_fast_internal: pre-scanned {count_files} files for '{console_name}'")
            
            # Get remote game list from cached catalog (INSTANT - no network)
            console_remote = remote_catalog['consoles'].get(console_name, {})
            sections_data = {}
            
            for idx, section in enumerate(SECTIONS):
                INDEX_PROGRESS['current_section'] = section
                INDEX_PROGRESS['sections_done'] = idx
                
                # Get games from cached catalog (no network fetch!)
                cached_games = console_remote.get('sections', {}).get(section, [])
                
                # Annotate with local presence (FAST - uses pre-built local index)
                annotated_games = []
                for game in cached_games:
                    present = False
                    try:
                        if dl.local_index is not None:
                            matches = dl.find_all_matching_files(game['name'])
                            present = bool(matches)
                    except Exception as e:
                        logger.exception(f"api_index_build_fast_internal: error checking '{game['name']}': {e}")
                    
                    game_entry = {
                        'id': game.get('id', ''),
                        'name': game.get('name', ''),
                        'url': game.get('url', ''),
                        'present': present
                    }
                    
                    # Preserve rating from cached catalog (from previous full build)
                    if 'rating' in game:
                        game_entry['rating'] = game['rating']
                    
                    annotated_games.append(game_entry)
                    total_games += 1
                    INDEX_PROGRESS['games_found'] = total_games
                
                sections_data[section] = annotated_games
            
            # Create console entry
            console_entry = {
                'name': console_name,
                'system': system,
                'folder': str(console_folder),
                'sections': sections_data,
                'total_games': sum(len(s) for s in sections_data.values()),
                'exists': True,
                'complete': True  # Mark as complete
            }
            
            # Remove any old incomplete entry for this console
            index_data['consoles'] = [c for c in index_data.get('consoles', []) if c.get('name') != console_name]
            
            index_data['consoles'].append(console_entry)
            INDEX_PROGRESS['partial_consoles'].append(console_entry)
            INDEX_PROGRESS['consoles_done'] += 1
            
            logger.info(f"api_index_build_fast_internal: completed '{console_name}' with {console_entry['total_games']} games")
            
            # Save incremental progress
            try:
                with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, indent=2)
            except Exception as e:
                logger.exception(f"api_index_build_fast_internal: error saving progress: {e}")
        
        except Exception as e:
            logger.exception(f"api_index_build_fast_internal: error scanning '{console_name}': {e}")
    
    # Mark as complete
    index_data['complete'] = True
    try:
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        CACHED_INDEX = index_data
        INDEX_PROGRESS['in_progress'] = False
        logger.info(f"api_index_build_fast_internal: saved complete index with {len(index_data['consoles'])} consoles, {total_games} total games")
    except Exception as e:
        logger.exception(f"api_index_build_fast_internal: error saving final index: {e}")


@app.route('/api/index/refresh', methods=['POST'])
def api_index_refresh():
    """Refresh the index by re-scanning the workspace root from existing cache."""
    global CACHED_INDEX
    
    # Get workspace root from existing cache
    if not INDEX_FILE.exists():
        return jsonify({'error': 'No existing index to refresh. Please build initial index first.'}), 404
    
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            old_index = json.load(f)
        workspace_root = old_index.get('workspace_root')
        
        if not workspace_root:
            return jsonify({'error': 'No workspace_root in existing index'}), 400
        
        logger.info(f"api_index_refresh: refreshing index for '{workspace_root}'")
        
        # Call build with stored workspace root
        return api_index_build_internal(workspace_root)
        
    except Exception as e:
        logger.exception(f"api_index_refresh: error: {e}")
        return jsonify({'error': 'Failed to refresh index'}), 500


def api_index_build_internal(workspace_root):
    """Internal helper to build index (shared by build and refresh endpoints)."""
    global CACHED_INDEX, DL_INSTANCES, INDEX_PROGRESS
    
    root_path = Path(workspace_root)
    if not root_path.exists():
        return jsonify({'error': f"Workspace root '{workspace_root}' not found"}), 404
    
    logger.info(f"api_index_build_internal: starting full scan of '{workspace_root}'")
    
    # Scan for console folders - both on disk and in config
    from download_vimms import CONSOLE_MAP
    console_folders_set = set()
    
    # STEP 1: Create ALL configured folders FIRST
    logger.info("api_index_build_internal: STEP 1 - Creating all configured console folders...")
    folders_created = 0
    folders_existed = 0
    try:
        config_path = Path('vimms_config.json')
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for folder_key in config.get('folders', {}).keys():
                if folder_key in CONSOLE_MAP:
                    console_folder = root_path / folder_key
                    if not console_folder.exists():
                        try:
                            console_folder.mkdir(parents=True, exist_ok=True)
                            folders_created += 1
                            logger.info(f"api_index_build_internal: created folder '{folder_key}' at '{console_folder}'")
                        except Exception as e:
                            logger.warning(f"api_index_build_internal: failed to create '{folder_key}': {e}")
                    else:
                        folders_existed += 1
                    # Also create ROMs subfolder
                    roms_folder = console_folder / 'ROMs'
                    if not roms_folder.exists():
                        try:
                            roms_folder.mkdir(parents=True, exist_ok=True)
                        except Exception as e:
                            logger.warning(f"api_index_build_internal: failed to create ROMs subfolder for '{folder_key}': {e}")
                    console_folders_set.add(folder_key)
    except Exception as e:
        logger.warning(f"api_index_build_internal: could not load vimms_config.json: {e}")
    
    logger.info(f"api_index_build_internal: Folders: {folders_created} created, {folders_existed} already existed")
    
    # STEP 2: Scan for any additional physical folders not in config
    logger.info("api_index_build_internal: STEP 2 - Scanning for additional physical folders...")
    for child in root_path.iterdir():
        if child.is_dir() and child.name in CONSOLE_MAP:
            if child.name not in console_folders_set:
                logger.info(f"api_index_build_internal: found additional physical folder '{child.name}'")
            console_folders_set.add(child.name)
    
    console_folders = sorted(list(console_folders_set))
    
    if not console_folders:
        return jsonify({'error': 'No console folders found in workspace root or config'}), 404
    
    # Initialize progress
    INDEX_PROGRESS['in_progress'] = True
    INDEX_PROGRESS['consoles_total'] = len(console_folders)
    INDEX_PROGRESS['consoles_done'] = 0
    INDEX_PROGRESS['sections_total'] = len(SECTIONS)
    INDEX_PROGRESS['sections_done'] = 0
    INDEX_PROGRESS['games_found'] = 0
    INDEX_PROGRESS['partial_consoles'] = []
    
    logger.info(f"api_index_build_internal: found {len(console_folders)} console folders: {console_folders}")
    
    # Load existing index to preserve completed consoles
    existing_index = {}
    index_file_path = BASE_DIR / 'webui_index.json'
    if index_file_path.exists():
        try:
            with open(index_file_path, 'r', encoding='utf-8') as f:
                existing_index = json.load(f)
            logger.info(f"api_index_build_internal: loaded existing index with {len(existing_index.get('consoles', []))} consoles")
        except Exception as e:
            logger.warning(f"api_index_build_internal: could not load existing index: {e}")
    
    # Build index - preserve only COMPLETED consoles from existing index
    # Incomplete consoles need to be re-indexed to get latest data (ratings, etc.)
    index_data = {
        'workspace_root': str(root_path),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'consoles': [c for c in existing_index.get('consoles', []) if c.get('complete') == True],
        'complete': False  # Mark as incomplete until build finishes
    }
    
    if index_data['consoles']:
        logger.info(f"api_index_build_internal: preserved {len(index_data['consoles'])} completed consoles from previous index")
    
    total_games = 0
    for console_name in console_folders:
        system = CONSOLE_MAP.get(console_name, console_name)
        
        # Check if this console is already complete (resuming interrupted build)
        already_complete = False
        for existing_console in index_data.get('consoles', []):
            if existing_console.get('name') == console_name and existing_console.get('complete') == True:
                already_complete = True
                # Calculate total games from sections
                console_game_count = sum(len(section_games) for section_games in existing_console.get('sections', {}).values())
                total_games += console_game_count
                INDEX_PROGRESS['consoles_done'] += 1
                logger.info(f"api_index_build_internal: skipping '{console_name}' (already complete)")
                break
        
        if already_complete:
            continue
        
        # Update progress
        INDEX_PROGRESS['current_console'] = console_name
        INDEX_PROGRESS['sections_done'] = 0
        
        # Get console folder (already created in STEP 1)
        console_folder = root_path / console_name
        
        # Prefer ROMs subfolder if it exists
        roms_folder = console_folder / 'ROMs'
        target_folder = roms_folder if roms_folder.exists() else console_folder
        
        logger.info(f"api_index_build_internal: STEP 3 - Scanning console '{console_name}' at '{target_folder}'")
        
        try:
            # Create downloader with pre_scan to build local index
            dl = VimmsDownloader(str(target_folder), system=system, detect_existing=True, pre_scan=True)
            DL_INSTANCES[str(target_folder)] = dl
            
            # Manually trigger local index build since we're not calling download_games_from_sections
            if dl.detect_existing and dl.pre_scan:
                dl._build_local_index()
                if dl.local_index is not None:
                    count_files = sum(len(v) for v in dl.local_index.values())
                    logger.info(f"api_index_build_internal: pre-scanned {count_files} files for '{console_name}'")
            
            # Scan all sections
            sections_data = {}
            for idx, section in enumerate(SECTIONS):
                INDEX_PROGRESS['current_section'] = section
                INDEX_PROGRESS['sections_done'] = idx
                try:
                    games = dl.get_game_list_from_section(section)
                    
                    # Annotate with local presence
                    annotated_games = []
                    debug_count = 0
                    for game in games:
                        present = False
                        try:
                            if dl.local_index is not None:
                                matches = dl.find_all_matching_files(game['name'])
                                present = bool(matches)
                                # Debug log first few games in number section to see matching behavior
                                if section == 'number' and debug_count < 5:
                                    logger.info(f"api_index_build_internal: game='{game['name']}' present={present} matches={len(matches) if matches else 0}")
                                    debug_count += 1
                        except Exception as e:
                            logger.exception(f"api_index_build_internal: error checking '{game['name']}': {e}")
                            pass
                        
                        game_entry = {
                            'id': game.get('game_id', ''),
                            'name': game.get('name', ''),
                            'url': game.get('page_url', ''),
                            'present': present
                        }
                        
                        # Preserve rating if extracted from section page
                        if 'rating' in game:
                            game_entry['rating'] = game['rating']
                        
                        annotated_games.append(game_entry)
                        total_games += 1
                        INDEX_PROGRESS['games_found'] = total_games
                    
                    sections_data[section] = annotated_games
                    logger.info(f"api_index_build_internal: section '{section}' for '{console_name}': {len(annotated_games)} games")
                    
                except Exception as e:
                    logger.warning(f"api_index_build_internal: error scanning section '{section}' for '{console_name}': {e}")
                    sections_data[section] = []
            
            console_entry = {
                'name': console_name,
                'system': system,
                'folder': str(target_folder),
                'sections': sections_data
            }
            index_data['consoles'].append(console_entry)
            INDEX_PROGRESS['consoles_done'] += 1
            INDEX_PROGRESS['partial_consoles'].append(console_entry)  # Add to partial list for progressive UI
            logger.info(f"api_index_build_internal: completed '{console_name}' with {sum(len(s) for s in sections_data.values())} total games")
            
            # Save incrementally after each console to avoid data loss
            try:
                with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, indent=2)
            except Exception as e:
                logger.exception(f"api_index_build_internal: error saving incremental progress: {e}")
            
        except Exception as e:
            logger.exception(f"api_index_build_internal: error scanning console '{console_name}': {e}")
    
    # Mark as complete and save final version
    index_data['complete'] = True
    try:
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        logger.info(f"api_index_build_internal: saved complete index with {len(index_data['consoles'])} consoles, {total_games} total games")
    except Exception as e:
        logger.exception(f"api_index_build_internal: error saving index file: {e}")
        return jsonify({'error': 'Failed to save index file'}), 500
    
    CACHED_INDEX = index_data
    INDEX_PROGRESS['in_progress'] = False
    INDEX_PROGRESS['current_console'] = 'Complete'
    INDEX_PROGRESS['current_section'] = ''
    INDEX_PROGRESS['partial_consoles'] = []  # Clear partial data
    
    return jsonify({
        'status': 'ok',
        'consoles_count': len(index_data['consoles']),
        'total_games': total_games,
        'timestamp': index_data['timestamp']
    })


def _find_missing_consoles(root_path: Path, index_data: dict) -> dict:
    """Return a dict describing consoles missing or partially indexed.

    Returns:
      {
        'missing_on_disk': [names],    # present on disk but not in index
        'partial_in_index': [names],   # present in index but appear incomplete
        'to_resync': [names]           # union of both lists
      }

    A console is identified by folder name vs keys in CONSOLE_MAP (case-insensitive).
    """
    consoles_on_disk = []
    try:
        p = Path(root_path)
        for child in p.iterdir():
            if child.is_dir() and child.name.upper() in CONSOLE_MAP:
                consoles_on_disk.append(child.name.upper())
    except Exception:
        logger.exception(f"_find_missing_consoles: error scanning root '{root_path}'")

    indexed_entries = (index_data or {}).get('consoles', [])
    indexed_names = [c.get('name').upper() for c in indexed_entries if c.get('name')]

    # Missing consoles: on disk but not indexed
    missing_on_disk = [c for c in consoles_on_disk if c not in indexed_names]

    # Partial consoles: indexed but with zero or very low total game counts
    partial_in_index = []
    for c in indexed_entries:
        name = c.get('name')
        try:
            total_games = 0
            for sec in (c.get('sections') or {}).values():
                if isinstance(sec, list):
                    total_games += len(sec)
                elif isinstance(sec, int):
                    total_games += sec
            if total_games == 0 or total_games < 10:
                partial_in_index.append(name.upper())
        except Exception:
            continue

    # Build resync list
    to_resync = sorted(list(set(missing_on_disk + partial_in_index)))

    return {
        'missing_on_disk': missing_on_disk,
        'partial_in_index': partial_in_index,
        'to_resync': to_resync
    }


def _scan_console_and_append(index_data: dict, console_name: str, root_path: Path) -> dict:
    """Scan a single console folder and append the console entry to index_data.

    Returns the created console_entry dict.
    """
    global INDEX_PROGRESS
    console_folder = Path(root_path) / console_name
    # Prefer ROMs subfolder
    roms_folder = console_folder / 'ROMs'
    target_folder = roms_folder if roms_folder.exists() and roms_folder.is_dir() else console_folder

    try:
        dl = VimmsDownloader(str(target_folder), system=console_name, detect_existing=True, pre_scan=True)
        DL_INSTANCES[str(target_folder)] = dl
        sections_data = {}
        for idx, section in enumerate(SECTIONS):
            INDEX_PROGRESS['current_section'] = section
            INDEX_PROGRESS['sections_done'] = idx
            games = dl.get_game_list_from_section(section)
            # Annotate presence
            annotated_games = []
            for game in games:
                present = False
                try:
                    if dl.local_index is not None:
                        matches = dl.find_all_matching_files(game['name'])
                        present = bool(matches)
                except Exception:
                    present = False
                annotated_games.append(game)
            sections_data[section] = annotated_games
        console_entry = {
            'name': console_name,
            'system': CONSOLE_MAP.get(console_name, console_name),
            'folder': str(target_folder),
            'sections': {k: [g for g in v] for k, v in sections_data.items()}
        }
        index_data['consoles'].append(console_entry)
        # Save incrementally
        try:
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2)
        except Exception:
            logger.exception('Error saving incremental index for console %s', console_name)
        return console_entry
    except Exception as e:
        logger.exception(f"_scan_console_and_append: error scanning console '{console_name}': {e}")
        return None


@app.route('/api/index/resync', methods=['POST'])
def api_index_resync():
    """Resync missing consoles or selected consoles. Supports dry-run (no changes) and apply.

    Payload:
      {
        "mode": "dry" | "apply",
        "consoles": ["DS", "GBA"]  # optional, if omitted compute missing consoles
      }

    If mode == 'apply' this will run scans for the specified consoles and append them to the index incrementally.
    Returns the list of consoles affected and a status.
    """
    global CACHED_INDEX, INDEX_PROGRESS
    data = request.json or {}
    mode = data.get('mode', 'dry')
    consoles = data.get('consoles')

    # Ensure index exists
    if not INDEX_FILE.exists():
        return jsonify({'error': 'No index found to resync, please initialize index first.'}), 400

    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
    except Exception as e:
        logger.exception(f"api_index_resync: failed to read index file: {e}")
        return jsonify({'error': 'Failed to read index file'}), 500

    root = index_data.get('workspace_root') or ''

    if not consoles:
        findings = _find_missing_consoles(root, index_data)
        consoles = findings.get('to_resync', [])

    if mode == 'dry':
        # Return categorized results
        findings = _find_missing_consoles(root, index_data)
        return jsonify({'mode': 'dry', 'missing_on_disk': findings.get('missing_on_disk', []), 'partial_in_index': findings.get('partial_in_index', []), 'to_resync': findings.get('to_resync', [])})

    # mode == 'apply' -> start resync in background so API returns immediately
    def _resync_worker(items, root_path):
        logger.info(f"api_index_resync: starting resync for consoles: {items}")
        INDEX_PROGRESS['resync_in_progress'] = True
        INDEX_PROGRESS['resync_partial_consoles'] = []
        for c in items:
            try:
                idx_entry = _scan_console_and_append(index_data, c, Path(root_path))
                if idx_entry:
                    INDEX_PROGRESS['resync_partial_consoles'].append(idx_entry)
                    INDEX_PROGRESS['consoles_done'] = len(index_data['consoles'])
            except Exception:
                logger.exception(f"api_index_resync: error resyncing console {c}")
        # Mark complete flag depending on whether missing consoles remain
        missing_after = _find_missing_consoles(root_path, index_data)
        index_data['complete'] = False if missing_after else True
        try:
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2)
        except Exception:
            logger.exception('api_index_resync: failed to write final index file')
        INDEX_PROGRESS['resync_in_progress'] = False
        INDEX_PROGRESS['resync_partial_consoles'] = []
        logger.info('api_index_resync: resync worker complete')

    t = Thread(target=_resync_worker, args=(consoles, root), daemon=True)
    t.start()

    return jsonify({'status': 'resync_started', 'consoles': consoles}), 202

# NOTE: /api/init endpoint - Alternative initialization flow (currently unused by frontend)
# The frontend now uses /api/index/build or /api/index/build_fast instead.
# This endpoint is kept for potential future use or programmatic API access.
@app.route('/api/init', methods=['POST'])
def api_init():
    """Initialize downloader for a given folder path.

    If the provided folder is a workspace root containing console subfolders, return
    the list of console candidate subfolders so the UI can let the user pick one.
    Otherwise create a `VimmsDownloader` instance for that console folder.
    """
    data = request.json or {}
    folder = data.get('folder')
    if not folder:
        return jsonify({'error': 'folder required'}), 400
    p = Path(folder)
    create_flag = bool(data.get('create', False))
    create_consoles_flag = bool(data.get('create_consoles', False))

    if not p.exists():
        if create_flag:
            try:
                p.mkdir(parents=True, exist_ok=True)
                logger.info(f"api_init: created missing folder '{p}' as requested")
            except Exception as e:
                logger.exception(f"api_init: failed to create folder '{p}': {e}")
                return jsonify({'error': 'Failed to create folder'}), 500
        else:
            return jsonify({'error': 'folder not found'}), 404


    # If folder appears to be a workspace root (contains possible console folders), return candidates
    consoles = []
    try:
        # Known console names for detection (fallback if import fails)
        known_consoles = ['DS', 'NDS', 'NES', 'SNES', 'N64', 'GC', 'GAMECUBE', 'WII', 'WIIWARE', 
                         'GB', 'GAMEBOY', 'GBC', 'GBA', 'PS1', 'PSX', 'PLAYSTATION', 'PS2', 'PS3', 
                         'PSP', 'GENESIS', 'MEGADRIVE', 'SMS', 'MASTERSYSTEM', 'SATURN', 'DREAMCAST', 
                         'DC', 'XBOX', 'ATARI2600', 'ATARI7800']
        
        console_map = {}
        try:
            # Try importing from parent directory (workspace root)
            import sys
            parent_dir = Path(__file__).parent.parent
            sys.path.insert(0, str(parent_dir))
            from download_vimms import CONSOLE_MAP
            console_map = CONSOLE_MAP
            sys.path.remove(str(parent_dir))
        except Exception:
            # Fallback to known console names
            console_map = {name: name for name in known_consoles}
            logger.warning("api_init: could not import CONSOLE_MAP, using fallback console detection")
        
        for child in p.iterdir():
            if child.is_dir():
                name = child.name.upper()  # Normalize to uppercase for comparison
                # Check against known console names (case-insensitive)
                if any(k.upper() == name or k.upper() in name for k in console_map.keys()):
                    consoles.append(child.name)  # Keep original case for display
                    
        logger.info(f"api_init: scanned folder '{p}' and found consoles: {consoles}")
    except Exception:
        logger.exception(f"api_init: error scanning folder '{p}' for consoles")
        consoles = []

    if consoles:
        # Optionally create any configured console folders if requested
        if create_consoles_flag:
            try:
                cfg = None
                cfg_path = Path(__file__).resolve().parent.parent / 'vimms_config.json'
                if cfg_path.exists():
                    with open(cfg_path, 'r', encoding='utf-8') as cf:
                        cfg = json.load(cf)
                if cfg and isinstance(cfg.get('folders'), dict):
                    for key, v in cfg.get('folders', {}).items():
                        # Only create if active (or if user asked to create all via flag)
                        if v.get('active', True):
                            new_dir = p / key
                            if not new_dir.exists():
                                new_dir.mkdir(parents=True, exist_ok=True)
                                logger.info(f"api_init: created configured console folder '{new_dir}'")
            except Exception:
                logger.exception('api_init: failed while creating configured console folders')

        logger.info(f"api_init: returning workspace root with {len(consoles)} consoles for '{p}'")
        return jsonify({'status': 'root', 'root': str(p), 'consoles': consoles})

    # Otherwise treat this as a console folder (or folder with ROMs)
    # Infer system/console from folder path
    detected_system = detect_system_from_path(p)
    global CURRENT_SYSTEM
    CURRENT_SYSTEM = detected_system
    logger.info(f"api_init: detected system '{detected_system}' from folder path '{p}'")
    
    # Prefer 'ROMs' subfolder if present
    roms_dir = p / 'ROMs'
    if roms_dir.exists() and roms_dir.is_dir():
        target_dir = roms_dir
    else:
        target_dir = p

    # Create a downloader instance per folder
    dl = VimmsDownloader(str(target_dir), system=detected_system, detect_existing=True, pre_scan=True)
    DL_INSTANCES[str(target_dir)] = dl
    return jsonify({'status': 'ok', 'folder': str(target_dir)})


# NOTE: /api/sections endpoint - Returns static list of available sections (A-Z, 0-9, #)
# Available for frontend to get section list without hardcoding.
# Currently frontend has SECTIONS hardcoded but this endpoint is available if needed.
@app.route('/api/sections', methods=['GET'])
def api_sections():
    """Return the list of available Vimm's Lair sections (A-Z, 0-9, #)."""
    return jsonify({'sections': SECTIONS})


@app.route('/api/config', methods=['GET'])
def api_config_get():
    """Return the top-level `vimms_config.json` if present."""
    cfg_path = Path(__file__).resolve().parent.parent / 'vimms_config.json'
    if not cfg_path.exists():
        return jsonify({'error': 'config not found'}), 404
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        return jsonify(cfg)
    except Exception as e:
        logger.exception(f"api_config_get: failed to read config: {e}")
        return jsonify({'error': 'failed to read config'}), 500


@app.route('/api/config/default_folders', methods=['GET'])
def api_config_default_folders():
    """Return a list of known console folder names derived from the downloader's CONSOLE_MAP.
    This helps the UI populate a sensible default `folders` mapping when none exists.
    """
    try:
        # Import CONSOLE_MAP from downloader (workspace root)
        import sys
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        from download_vimms import CONSOLE_MAP
        sys.path.remove(str(parent_dir))
        # Use a deterministic ordering
        keys = sorted(CONSOLE_MAP.keys())
        # Build minimal default mapping
        defaults = {k: {'active': True, 'priority': idx + 1} for idx, k in enumerate(keys)}
        return jsonify({'defaults': defaults})
    except Exception as e:
        logger.exception(f"api_config_default_folders: failed to build defaults: {e}")
        return jsonify({'error': 'failed to build default folders'}), 500


@app.route('/api/config/save', methods=['POST'])
def api_config_save():
    """Replace or update `vimms_config.json` with stronger validation and atomic save.

    Expected payload: full config object. A `_force_save` boolean may be provided to
    override strict checks (use with caution).
    """
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'malformed JSON'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'expected JSON object'}), 400

    cfg_path = Path(__file__).resolve().parent.parent / 'vimms_config.json'

    # Basic validation: folders must be a non-empty dict unless _force_save is set
    force_flag = bool(data.get('_force_save', False))
    if (not isinstance(data.get('folders'), dict) or len(data.get('folders') or {}) == 0) and not force_flag:
        return jsonify({'error': 'folders missing or empty; use _force_save to override'}), 400

    # Prevent accidental removal of workspace_root unless explicitly forced
    try:
        existing_cfg = None
        if cfg_path.exists():
            with open(cfg_path, 'r', encoding='utf-8') as f:
                existing_cfg = json.load(f)
        if existing_cfg and 'workspace_root' in existing_cfg:
            if 'workspace_root' not in data or not data.get('workspace_root'):
                if not force_flag:
                    return jsonify({'error': 'workspace_root removal not allowed without _force_save'}), 400
    except Exception as e:
        logger.exception(f"api_config_save: failed to read existing config for validation: {e}")
        return jsonify({'error': 'failed to validate against existing config'}), 500

    # Normalize and validate folders structure
    if 'folders' in data and isinstance(data['folders'], dict):
        sanitized = {}
        for k, v in data['folders'].items():
            if not isinstance(k, str) or not isinstance(v, dict):
                return jsonify({'error': 'invalid folders format'}), 400
            # Ensure priority is int (default large) and active is boolean
            sanitized[k] = {
                'active': bool(v.get('active', True)),
                'priority': int(v.get('priority', 999)),
                **{kk: vv for kk, vv in v.items() if kk not in ('active', 'priority')}
            }
        # Sort by priority
        data['folders'] = dict(sorted(sanitized.items(), key=lambda x: x[1].get('priority', 999)))

    # Do atomic write: write to tmp file then replace
    try:
        import shutil, tempfile, os
        # Create timestamped backup of existing config
        if cfg_path.exists():
            ts = datetime.now().strftime('%Y%m%d%H%M%S')
            bak = cfg_path.with_suffix(f'.{ts}.bak')
            shutil.copy2(cfg_path, bak)
            logger.info(f'api_config_save: backed up config to {bak}')

        # Write to temp file in same directory then replace
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(cfg_path.parent), prefix='vimms_config.', suffix='.tmp')
        try:
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as tf:
                json.dump(data, tf, indent=2)
                tf.flush()
                os.fsync(tf.fileno())
            os.replace(tmp_path, cfg_path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        # Log request context + a small diff (keys added/removed/changed at top level)
        try:
            requester = request.remote_addr or 'local'
            ua = request.headers.get('User-Agent', '')[:200]
            logger.info(f"api_config_save: request from={requester} user_agent={ua} size={len(request.data or b'')} force={force_flag}")

            old_keys = set(existing_cfg.keys()) if existing_cfg else set()
            new_keys = set(data.keys())
            added = new_keys - old_keys
            removed = old_keys - new_keys
            changed = [k for k in new_keys & old_keys if existing_cfg and existing_cfg.get(k) != data.get(k)]
            logger.info(f"api_config_save: saved vimms_config.json (added={list(added)}, removed={list(removed)}, changed={changed})")
        except Exception:
            logger.info('api_config_save: saved vimms_config.json (diff unavailable)')

        return jsonify({'status': 'saved'})
    except Exception as e:
        logger.exception(f"api_config_save: failed to save config: {e}")
        return jsonify({'error': 'failed to save config'}), 500


@app.route('/api/config/create_folders', methods=['POST'])
def api_config_create_folders():
    """Create console folders under a workspace root based on vimms_config.json.

    Payload: { "workspace_root": "H:/Games", "active_only": true }
    Returns list of folders created.
    """
    data = request.json or {}
    root = data.get('workspace_root')
    active_only = bool(data.get('active_only', True))
    if not root:
        return jsonify({'error': 'workspace_root required'}), 400
    cfg_path = Path(__file__).resolve().parent.parent / 'vimms_config.json'
    if not cfg_path.exists():
        return jsonify({'error': 'config not found'}), 404
    created = []
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        for key, v in (cfg.get('folders') or {}).items():
            # Handle case where v might be a string instead of a dict
            if isinstance(v, str):
                continue
            if active_only and not v.get('active', True):
                continue
            new_dir = Path(root) / key
            if not new_dir.exists():
                new_dir.mkdir(parents=True, exist_ok=True)
                created.append(str(new_dir))
                logger.info(f"api_config_create_folders: created {new_dir}")
        return jsonify({'created': created})
    except Exception as e:
        logger.exception(f"api_config_create_folders: failed: {e}")
        return jsonify({'error': 'failed to create folders'}), 500


@app.route('/api/section/<section>', methods=['GET'])
def api_section(section):
    """Get games for a section. Prefers cached index data, falls back to live fetch."""
    global CURRENT_SYSTEM, CACHED_INDEX
    folder = request.args.get('folder')
    
    # Try to use cached index first (much faster and includes present status)
    if CACHED_INDEX and folder:
        # Find the console in the cached index
        for console in CACHED_INDEX.get('consoles', []):
            if console.get('folder') == folder or console.get('name') == folder:
                section_games = console.get('sections', {}).get(section, [])
                if section_games:
                    # Debug: log first game to verify present status
                    if section_games:
                        first = section_games[0]
                        logger.info(f"api_section: first game: {first.get('name')} present={first.get('present')} id={first.get('id')} game_id={first.get('game_id')}")
                    logger.info(f"api_section: returning {len(section_games)} games from cached index for {folder}/{section}")
                    return jsonify({'games': section_games})
    
    # Fall back to live fetch from Vimm's Lair
    dl = None
    if folder:
        # Accept either the exact registered key or try resolved Paths
        if folder in DL_INSTANCES:
            dl = DL_INSTANCES[folder]
        else:
            p = Path(folder)
            # Prefer ROMs subfolder when present
            cand = p / 'ROMs'
            if cand.exists() and cand.is_dir():
                key = str(cand)
            else:
                key = str(p)
            if key in DL_INSTANCES:
                dl = DL_INSTANCES[key]
            else:
                # Infer system from the folder path (fallback when CURRENT_SYSTEM is unknown)
                detected = detect_system_from_path(p)
                try:
                    dl = VimmsDownloader(str(key), system=detected, detect_existing=True, pre_scan=True)
                    DL_INSTANCES[key] = dl
                    logger.info(f"api_section: created temporary downloader for key={key} system={detected}")
                except Exception:
                    # Fall back to a minimal downloader
                    logger.exception(f"api_section: failed to create downloader for key={key} system={detected}")
                    dl = VimmsDownloader('.', system=detected, detect_existing=False, pre_scan=False)
    else:
        detected = detect_system_from_path(Path('.'))
        dl = VimmsDownloader('.', system=detected, detect_existing=False, pre_scan=False)

    games = dl.get_game_list_from_section(section)

    # Annotate games with local presence if we have a downloader with indexing
    annotated = []
    present_count = 0
    for g in games:
        present = False
        try:
            if dl and dl.local_index is not None:
                matches = dl.find_all_matching_files(g['name'])
                present = bool(matches)
                if present:
                    present_count += 1
        except Exception:
            present = False
        annotated.append({**g, 'present': present})

    logger.info(f"api_section: section={section} folder={folder} games={len(games)} present={present_count}")
    return jsonify({'games': annotated})


@app.route('/api/debug/instances', methods=['GET'])
def api_debug_instances():
    """Debug endpoint to show downloader instances."""
    return jsonify({
        'instances': list(DL_INSTANCES.keys()),
        'count': len(DL_INSTANCES)
    })


@app.route('/api/game/<game_id>', methods=['GET'])
def api_game(game_id):
    folder = request.args.get('folder')
    url = f'https://vimm.net/vault/{game_id}'
    
    # Normalize folder path to match DL_INSTANCES keys (Windows uses backslashes)
    if folder:
        folder = str(Path(folder))
    
    dl = DL_INSTANCES.get(folder) if folder else None
    
    # Debug logging
    if not dl:
        logger.warning(f"api_game: no downloader instance for folder='{folder}', available keys: {list(DL_INSTANCES.keys())[:5]}")
    
    # Be robust against test/mocks that may not provide all attributes on the downloader instance
    session_arg = getattr(dl, 'session', None) if dl else None
    
    if dl and not session_arg:
        logger.warning(f"api_game: downloader has no session for folder='{folder}'")
    cache_path_arg = None
    if dl and getattr(dl, 'download_dir', None):
        try:
            cache_path_arg = getattr(dl, 'download_dir') / 'metadata_cache.json'
        except Exception:
            cache_path_arg = None
    logger_arg = getattr(dl, 'logger', None) if dl else None
    pop = None
    if get_game_popularity:
        pop = get_game_popularity(url, session=session_arg, cache_path=cache_path_arg, logger=logger_arg)
    present = False
    files = []
    title = ''
    if dl:
        # We don't have the game name here, attempt to find files by calling find_all_matching_files on title fetched from page
        try:
            # Fetch page title. Be permissive about session.get signature to support
            # simple test doubles that may be implemented as class-level functions.
            s = getattr(dl, 'session', None)
            resp = None
            if s:
                get_fn = getattr(s, 'get', None)
                if get_fn:
                    try:
                        resp = get_fn(url, timeout=10)
                    except TypeError:
                        # Some test doubles define get as a plain function expecting (self, url)
                        try:
                            resp = get_fn(None, url, timeout=10)
                        except TypeError:
                            # Last resort, call without timeout
                            resp = get_fn(url)
            if resp:
                resp.raise_for_status()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                title_el = soup.find('title')
                title = title_el.text.strip() if title_el else ''
                if title:
                    matches = dl.find_all_matching_files(title)
                    present = bool(matches)
                    files = [str(p) for p in matches]
        except Exception:
            pass

    # Prepare popularity dict for JSON responses
    pop_obj = None
    if get_game_popularity and pop:
        score, votes = pop
        pop_obj = {'score': score, 'votes': votes, 'rounded_score': int(round(score))}

    # Try to resolve download URL and fetch size/extension if possible
    size_bytes = None
    extension = None
    try:
        if dl and title:
            # Attempt to find download form on page and resolve URL
            # Re-fetch page if resp not available
            if not resp:
                try:
                    resp = dl.session.get(url, timeout=10)
                except Exception:
                    resp = None
            if resp:
                from downloader_lib.parse import resolve_download_form
                download_url = resolve_download_form(resp.text, dl.session, url, game_id, getattr(dl, 'logger', None))
                if download_url:
                    # HEAD the download URL to get size and filename
                    try:
                        head = dl.session.head(download_url, allow_redirects=True, timeout=10)
                        head.raise_for_status()
                        cl = head.headers.get('Content-Length')
                        if cl:
                            size_bytes = int(cl)
                        cd = head.headers.get('Content-Disposition') or ''
                        # parse filename from content-disposition
                        import re
                        m = re.search(r'filename\*=.*\'\'([^;]+)|filename="?([^\";]+)"?', cd)
                        fname = None
                        if m:
                            fname = (m.group(1) or m.group(2)) if m.group(1) or m.group(2) else None
                        if not fname:
                            # fallback to URL path
                            from urllib.parse import urlparse, unquote
                            p = urlparse(download_url).path
                            fname = unquote(p.split('/')[-1] or '')
                        if fname:
                            import os
                            _, ext = os.path.splitext(fname)
                            if ext:
                                extension = ext.lower()
                    except Exception:
                        pass
    except Exception:
        logger.exception('api_game: error resolving download details')

    logger.info(f"api_game: id={game_id} folder={folder} title='{title[:60]}' present={present} files={len(files)} size={size_bytes} ext={extension}")
    return jsonify({'game_id': game_id, 'title': title, 'popularity': pop_obj, 'present': present, 'files': files, 'size_bytes': size_bytes, 'extension': extension})


@app.route('/api/queue', methods=['POST'])
def api_queue_post():
    """Add item to download queue.
    
    Supports 4 queue types:
    - type='game': { type: 'game', folder, game: {...} }
    - type='section': { type: 'section', folder, section, console_name }
    - type='console': { type: 'console', folder, console_name }
    - type='all': { type: 'all', workspace_root }
    
    For backward compatibility, items without 'type' default to 'game'.
    """
    item = request.json or {}
    
    # Validate based on type
    item_type = item.get('type', 'game')
    
    if item_type == 'all':
        if not item.get('workspace_root'):
            return jsonify({'error': 'workspace_root required for type=all'}), 400
    elif item_type == 'console':
        if not item.get('folder'):
            return jsonify({'error': 'folder required for type=console'}), 400
    elif item_type == 'section':
        if not item.get('folder') or not item.get('section'):
            return jsonify({'error': 'folder and section required for type=section'}), 400
    elif item_type == 'game':
        if not item.get('folder') or not item.get('game'):
            return jsonify({'error': 'folder and game required for type=game'}), 400
    
    task_q.put(item)
    _save_queue_to_disk()
    
    # Log with appropriate detail based on type
    if item_type == 'all':
        logger.info(f"api_queue: queued ALL consoles from workspace={item.get('workspace_root')}")
    elif item_type == 'console':
        logger.info(f"api_queue: queued CONSOLE {item.get('console_name')} folder={item.get('folder')}")
    elif item_type == 'section':
        logger.info(f"api_queue: queued SECTION {item.get('console_name')}/{item.get('section')} folder={item.get('folder')}")
    else:
        logger.info(f"api_queue: queued GAME for folder={item.get('folder')} item={item.get('game', {}).get('name', 'unknown')}")
    
    return jsonify({'status': 'queued', 'type': item_type})


@app.route('/api/queue', methods=['GET'])
def api_queue_get():
    # Return a snapshot of the queue (not destructive)
    items = list(task_q.queue)
    logger.debug(f"api_queue_get: returning {len(items)} items")
    return jsonify({'queue': items})


def api_queue_delete():
    # Clear the queue
    try:
        while not task_q.empty():
            task_q.get_nowait()
        _save_queue_to_disk()
        logger.info('api_queue: cleared queue')
        return jsonify({'status': 'cleared'})
    except Exception:
        logger.exception('api_queue: error clearing queue')
        return jsonify({'status': 'error'})


@app.route('/api/processed', methods=['GET'])
def api_processed():
    return jsonify({'processed': PROCESSED})

@app.route('/api/queue', methods=['DELETE'])
def api_queue_delete():
    # Clear the queue
    try:
        while not task_q.empty():
            task_q.get_nowait()
        _save_queue_to_disk()
        return jsonify({'status': 'cleared'})
    except Exception:
        return jsonify({'status': 'error'})


def worker_loop():
    """Background worker that processes queued download tasks.
    
    Supports 4 queue types:
    - type='game': Download single game (uses VimmsDownloader directly)
    - type='section': Download all games in a section (calls CLI script)
    - type='console': Download all sections for a console (calls CLI script)
    - type='all': Download all active consoles (calls CLI script)
    
    For bulk operations (console/section/all), this calls the CLI scripts
    as subprocesses to ensure identical behavior and leverage existing
    progress tracking, rate limiting, and resume capability.
    """
    global worker_running
    import subprocess
    import sys
    
    # Resolve paths to CLI scripts
    repo_root = Path(__file__).parent.parent
    run_vimms_script = repo_root / 'cli' / 'run_vimms.py'
    download_vimms_script = repo_root / 'cli' / 'download_vimms.py'
    
    worker_running = True
    logger.info('worker_loop: started')
    while True:
        try:
            item = task_q.get()
            logger.info(f"worker_loop: dequeued item: {item}")
            if item is None:
                logger.info('worker_loop: received shutdown sentinel')
                break
            
            # Determine queue item type (default to 'game' for backward compatibility)
            item_type = item.get('type', 'game')
            folder = item.get('folder')
            success = False
            output_lines = []
            
            try:
                # Type 1: Queue All - Run run_vimms.py to process all active consoles
                if item_type == 'all':
                    workspace_root = item.get('workspace_root')
                    logger.info(f"worker_loop: queuing ALL consoles from workspace: {workspace_root}")
                    
                    # Build command: python cli/run_vimms.py --src <workspace_root>
                    cmd = [sys.executable, str(run_vimms_script)]
                    if workspace_root:
                        cmd.extend(['--src', workspace_root])
                    
                    logger.info(f"worker_loop: running command: {' '.join(cmd)}")
                    
                    # Run subprocess and capture output
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    # Stream output line by line
                    for line in process.stdout:
                        output_lines.append(line.rstrip())
                        logger.info(f"[CLI] {line.rstrip()}")
                    
                    process.wait()
                    success = process.returncode == 0
                    logger.info(f"worker_loop: run_vimms.py completed with returncode={process.returncode}")
                
                # Type 2: Queue Console - Run download_vimms.py for all sections
                elif item_type == 'console':
                    console_name = item.get('console_name', 'Unknown')
                    logger.info(f"worker_loop: queuing CONSOLE: {console_name} folder={folder}")
                    
                    # Build command: python cli/download_vimms.py --folder <path>
                    cmd = [sys.executable, str(download_vimms_script), '--folder', folder]
                    
                    logger.info(f"worker_loop: running command: {' '.join(cmd)}")
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    for line in process.stdout:
                        output_lines.append(line.rstrip())
                        logger.info(f"[CLI] {line.rstrip()}")
                    
                    process.wait()
                    success = process.returncode == 0
                    logger.info(f"worker_loop: download_vimms.py completed with returncode={process.returncode}")
                
                # Type 3: Queue Section - Run download_vimms.py for one section
                elif item_type == 'section':
                    section = item.get('section', '')
                    console_name = item.get('console_name', 'Unknown')
                    logger.info(f"worker_loop: queuing SECTION: {console_name}/{section} folder={folder}")
                    
                    # Build command: python cli/download_vimms.py --folder <path> --section-priority <letter>
                    cmd = [sys.executable, str(download_vimms_script), '--folder', folder, '--section-priority', section]
                    
                    logger.info(f"worker_loop: running command: {' '.join(cmd)}")
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    for line in process.stdout:
                        output_lines.append(line.rstrip())
                        logger.info(f"[CLI] {line.rstrip()}")
                    
                    process.wait()
                    success = process.returncode == 0
                    logger.info(f"worker_loop: download_vimms.py completed with returncode={process.returncode}")
                
                # Type 4: Queue Game - Download single game (existing behavior)
                elif item_type == 'game':
                    game = item.get('game')
                    logger.info(f"worker_loop: queuing GAME: {game.get('name') if game else 'Unknown'} folder={folder}")
                    
                    # Find or create downloader for folder
                    dl = DL_INSTANCES.get(folder)
                    if not dl:
                        logger.info(f"worker_loop: creating downloader for folder: {folder}")
                        # Try to infer system from cached index
                        detected_system = 'UNKNOWN'
                        if CACHED_INDEX and 'consoles' in CACHED_INDEX:
                            for console in CACHED_INDEX['consoles']:
                                if console['folder'] == folder:
                                    detected_system = console['system']
                                    logger.info(f"worker_loop: detected system '{detected_system}' from cached index for folder '{folder}'")
                                    break
                        dl = VimmsDownloader(folder, system=detected_system, detect_existing=True, pre_scan=True)
                        DL_INSTANCES[folder] = dl
                    
                    # Download the game
                    if game:
                        logger.info(f"worker_loop: starting download_game for {game.get('name')} (id={game.get('game_id')})")
                        success = dl.download_game(game)
                    else:
                        # Accept minimal {game_id, page_url, name}
                        gid = item.get('game_id')
                        page = item.get('page_url')
                        if gid and page:
                            g = {'game_id': gid, 'page_url': page, 'name': item.get('name', '')}
                            logger.info(f"worker_loop: starting download_game for {g.get('name')} (id={gid}) via page {page}")
                            success = dl.download_game(g)
                
                # Record processed outcome
                record = {
                    'folder': folder,
                    'item': item,
                    'type': item_type,
                    'success': bool(success),
                    'output': output_lines if output_lines else None,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                PROCESSED.insert(0, record)
                # keep last 200
                if len(PROCESSED) > 200:
                    PROCESSED.pop()
                _save_processed_to_disk()
                task_q.task_done()
                logger.info(f"worker_loop: completed item: type={item_type} success={bool(success)} for folder={folder}")
                
            except Exception as e:
                logger.exception('Error in worker loop while processing item')
                # Record the failure
                record = {
                    'folder': folder,
                    'item': item,
                    'type': item_type,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                PROCESSED.insert(0, record)
                if len(PROCESSED) > 200:
                    PROCESSED.pop()
                _save_processed_to_disk()
                task_q.task_done()
                
        except Exception as e:
            logger.exception(f'Worker loop unexpected error: {e}')
    worker_running = False
    logger.info('worker_loop: stopped')


def init_worker():
    global worker_thread, CACHED_INDEX
    # Load queue persisted on disk
    _load_queue_from_disk()
    # Load processed history
    _load_processed_from_disk()
    
    # Load cached index if exists
    index_incomplete = False
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                CACHED_INDEX = json.load(f)
            logger.info(f"init_worker: loaded cached index with {len(CACHED_INDEX.get('consoles', []))} consoles")
            
            # Check if index is incomplete (build was interrupted)
            if CACHED_INDEX.get('complete') == False:
                index_incomplete = True
                workspace_root = CACHED_INDEX.get('workspace_root')
                if workspace_root:
                    logger.info(f"init_worker: index incomplete, auto-starting rebuild for '{workspace_root}'")
                    # Start rebuild in background thread
                    def auto_rebuild():
                        with app.app_context():
                            try:
                                api_index_build_internal(workspace_root)
                            except Exception as e:
                                logger.exception(f"init_worker: auto-rebuild failed: {e}")
                    t_rebuild = Thread(target=auto_rebuild, daemon=True)
                    t_rebuild.start()
        except Exception as e:
            logger.warning(f"init_worker: failed to load cached index: {e}")
    else:
        # No index file exists - try to infer workspace root and auto-build
        logger.info("init_worker: no index file found")
        workspace_root = None
        
        # Try to infer from queue items (which have full folder paths)
        if not task_q.empty():
            try:
                # Peek at first queue item to get a folder path
                queue_list = list(task_q.queue)
                if queue_list:
                    first_item = queue_list[0]
                    folder_path = first_item.get('folder', '')
                    if folder_path:
                        # folder_path is like "H:\Games\DS\ROMs" or "H:\Games\DS"
                        # We want the parent of the console folder (H:\Games)
                        console_path = Path(folder_path)
                        # If it ends with ROMs, go up two levels, otherwise one
                        if console_path.name == 'ROMs':
                            workspace_root = str(console_path.parent.parent)
                        else:
                            workspace_root = str(console_path.parent)
                        logger.info(f"init_worker: inferred workspace root '{workspace_root}' from queue")
            except Exception as e:
                logger.warning(f"init_worker: failed to infer workspace from queue: {e}")
        
        # Fall back to config file
        if not workspace_root:
            config_file = Path(__file__).parent.parent / 'vimms_config.json'
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    # Look for an explicit workspace_root field in config
                    workspace_root = config.get('workspace_root')
                    if workspace_root:
                        logger.info(f"init_worker: got workspace root '{workspace_root}' from config")
                except Exception as e:
                    logger.warning(f"init_worker: failed to read config: {e}")
        
        # Start auto-build if we have a workspace root
        if workspace_root and Path(workspace_root).exists():
            logger.info(f"init_worker: auto-starting build for '{workspace_root}'")
            def auto_build():
                with app.app_context():
                    try:
                        api_index_build_internal(workspace_root)
                    except Exception as e:
                        logger.exception(f"init_worker: auto-build failed: {e}")
            t_build = Thread(target=auto_build, daemon=True)
            t_build.start()
        else:
            logger.info("init_worker: could not infer workspace root for auto-build")
    
    logger.info(f"init_worker: loaded queue with {task_q.qsize()} items and {len(PROCESSED)} processed records")
    # ensure worker directory exists
    if not worker_thread:
        t = Thread(target=worker_loop, daemon=True)
        t.start()
        worker_thread = t
        logger.info('init_worker: worker thread started')

# Initialize worker when module is loaded
init_worker()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
