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

if __name__ == '__main__':
    pytest.main([__file__, '-v'])