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

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.download_vimms import VimmsDownloader, CONSOLE_MAP, SECTIONS

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
from src.download_vimms import CONSOLE_MAP

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
    
    # Scan for console folders
    from src.download_vimms import CONSOLE_MAP
    console_folders = []
    for child in root_path.iterdir():
        if child.is_dir() and child.name in CONSOLE_MAP:
            console_folders.append(child)
    
    if not console_folders:
        return jsonify({'error': 'No console folders found in workspace root'}), 404
    
    # Initialize progress
    INDEX_PROGRESS['in_progress'] = True
    INDEX_PROGRESS['consoles_total'] = len(console_folders)
    INDEX_PROGRESS['consoles_done'] = 0
    INDEX_PROGRESS['sections_total'] = len(SECTIONS)
    INDEX_PROGRESS['sections_done'] = 0
    INDEX_PROGRESS['games_found'] = 0
    INDEX_PROGRESS['partial_consoles'] = []
    
    logger.info(f"api_index_build: found {len(console_folders)} console folders: {[c.name for c in console_folders]}")
    
    # Build index
    index_data = {
        'workspace_root': str(root_path),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'consoles': [],
        'complete': False  # Mark as incomplete until build finishes
    }
    
    total_games = 0
    for console_folder in console_folders:
        console_name = console_folder.name
        system = CONSOLE_MAP.get(console_name, console_name)
        
        # Update progress
        INDEX_PROGRESS['current_console'] = console_name
        INDEX_PROGRESS['sections_done'] = 0
        
        # Prefer ROMs subfolder
        roms_folder = console_folder / 'ROMs'
        target_folder = roms_folder if roms_folder.exists() else console_folder
        
        logger.info(f"api_index_build: scanning console '{console_name}' at '{target_folder}'")
        
        try:
            # Create downloader with pre_scan to build local index
            dl = VimmsDownloader(str(target_folder), system=system, detect_existing=True, pre_scan=True)
            DL_INSTANCES[str(target_folder)] = dl
            
            # Scan all sections
            sections_data = {}
            for idx, section in enumerate(SECTIONS):
                INDEX_PROGRESS['current_section'] = section
                INDEX_PROGRESS['sections_done'] = idx
                try:
                    games = dl.get_game_list_from_section(section)
                    
                    # Annotate with local presence
                    annotated_games = []
                    for game in games:
                        present = False
                        try:
                            if dl.local_index is not None:
                                matches = dl.find_all_matching_files(game['name'])
                                present = bool(matches)
                        except Exception:
                            pass
                        
                        annotated_games.append({
                            'id': game.get('id', ''),
                            'name': game.get('name', ''),
                            'url': game.get('url', ''),
                            'present': present
                        })
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
                'sections': sections_data
            }
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
    """Get current progress of index build operation."""
    return jsonify(INDEX_PROGRESS)


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
        
        return jsonify(CACHED_INDEX)
    except Exception as e:
        logger.exception(f"api_index_get: error loading index file: {e}")
        return jsonify({'error': 'Failed to load index file'}), 500


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
    # Just reuse the build logic
    request.json = {'workspace_root': workspace_root}
    return api_index_build()


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
    if not p.exists():
        return jsonify({'error': 'folder not found'}), 404

    # If folder appears to be a workspace root (contains possible console folders), return candidates
    consoles = []
    try:
        for child in p.iterdir():
            if child.is_dir():
                name = child.name
                # Simple match against known consoles (case-insensitive)
                from src.download_vimms import CONSOLE_MAP
                if any(k.lower() in name.lower() for k in CONSOLE_MAP.keys()):
                    consoles.append(name)
        logger.info(f"api_init: scanned folder '{p}' and found consoles: {consoles}")
    except Exception:
        logger.exception(f"api_init: error scanning folder '{p}' for consoles")
        consoles = []

    if consoles:
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


@app.route('/api/sections', methods=['GET'])
def api_sections():
    return jsonify({'sections': SECTIONS})


@app.route('/api/section/<section>', methods=['GET'])
def api_section(section):
    global CURRENT_SYSTEM
    folder = request.args.get('folder')
    # Fetch games in a section using the downloader instance if initialized, otherwise create a temporary one
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


@app.route('/api/game/<game_id>', methods=['GET'])
def api_game(game_id):
    folder = request.args.get('folder')
    url = f'https://vimm.net/vault/{game_id}'
    dl = DL_INSTANCES.get(folder) if folder else None
    # Be robust against test/mocks that may not provide all attributes on the downloader instance
    session_arg = getattr(dl, 'session', None) if dl else None
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

    logger.info(f"api_game: id={game_id} folder={folder} title='{title[:60]}' present={present} files={len(files)}")
    return jsonify({'game_id': game_id, 'title': title, 'popularity': pop_obj, 'present': present, 'files': files})


@app.route('/api/queue', methods=['POST'])
def api_queue_post():
    # item should contain folder and game dict or game_id and optionally page_url/name
    item = request.json or {}
    task_q.put(item)
    _save_queue_to_disk()
    logger.info(f"api_queue: queued item for folder={item.get('folder')} item={item.get('game') or item.get('game_id')}" )
    return jsonify({'status': 'queued'})


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
    global worker_running
    worker_running = True
    logger.info('worker_loop: started')
    while True:
        try:
            item = task_q.get()
            logger.info(f"worker_loop: dequeued item: {item}")
            if item is None:
                logger.info('worker_loop: received shutdown sentinel')
                break
            folder = item.get('folder')
            game = item.get('game')
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
            # If game has game_id and page_url, directly call download_game
            success = False
            try:
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
                    'success': bool(success),
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                PROCESSED.insert(0, record)
                # keep last 200
                if len(PROCESSED) > 200:
                    PROCESSED.pop()
                _save_processed_to_disk()
                task_q.task_done()
                logger.info(f"worker_loop: completed item: success={bool(success)} for folder={folder}")
            except Exception as e:
                logger.exception('Error in worker loop while processing item')
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
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                CACHED_INDEX = json.load(f)
            logger.info(f"init_worker: loaded cached index with {len(CACHED_INDEX.get('consoles', []))} consoles")
        except Exception as e:
            logger.warning(f"init_worker: failed to load cached index: {e}")
    
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
