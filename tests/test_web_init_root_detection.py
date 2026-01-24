from pathlib import Path
import tempfile
from fastapi.testclient import TestClient
from src.webapp import app

client = TestClient(app)


def test_init_root_detection(tmp_path):
    # create temp root with console-like subfolders
    root = tmp_path / 'games'
    root.mkdir()
    (root / 'GC').mkdir()
    (root / 'DS').mkdir()

    r = client.post('/api/init', json={'folder': str(root)})
    assert r.status_code == 200
    j = r.json()
    assert j.get('status') == 'root'
    assert 'consoles' in j
    assert 'GC' in j['consoles']
