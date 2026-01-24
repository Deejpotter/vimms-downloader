"""Network fetch helpers for Vimm's Lair downloader."""
import requests
from utils.constants import USER_AGENTS
import random

BASE_URL = "https://vimm.net"
VAULT_BASE = f"{BASE_URL}/vault"

def _get_random_user_agent() -> str:
    """Return a random user agent."""
    return random.choice(USER_AGENTS)

def fetch_section_page(session: requests.Session, system: str, section: str, page_num: int):
    """Fetch a single page of games from a section."""
    section_url = f"{VAULT_BASE}/?p=list&action=filters&system={system}&section={section}&page={page_num}"
    headers = {
        'User-Agent': _get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    response = session.get(section_url, headers=headers, verify=False)
    response.raise_for_status()
    return response

def fetch_game_page(session: requests.Session, game_page_url: str):
    """Fetch the detail page for a single game."""
    headers = {
        'User-Agent': _get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': VAULT_BASE
    }
    response = session.get(game_page_url, headers=headers, verify=False)
    response.raise_for_status()
    return response
