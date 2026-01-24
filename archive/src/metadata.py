"""Metadata extraction helpers (popularity/rating) for Vimm's Lair games."""
from typing import Optional, Tuple
from bs4 import BeautifulSoup
import requests
import re
import json
from pathlib import Path


def _parse_popularity_from_html(html: str) -> Optional[Tuple[float, int]]:
    """Parse numeric score and votes from a game page HTML.

    Returns (score: float, votes: int) or None if not found.
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Common pattern: text containing 'Overall' followed by a numeric score and vote count
    text = soup.get_text(separator=' ', strip=True)
    m = re.search(r'Overall\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*\(?([0-9]+)?\s*votes?\)?', text, re.IGNORECASE)
    if m:
        score = float(m.group(1))
        votes = int(m.group(2)) if m.group(2) else 0
        return (score, votes)

    # Fallback: look for 'Overall <score>' without votes
    m2 = re.search(r'Overall\s*:?\s*([0-9]+(?:\.[0-9]+)?)', text, re.IGNORECASE)
    if m2:
        score = float(m2.group(1))
        return (score, 0)

    # Fallback: look for 'Rating: X / 10' or similar
    m3 = re.search(r'Rating\s*:?\s*([0-9]+(?:\.[0-9]+)?)', text, re.IGNORECASE)
    if m3:
        score = float(m3.group(1))
        return (score, 0)

    return None


def score_to_stars(score: float) -> int:
    """Map a 0-10 score to 1-5 star bucket."""
    s = max(0.0, min(10.0, float(score)))
    if s < 2.0:
        return 1
    if s < 4.0:
        return 2
    if s < 6.0:
        return 3
    if s < 8.0:
        return 4
    return 5


def get_game_popularity(html_or_url: str, session: Optional[requests.Session] = None, cache_path: Optional[Path] = None, logger=None) -> Optional[Tuple[float, int]]:
    """Get popularity (score, votes) from either raw HTML or a URL.

    If `cache_path` is provided and contains data for the URL, that will be used.
    """
    is_html = '<html' in (html_or_url or '').lower()
    html = None

    # If it's a URL, optionally check cache then fetch
    if not is_html:
        url = html_or_url
        # Load from cache if present
        if cache_path and cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                if url in cache:
                    entry = cache[url]
                    return (entry.get('score'), int(entry.get('votes', 0)))
            except Exception:
                if logger:
                    logger.exception('Error reading metadata cache')
        # Fetch the page
        try:
            if session is None:
                session = requests.Session()
            resp = session.get(url, timeout=10)
            resp.raise_for_status()
            html = resp.text
        except Exception:
            if logger:
                logger.exception(f'Could not fetch game page for popularity: {html_or_url}')
            return None
    else:
        html = html_or_url

    parsed = _parse_popularity_from_html(html)
    if parsed and cache_path and not is_html:
        try:
            cache = {}
            if cache_path.exists():
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            cache[url] = {'score': parsed[0], 'votes': parsed[1]}
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2)
        except Exception:
            if logger:
                logger.exception('Could not write metadata cache')

    return parsed
