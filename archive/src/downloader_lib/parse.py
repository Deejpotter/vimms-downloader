"""HTML parsing helpers for Vimm's Lair downloader."""
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
import requests
import os

BASE_URL = "https://vimm.net"
DOWNLOAD_BASE = "https://dl2.vimm.net"

def parse_games_from_section(html_content: str, section: str) -> List[Dict[str, str]]:
    """Parse a list of games from the HTML of a section page."""
    games = []
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'class': 'rounded centered cellpadding1 hovertable striped'})
    if not table:
        return []

    rows = table.find_all('tr')
    for row in rows:
        first_td = row.find('td')
        if first_td:
            link = first_td.find('a')
            if link:
                name = link.text.strip()
                href = link.get('href')
                if not href:
                    continue
                if isinstance(href, (list, tuple)):
                    href = href[0]
                href = str(href)
                game_id = href.split('/')[-1]
                page_url = BASE_URL + href
                games.append({
                    'name': name,
                    'page_url': page_url,
                    'game_id': game_id,
                    'section': section
                })
    return games

def resolve_download_form(html_content: str, session: requests.Session, game_page_url: str, game_id: str, logger) -> Optional[str]:
    """Find the download form and resolve the final download URL, handling POSTs."""
    soup = BeautifulSoup(html_content, 'html.parser')
    dl_form = soup.find(id='dl_form') or soup.find('form', attrs={'id': 'dl_form'})

    media_id = None
    if dl_form:
        # Log discovered form details for debugging (action, method, inputs)
        try:
            form_method = (dl_form.get('method') or 'GET').upper()
            form_action = (dl_form.get('action') or '').strip()
            inputs_info = []
            for inp in dl_form.find_all('input'):
                inputs_info.append({
                    'name': inp.get('name'),
                    'value': inp.get('value'),
                    'disabled': bool(inp.get('disabled'))
                })
            if logger:
                logger.info(f"Found download form for {game_id}: method={form_method}, action={form_action}, inputs={inputs_info}")
        except Exception:
            if logger:
                logger.exception(f"Error logging download form for {game_id}")

        media_input = dl_form.find('input', attrs={'name': 'mediaId'}) or dl_form.find('input', attrs={'name': re.compile(r'^mediaId$', re.I)})
        if media_input:
            media_id = media_input.get('value')

        action = (dl_form.get('action') or '').strip()
        params = {inp.get('name'): inp.get('value') for inp in dl_form.find_all('input') if inp.get('name') and inp.get('value') is not None}
        if media_id and 'mediaId' not in params:
            params['mediaId'] = media_id

        if action:
            action_url = urljoin(BASE_URL + '/', action)
            method = (dl_form.get('method') or 'get').lower()
            parsed = urlparse(action_url)
            q = parse_qs(parsed.query)
            for k, v in list(q.items()):
                if k not in params and isinstance(v, list) and v:
                    params[k] = v[-1]

            if method == 'get':
                new_q = urlencode(params, doseq=False)
                action_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment))
                if logger: logger.info(f"Resolved download URL via form action (GET) for {game_id}: {action_url}")
                return action_url
            else: # POST
                try:
                    # Build richer browser-like headers; prefer session User-Agent when present
                    ua = None
                    if getattr(session, 'headers', None):
                        ua = session.headers.get('User-Agent')
                    if not ua:
                        try:
                            from utils.constants import USER_AGENTS
                            ua = USER_AGENTS[0]
                        except Exception:
                            ua = 'python-requests/unknown'

                    # Decide Sec-Fetch-Site: often 'same-site' for vimm/dl hosts
                    sec_fetch_site = 'same-site'
                    # Build headers used for both POST and GET attempts
                    base_headers = {
                        'User-Agent': ua,
                        'Referer': game_page_url,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': sec_fetch_site,
                        'Sec-Fetch-User': '?1',
                        # CH UA hints (not required to be exact)
                        'Sec-CH-UA': '"Chromium";v="143", "Google Chrome";v="143", "Not A(Brand";v="24"',
                        'Sec-CH-UA-Mobile': '?0',
                        'Sec-CH-UA-Platform': '"Windows"',
                    }

                    # For POST include Origin and Host
                    try:
                        origin = f"{parsed.scheme}://{parsed.netloc}"
                        headers_post = dict(base_headers)
                        headers_post['Origin'] = origin
                        headers_post['Host'] = parsed.netloc
                    except Exception:
                        headers_post = dict(base_headers)

                    if logger: logger.info(f"Submitting POST form to {action_url} for {game_id} with params {params}")
                    # Use streaming requests to avoid downloading large content during resolution
                    resp = session.post(action_url, data=params, headers=headers_post, verify=False, allow_redirects=True, stream=True, timeout=10)
                    # If POST returns a workable URL or successful status, prefer it
                    if resp and getattr(resp, 'status_code', None) and 200 <= resp.status_code < 400 and getattr(resp, 'url', None):
                        if logger: logger.info(f"POST form resolved to URL for {game_id}: {resp.url}")
                        try:
                            resp.close()
                        except Exception:
                            pass
                        return resp.url

                    # POST didn't succeed — try GET fallback by encoding params into query string
                    new_q = urlencode(params, doseq=False)
                    action_get = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment))
                    if logger: logger.warning(f"POST form did not return usable URL for {game_id} (status={getattr(resp,'status_code',None)}); trying GET fallback {action_get}")

                    headers_get = dict(base_headers)
                    headers_get['Host'] = parsed.netloc
                    try:
                        resp_get = session.get(action_get, headers=headers_get, verify=False, allow_redirects=True, stream=True, timeout=10)
                        if resp_get and getattr(resp_get, 'status_code', None) and 200 <= resp_get.status_code < 400:
                            if logger: logger.info(f"GET fallback returned URL for {game_id}: {getattr(resp_get, 'url', action_get)}")
                            try:
                                resp_get.close()
                            except Exception:
                                pass
                            return getattr(resp_get, 'url', action_get)
                    except Exception:
                        if logger: logger.exception(f"GET fallback failed for {game_id} at {action_get}")

                    # Try alternate mirrors if GET to original host fails
                    mirrors = ['dl3.vimm.net', 'dl2.vimm.net', 'dl1.vimm.net']
                    original = parsed.netloc
                    for m in mirrors:
                        if m == original:
                            continue
                        mirror_url = urlunparse((parsed.scheme, m, parsed.path, parsed.params, new_q, parsed.fragment))
                        if logger: logger.info(f"Trying mirror {mirror_url} for {game_id}")
                        try:
                            r = session.get(mirror_url, headers=headers_get, verify=False, allow_redirects=True, stream=True, timeout=10)
                            if r and getattr(r, 'status_code', None) and 200 <= r.status_code < 400:
                                if logger: logger.info(f"Mirror {m} returned URL for {game_id}: {getattr(r,'url', mirror_url)}")
                                try:
                                    r.close()
                                except Exception:
                                    pass
                                return getattr(r, 'url', mirror_url)
                        except Exception:
                            if logger: logger.exception(f"Error trying mirror {m} for {game_id}")

                    # All attempts failed; return the GET-like URL as a best-effort fallback
                    if logger: logger.warning(f"All form submission attempts failed for {game_id}; returning GET-like URL {action_get}")
                    return action_get
                except Exception:
                    new_q = urlencode(params, doseq=False)
                    action_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment))
                    if logger: logger.exception(f"POST form submission raised exception for {game_id}, falling back to GET-like URL: {action_url}")
                    return action_url

    # Fallbacks if form parsing fails
    # Collect candidate anchors that appear to reference media downloads
    candidates = []
    for a in soup.find_all('a', href=True):
        href = a.get('href')
        if not href:
            continue
        if re.search(r'mediaId=', href, re.IGNORECASE) or re.search(r'\.(ciso|rvz|iso|gcm)($|\?)', href, re.IGNORECASE):
            resolved = urljoin(BASE_URL + '/', href)
            # Try to infer extension from anchor text or href
            text = (a.get_text(strip=True) or '').lower()
            ext = None
            if '.' in text:
                ext = os.path.splitext(text)[1].lower()
            if not ext:
                m = re.search(r'\.(ciso|rvz|iso|gcm)($|\?)', href, re.IGNORECASE)
                if m:
                    ext = m.group(0).lower().split('?')[0]
            candidates.append((resolved, ext))

    # Prefer .ciso if present, then .rvz, otherwise return first candidate
    if candidates:
        pref = ['.ciso', '.rvz']
        for p in pref:
            for url, ext in candidates:
                if ext == p:
                    if logger: logger.info(f"Resolved download URL via preferred anchor for {game_id}: {url} (matched {p})")
                    return url
        # No preferred ext found; return first candidate
        if logger: logger.info(f"Resolved download URL via anchor for {game_id}: {candidates[0][0]}")
        return candidates[0][0]

    if not media_id:
        alt = soup.find('input', attrs={'name': re.compile(r'^mediaId$', re.I)})
        media_id = alt.get('value') if alt else None
    if media_id:
        fallback = f"{DOWNLOAD_BASE}/?mediaId={media_id}"
        if logger: logger.info(f"Fallback constructed download URL for {game_id}: {fallback}")
        return fallback

    return None
