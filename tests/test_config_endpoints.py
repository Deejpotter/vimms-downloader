#!/usr/bin/env python3
"""
Integration tests for webapp config API endpoints.

Tests the GET /api/config, POST /api/config/save, and POST /api/config/create_folders endpoints.
These are integration tests that use the actual config file in the repository.
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add src directory to path for importing webapp
test_dir = Path(__file__).parent
repo_root = test_dir.parent
src_dir = repo_root / 'src'
sys.path.insert(0, str(src_dir))

from webapp import app

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_get_config_endpoint_exists(client):
    """Test that the config endpoint exists and returns valid JSON."""
    response = client.get('/api/config')
    assert response.status_code in [200, 404]  # Either works or config missing
    
    if response.status_code == 200:
        data = response.get_json()
        assert isinstance(data, dict)
        # Config might be empty, that's ok - just verify it's a valid dict
        # The key test is that the endpoint works and returns JSON

def test_save_config_endpoint_exists(client):
    """Test that the save config endpoint exists and handles requests."""
    # Test with minimal valid config
    test_config = {
        "defaults": {"detect_existing": True},
        "folders": {"TEST": {"active": True, "priority": 1}}
    }
    
    response = client.post('/api/config/save',
                          data=json.dumps(test_config),
                          content_type='application/json')
    
    # Should either succeed or fail gracefully
    assert response.status_code in [200, 400, 500]
    
    # Should return JSON
    data = response.get_json()
    assert isinstance(data, dict)

def test_save_config_handles_invalid_json(client):
    """Test that save config handles invalid JSON gracefully."""
    response = client.post('/api/config/save',
                          data='invalid json',
                          content_type='application/json')
    
    # Should return 400 for bad JSON
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_create_folders_endpoint_exists(client):
    """Test that create folders endpoint exists and handles requests."""
    temp_dir = tempfile.mkdtemp()
    
    try:
        response = client.post('/api/config/create_folders',
                              data=json.dumps({
                                  'workspace_root': temp_dir,
                                  'active_only': True
                              }),
                              content_type='application/json')
        
        # Should either succeed or fail gracefully  
        assert response.status_code in [200, 404, 500]
        
        # Should return JSON
        data = response.get_json()
        assert isinstance(data, dict)
        
        if response.status_code == 200:
            assert 'created' in data
            assert isinstance(data['created'], list)
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_create_folders_missing_workspace_root(client):
    """Test create folders with missing workspace root."""
    response = client.post('/api/config/create_folders',
                          data=json.dumps({
                              'active_only': True
                              # Missing workspace_root
                          }),
                          content_type='application/json')
    
    # Should handle missing parameter gracefully
    assert response.status_code in [400, 500]

def test_endpoints_return_json_content_type(client):
    """Test that all endpoints return proper JSON content type."""
    # Test GET config
    response = client.get('/api/config')
    assert 'application/json' in response.content_type
    
    # Test POST save config
    response = client.post('/api/config/save',
                          data='{}',
                          content_type='application/json')
    assert 'application/json' in response.content_type
    
    # Test POST create folders
    response = client.post('/api/config/create_folders',
                          data='{}',
                          content_type='application/json')
    assert 'application/json' in response.content_type


def test_save_config_rejects_workspace_root_removal(client):
    """Ensure the API rejects attempts to remove workspace_root unless forced."""
    # Load current config; skip if not present
    res = client.get('/api/config')
    if res.status_code != 200:
        pytest.skip('No top-level config available')
    orig = res.get_json()
    if 'workspace_root' not in orig:
        pytest.skip('No workspace_root to test removal against')

    # Attempt to save config with workspace_root removed
    bad_cfg = dict(orig)
    bad_cfg.pop('workspace_root', None)
    response = client.post('/api/config/save', data=json.dumps(bad_cfg), content_type='application/json')
    assert response.status_code == 400
    data = response.get_json()
    assert 'workspace_root' in data.get('error', '')


def test_save_creates_timestamped_backup_and_atomic_replace(client, tmp_path):
    """Saving config should create a timestamped backup and atomically replace the file."""
    cfg_file = Path(__file__).resolve().parent.parent / 'vimms_config.json'
    if not cfg_file.exists():
        pytest.skip('Top-level vimms_config.json not present')

    # Read original and prepare modified copy
    orig_text = cfg_file.read_text(encoding='utf-8')
    orig = json.loads(orig_text)
    modified = dict(orig)
    # Toggle a boolean default (safe change)
    md = modified.get('defaults', {})
    md['detect_existing'] = not md.get('detect_existing', True)
    modified['defaults'] = md

    try:
        start_files = set(p.name for p in cfg_file.parent.glob('vimms_config.*'))
        response = client.post('/api/config/save', data=json.dumps(modified), content_type='application/json')
        assert response.status_code == 200

        # Verify a timestamped backup (.YYYYMMDDHHMMSS.bak) exists
        new_files = set(p.name for p in cfg_file.parent.glob('vimms_config.*')) - start_files
        bak_files = [n for n in new_files if n.endswith('.bak')]
        assert len(bak_files) >= 1

        # Ensure the saved file is valid JSON and equals our modified payload
        saved = json.loads(cfg_file.read_text(encoding='utf-8'))
        assert saved.get('defaults', {}).get('detect_existing') == md['detect_existing']

        # No lingering temp files
        tmp_matches = list(cfg_file.parent.glob('vimms_config.*.tmp'))
        assert len(tmp_matches) == 0

    finally:
        # Restore original config
        cfg_file.write_text(orig_text, encoding='utf-8')


def test_save_rejects_empty_folders_by_default(client):
    """Saving a config with empty folders should be rejected unless _force_save provided."""
    payload = {'defaults': {'detect_existing': True}, 'folders': {}}
    res = client.post('/api/config/save', data=json.dumps(payload), content_type='application/json')
    assert res.status_code == 400
    # Now force it - should succeed (but we won't keep the change)
    payload['_force_save'] = True
    cfg_file = Path(__file__).resolve().parent.parent / 'vimms_config.json'
    orig = cfg_file.read_text(encoding='utf-8')
    try:
        res2 = client.post('/api/config/save', data=json.dumps(payload), content_type='application/json')
        assert res2.status_code == 200
    finally:
        cfg_file.write_text(orig, encoding='utf-8')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])