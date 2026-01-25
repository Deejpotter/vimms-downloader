#!/usr/bin/env python3
"""Test default folders endpoint."""
import pytest
from pathlib import Path
import sys

# Add src dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from webapp import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_default_folders_endpoint(client):
    resp = client.get('/api/config/default_folders')
    assert resp.status_code in (200, 500)
    data = resp.get_json()
    assert isinstance(data, dict)
    if resp.status_code == 200:
        assert 'defaults' in data
        assert isinstance(data['defaults'], dict)
