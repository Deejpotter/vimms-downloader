"""HTML parsing helpers for Vimm's Lair downloader."""
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
import requests

BASE_URL = "https://vimm.net"
DOWNLOAD_BASE = "https://dl2.vimm.net"

def parse_game_details(html_content: str) -> Dict[str, any]:
    """Parse game details (size, format, rating) from game page HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    details = {}
    
    # Find size and format in the download form or nearby text
    size_match = re.search(r'([0-9.]+)\s*(MB|GB|KB)', html_content, re.IGNORECASE)
    if size_match:
        size_value = float(size_match.group(1))
        size_unit = size_match.group(2).upper()
        # Convert to bytes
        multipliers = {'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
        details['size_bytes'] = int(size_value * multipliers.get(size_unit, 1))
        details['size_display'] = f"{size_match.group(1)} {size_unit}"
    
    # Find format/extension from mediaId or file type indicators
    format_match = re.search(r'\.([a-z0-9]{2,5})\b', html_content, re.IGNORECASE)
    if format_match:
        details['extension'] = format_match.group(1).lower()
    
    # Find rating (star icons or score)
    rating_container = soup.find('div', class_=re.compile(r'rating|score', re.I))
    if rating_container:
        stars = len(rating_container.find_all('img', src=re.compile(r'star', re.I)))
        if stars > 0:
            details['rating'] = stars
    else:
        # Look for text-based rating
        rating_text = re.search(r'(\d+(\.\d+)?)\s*(?:out of|/)\s*\d+', html_content)
        if rating_text:
            details['rating'] = float(rating_text.group(1))
    
    return details

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
                if logger: logger.info(f"Resolved download URL via form action (GET) for {game_id}: {action_url}")
                return action_url
            else: # POST
                # For POST forms, extract the mediaId and construct a direct download URL
                # The server expects a GET request to the download URL with cookies from visiting the game page
                media_id = params.get('mediaId')
                if media_id:
                    # Use the action URL's netloc (dl3.vimm.net, etc.) with mediaId as query param
                    download_url = f"{parsed.scheme}://{parsed.netloc}/?mediaId={media_id}"
                    # Include alt parameter if present
                    if 'alt' in params:
                        download_url += f"&alt={params['alt']}"
                    if logger: logger.info(f"Constructed download URL from POST form for {game_id}: {download_url}")
                    return download_url

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
