"""Metadata fetching for individual game details from Vimm's Lair.

Provides functions to fetch and cache game popularity (rating) and other metadata
from individual game pages. Used when section page ratings are unavailable or for
real-time lookups during downloads.
"""
import json
import logging
from pathlib import Path
from typing import Optional, Tuple
import requests
from downloader_lib.parse import parse_game_details


def get_game_popularity(url: str, session: Optional[requests.Session] = None, 
                       cache_path: Optional[Path] = None,
                       logger: Optional[logging.Logger] = None) -> Optional[Tuple[float, int]]:
    """Fetch game popularity (overall rating and star rating) from Vimm game page.
    
    Args:
        url: Full URL to game page (e.g., https://vimm.net/vault/12345)
        session: Optional requests Session for connection pooling
        cache_path: Optional path to metadata_cache.json for persistent caching
        logger: Optional logger for diagnostics
        
    Returns:
        Tuple of (overall_rating, stars) where overall_rating is a float (e.g., 8.62)
        and stars is an integer (1-5). Returns None if rating cannot be fetched.
    """
    # Try cache first if provided
    game_id = url.split('/')[-1]
    if cache_path and cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            cached_entry = cache.get(game_id)
            if cached_entry and 'rating' in cached_entry:
                if logger:
                    logger.debug(f"get_game_popularity: cache hit for {game_id} -> {cached_entry['rating']}")
                # Return (overall_rating, stars) tuple
                overall = cached_entry.get('rating')
                stars = cached_entry.get('stars', int(round(overall))) if overall else None
                return (overall, stars) if overall else None
        except Exception as e:
            if logger:
                logger.warning(f"get_game_popularity: error reading cache: {e}")
    
    # Fetch from network
    if session is None:
        session = requests.Session()
    
    try:
        if logger:
            logger.info(f"get_game_popularity: fetching {url}")
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        # Parse game details from page
        details = parse_game_details(response.text)
        
        # Extract rating (prefer overall rating if available)
        rating = details.get('rating')
        if rating is None:
            if logger:
                logger.warning(f"get_game_popularity: no rating found for {game_id}")
            return None
        
        # Convert to float and calculate stars
        try:
            overall_rating = float(rating)
            stars = int(round(overall_rating))
        except (ValueError, TypeError):
            if logger:
                logger.warning(f"get_game_popularity: invalid rating '{rating}' for {game_id}")
            return None
        
        # Cache result if cache_path provided
        if cache_path:
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache = {}
                if cache_path.exists():
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cache = json.load(f)
                
                cache[game_id] = {
                    'rating': overall_rating,
                    'stars': stars,
                    'url': url
                }
                
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, indent=2)
                    
                if logger:
                    logger.debug(f"get_game_popularity: cached {game_id} -> {overall_rating}")
            except Exception as e:
                if logger:
                    logger.warning(f"get_game_popularity: error writing cache: {e}")
        
        return (overall_rating, stars)
        
    except requests.exceptions.RequestException as e:
        if logger:
            logger.warning(f"get_game_popularity: network error fetching {url}: {e}")
        return None
    except Exception as e:
        if logger:
            logger.exception(f"get_game_popularity: unexpected error for {url}: {e}")
        return None


def score_to_stars(score: float) -> int:
    """Convert overall rating score (0-10) to star rating (1-5).
    
    Args:
        score: Overall rating (e.g., 8.62)
        
    Returns:
        Star rating (1-5), rounded from score/2
    """
    try:
        return int(round(float(score) / 2.0))
    except (ValueError, TypeError):
        return 0
