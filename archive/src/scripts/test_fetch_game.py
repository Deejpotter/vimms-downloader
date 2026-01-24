"""Small helper to fetch a single Vimm's Lair game page and capture logs for form resolution.

Usage:
    python scripts/test_fetch_game.py --id 7726
    python scripts/test_fetch_game.py --url https://vimm.net/vault/7726

Outputs a log file under ./logs/test_fetch_<id>.log with request/response details.
"""
import argparse
import logging
from pathlib import Path
import sys
# Ensure repo root is on sys.path when executed directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests
from downloader_lib.fetch import fetch_game_page
from downloader_lib.parse import resolve_download_form
import random
from utils.constants import USER_AGENTS

LOGS = Path('logs')
LOGS.mkdir(exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument('--id', help='Game id (numeric part of /vault/<id>)')
parser.add_argument('--url', help='Full game page URL (overrides --id)')
parser.add_argument('--outfile', help='Path to log file (overrides default)')
args = parser.parse_args()

if args.url:
    url = args.url
elif args.id:
    url = f"https://vimm.net/vault/{args.id}"
else:
    parser.error('Provide --id or --url')

game_id = args.id or url.rstrip('/').split('/')[-1]
logfile = Path(args.outfile) if args.outfile else LOGS / f"test_fetch_{game_id}.log"

logger = logging.getLogger('test_fetch')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(logfile, encoding='utf-8')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(ch)

sess = requests.Session()
sess.headers.update({'User-Agent': random.choice(USER_AGENTS)})

logger.info(f"Fetching game page: {url}")
try:
    resp = fetch_game_page(sess, url)
    logger.info(f"Fetched game page: status={resp.status_code} url={resp.url}")
    page_text = resp.text
except Exception as e:
    logger.exception('Failed to fetch game page')
    raise SystemExit(1)

logger.info('Resolving download form (this may attempt POST/GET and mirrors)')
resolved = resolve_download_form(page_text, sess, url, game_id, logger=logger)
logger.info(f"Final resolved URL: {resolved}")

# Optional: probe the resolved URL to confirm file availability without saving
try:
    if resolved:
        logger.info('Probing resolved URL with HEAD request')
        head = sess.head(resolved, allow_redirects=True, verify=False)
        logger.info(f'HEAD status={getattr(head, "status_code", None)} headers={dict(getattr(head, "headers", {}))}')
        if not head or not getattr(head, 'status_code', 0) or head.status_code >= 400 or 'Content-Length' not in getattr(head, 'headers', {}):
            logger.info('HEAD not sufficient, performing small GET to probe content')
            getr = sess.get(resolved, stream=True, verify=False)
            logger.info(f'GET status={getr.status_code} headers={dict(getr.headers)}')
            # read first 1024 bytes to confirm response body
            try:
                chunk = next(getr.iter_content(1024))
                logger.info(f'Read probe chunk length={len(chunk)}')
            except StopIteration:
                logger.info('No body received during probe GET')
            finally:
                try:
                    getr.close()
                except Exception:
                    pass
except Exception:
    logger.exception('Error while probing resolved URL')

logger.info(f"Final resolved URL: {resolved}")
print(f"Log written: {logfile}")