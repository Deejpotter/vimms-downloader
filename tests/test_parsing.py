from pathlib import Path
from downloader_lib.parse import parse_games_from_section, resolve_download_form
import requests
from types import SimpleNamespace

FIXTURES = Path(__file__).parent / 'fixtures'

def test_parse_games_from_section():
    html = (FIXTURES / 'section_page.html').read_text()
    games = parse_games_from_section(html, 'A')
    assert len(games) == 2
    assert games[0]['name'] == 'Game 1'
    assert games[0]['game_id'] == '1'
    assert games[1]['name'] == 'Game 2'
    assert games[1]['game_id'] == '2'

def test_resolve_download_form_post():
    html = (FIXTURES / 'game_page_post.html').read_text()
    
    # Mock session for POST request
    session = SimpleNamespace()
    def fake_post(url, data=None, headers=None, verify=None, allow_redirects=None):
        return SimpleNamespace(status_code=200, url=f"https://dl3.vimm.net/?mediaId={data['mediaId']}")
    session.post = fake_post
    session.headers = {}

    url = resolve_download_form(html, session, 'http://example.com', '123', logger=None)
    assert url == 'https://dl3.vimm.net/?mediaId=6590'
