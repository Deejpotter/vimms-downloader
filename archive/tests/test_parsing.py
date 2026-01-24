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


def test_resolve_download_form_post_fallback_to_get():
    html = (FIXTURES / 'game_page_post.html').read_text()

    session = SimpleNamespace()
    called = {'post': False, 'get': False}
    last = {}

    def fake_post(url, data=None, headers=None, verify=None, allow_redirects=None):
        called['post'] = True
        last['post_headers'] = headers
        return SimpleNamespace(status_code=400, url=None)

    def fake_get(url, headers=None, verify=None, allow_redirects=None):
        called['get'] = True
        last['get_headers'] = headers
        # echo back mediaId from query string
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(url).query)
        mid = q.get('mediaId', [''])[0]
        return SimpleNamespace(status_code=200, url=f"https://dl3.vimm.net/?mediaId={mid}")

    session.post = fake_post
    session.get = fake_get
    session.headers = {'User-Agent': 'test-agent'}

    url = resolve_download_form(html, session, 'http://example.com', '123', logger=None)
    assert called['post'] and called['get']
    assert last['post_headers'] and last['get_headers']
    assert last['post_headers'].get('User-Agent') == 'test-agent'
    assert 'Referer' in last['post_headers']
    # Additional browser-like headers should be present
    assert last['post_headers'].get('Upgrade-Insecure-Requests') == '1'
    assert 'Sec-Fetch-Mode' in last['post_headers']
    assert 'Sec-CH-UA' in last['post_headers']
    assert url.startswith('https://dl3.vimm.net/?mediaId=')


def test_resolve_download_form_post_mirror_retry():
    html = (FIXTURES / 'game_page_post.html').read_text()

    session = SimpleNamespace()

    call_order = []
    last = {}
    def fake_post(url, data=None, headers=None, verify=None, allow_redirects=None):
        call_order.append(('post', url))
        return SimpleNamespace(status_code=400, url=None)

    def fake_get(url, headers=None, verify=None, allow_redirects=None):
        call_order.append(('get', url))
        # capture headers for assertion
        last.setdefault('gets', []).append(headers)
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        # Simulate original host failing, mirror returning 200
        if 'dl2.vimm.net' in parsed.netloc:
            return SimpleNamespace(status_code=404, url=None)
        else:
            mid = parse_qs(parsed.query).get('mediaId', [''])[0]
            return SimpleNamespace(status_code=200, url=f"https://{parsed.netloc}/?mediaId={mid}")

    session.post = fake_post
    session.get = fake_get
    session.headers = {'User-Agent': 'test-agent'}

    url = resolve_download_form(html, session, 'http://example.com', '123', logger=None)
    assert any('dl1.vimm.net' in u or 'dl3.vimm.net' in u for _, u in call_order if _ == 'get')
    assert 'dl2.vimm.net' not in url  # ensure we didn't return the failing host
    # ensure headers were passed to at least one GET attempt
    assert any(h and h.get('User-Agent') == 'test-agent' for h in last.get('gets', []))
    assert url.startswith('https://')
