"""Minimal FastAPI web UI for browsing and queuing Vimm downloads."""
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from threading import Thread
import queue
import time
from src.download_vimms import VimmsDownloader
from src.metadata import get_game_popularity, score_to_stars
from pathlib import Path
import logging

app = FastAPI(title='Vimms Downloader UI')
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / 'webui_templates'))
app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'webui_static')), name='static')

# Simple in-memory queue for download tasks
task_q = queue.Queue()
worker_thread = None
worker_running = False
QUEUE_FILE = BASE_DIR / 'webui_queue.json'
PROCESSED_FILE = BASE_DIR / 'webui_processed.json'

# Simple global state for downloader instance per-root folder
DL_INSTANCES = {}

# Keep recent processed records in memory for quick access
PROCESSED = []

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


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.post('/api/init')
def api_init(data: dict):
    """Initialize downloader for a given folder path.

    If the provided folder is a workspace root containing console subfolders, return
    the list of console candidate subfolders so the UI can let the user pick one.
    Otherwise create a `VimmsDownloader` instance for that console folder.
    """
    folder = data.get('folder')
    if not folder:
        return JSONResponse({'error': 'folder required'}, status_code=400)
    p = Path(folder)
    if not p.exists():
        return JSONResponse({'error': 'folder not found'}, status_code=404)

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
    except Exception:
        # ignore iteration errors
        consoles = []

    if consoles:
        return {'status': 'root', 'root': str(p), 'consoles': consoles}

    # Otherwise treat this as a console folder (or folder with ROMs)
    # Prefer 'ROMs' subfolder if present
    roms_dir = p / 'ROMs'
    if roms_dir.exists() and roms_dir.is_dir():
        target_dir = roms_dir
    else:
        target_dir = p

    # Create a downloader instance per folder
    dl = VimmsDownloader(str(target_dir), system='UNKNOWN', detect_existing=True, pre_scan=True)
    DL_INSTANCES[str(target_dir)] = dl
    return {'status': 'ok', 'folder': str(target_dir)}


@app.get('/api/sections')
def api_sections():
    from src.download_vimms import SECTIONS
    return {'sections': SECTIONS}


@app.get('/api/section/{section}')
def api_section(section: str, folder: str = None):
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
                # Create a temporary downloader with pre-scan enabled to detect local files
                try:
                    dl = VimmsDownloader(str(key), system='UNKNOWN', detect_existing=True, pre_scan=True)
                    DL_INSTANCES[key] = dl
                except Exception:
                    dl = VimmsDownloader('.', system='UNKNOWN', detect_existing=False, pre_scan=False)
    else:
        dl = VimmsDownloader('.', system='UNKNOWN', detect_existing=False, pre_scan=False)

    games = dl.get_game_list_from_section(section)

    # Annotate games with local presence if we have a downloader with indexing
    annotated = []
    for g in games:
        present = False
        try:
            if dl and dl.local_index is not None:
                matches = dl.find_all_matching_files(g['name'])
                present = bool(matches)
        except Exception:
            present = False
        annotated.append({**g, 'present': present})

    return {'games': annotated}


@app.get('/api/game/{game_id}')
def api_game(game_id: str, folder: str = None):
    url = f'https://vimm.net/vault/{game_id}'
    dl = DL_INSTANCES.get(folder) if folder else None
    pop = get_game_popularity(url, session=(dl.session if dl else None), cache_path=(dl.download_dir / 'metadata_cache.json' if dl else None), logger=(dl.logger if dl else None))
    present = False
    files = []
    title = ''
    if dl:
        # We don't have the game name here, attempt to find files by calling find_all_matching_files on title fetched from page
        try:
            # Fetch page title
            resp = dl.session.get(url, timeout=10)
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
    if pop:
        score, votes = pop
        pop_obj = {'score': score, 'votes': votes, 'rounded_score': int(round(score))}

    return {'game_id': game_id, 'title': title, 'popularity': pop_obj, 'present': present, 'files': files}


@app.post('/api/queue')
def api_queue(item: dict):
    # item should contain folder and game dict or game_id and optionally page_url/name
    task_q.put(item)
    _save_queue_to_disk()
    return {'status': 'queued'}


@app.get('/api/queue')
def api_queue_list():
    # Return a snapshot of the queue (not destructive)
    items = list(task_q.queue)
    return {'queue': items}


@app.get('/api/processed')
def api_processed():
    return {'processed': PROCESSED}

@app.delete('/api/queue')
def api_queue_clear():
    # Clear the queue
    try:
        while not task_q.empty():
            task_q.get_nowait()
        _save_queue_to_disk()
        return {'status': 'cleared'}
    except Exception:
        return {'status': 'error'}


def worker_loop():
    global worker_running
    worker_running = True
    while True:
        try:
            item = task_q.get()
            if item is None:
                break
            folder = item.get('folder')
            game = item.get('game')
            # Find or create downloader for folder
            dl = DL_INSTANCES.get(folder)
            if not dl:
                dl = VimmsDownloader(folder, system='UNKNOWN', detect_existing=True, pre_scan=True)
                DL_INSTANCES[folder] = dl
            # If game has game_id and page_url, directly call download_game
            success = False
            try:
                if game:
                    success = dl.download_game(game)
                else:
                    # Accept minimal {game_id, page_url, name}
                    gid = item.get('game_id')
                    page = item.get('page_url')
                    if gid and page:
                        g = {'game_id': gid, 'page_url': page, 'name': item.get('name', '')}
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
            except Exception as e:
                logger.exception('Error in worker loop')
        except Exception as e:
            logger.exception(f'Worker loop unexpected error: {e}')
    worker_running = False


@app.on_event('startup')
def startup():
    global worker_thread
    # Load queue persisted on disk
    _load_queue_from_disk()
    # Load processed history
    _load_processed_from_disk()
    # ensure worker directory exists
    if not worker_thread:
        t = Thread(target=worker_loop, daemon=True)
        t.start()
        worker_thread = t


@app.on_event('shutdown')
def shutdown():
    # Stop worker
    try:
        task_q.put(None)
        if worker_thread:
            worker_thread.join(timeout=1)
    except Exception:
        pass
