"""HTML parsing helpers for Vimm's Lair downloader."""
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
import requests

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
                if logger: logger..info(f"Resolved download URL via form action (GET) for {game_id}: {action_url}")
                return action_url
            else: # POST
                try:
                    headers_post = {'User-Agent': session.headers.get('User-Agent'), 'Referer': game_page_url}
                    if logger: logger.info(f"Submitting POST form to {action_url} for {game_id} with params {params}")
                    resp = session.post(action_url, data=params, headers=headers_post, verify=False, allow_redirects=True)
                    if resp and resp.url:
                        if logger: logger.info(f"POST form resolved to URL for {game_id}: {resp.url}")
                        return resp.url
                except Exception:
                    new_q = urlencode(params, doseq=False)
                    action_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment))
                    if logger: logger.exception(f"POST form submission failed for {game_id}, falling back to GET-like URL: {action_url}")
                    return action_url

    # Fallbacks if form parsing fails
    a = soup.find('a', href=re.compile(r'mediaId=', re.IGNORECASE))
    if a and a.get('href'):
        resolved = urljoin(BASE_URL + '/', a.get('href'))
        if logger: logger.info(f"Resolved download URL via anchor for {game_id}: {resolved}")
        return resolved

    if not media_id:
        alt = soup.find('input', attrs={'name': re.compile(r'^mediaId$', re.I)})
        media_id = alt.get('value') if alt else None
    if media_id:
        fallback = f"{DOWNLOAD_BASE}/?mediaId={media_id}"
        if logger: logger.info(f"Fallback constructed download URL for {game_id}: {fallback}")
        return fallback

    return None
