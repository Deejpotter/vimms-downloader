import pytest
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient
from src.webapp import app

client = TestClient(app)


def test_sections_endpoint():
    r = client.get('/api/sections')
    assert r.status_code == 200
    assert 'sections' in r.json()


def test_queue_flow():
    # Clear queue
    client.delete('/api/queue')
    r = client.get('/api/queue')
    assert r.status_code == 200
    assert isinstance(r.json().get('queue'), list)
    # enqueue a dummy item
    item = {'folder': '.', 'game': {'game_id': '1', 'name': 'Test', 'page_url': 'https://vimm.net/vault/1'}}
    r2 = client.post('/api/queue', json=item)
    assert r2.status_code == 200
    assert r2.json().get('status') == 'queued'
    r3 = client.get('/api/queue')
    assert any(it.get('game', {}).get('game_id') == '1' for it in r3.json().get('queue'))


def test_game_endpoint_with_mock(monkeypatch):
    # Mock get_game_popularity to return a known value
    def fake_get(url, session=None, cache_path=None, logger=None):
        return (8.38, 21)
    monkeypatch.setattr('src.webapp.get_game_popularity', fake_get)

    # Mock session.get to provide a basic title
    class FakeResp:
        text = '<html><head><title>Test Game</title></head><body></body></html>'
        def raise_for_status(self):
            return
    class FakeDL:
        session = type('S', (), {'get': lambda self, url, timeout=None: FakeResp()})
        def find_all_matching_files(self, title):
            return []
    # Register fake downloader instance
    webapp = __import__('src.webapp', fromlist=['webapp'])
    webapp.DL_INSTANCES['.'] = FakeDL()

    r = client.get('/api/game/999?folder=.')
    assert r.status_code == 200
    j = r.json()
    assert j['popularity']['score'] == 8.38
    assert j['popularity']['votes'] == 21
    assert j['title'] == 'Test Game'
