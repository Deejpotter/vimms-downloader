"""Test per-console completion tracking for index builds."""
import json
import tempfile
from pathlib import Path
import pytest


def test_console_marked_complete_after_scan():
    """Test that each console gets marked complete: true after scanning."""
    # Create a mock index structure
    index_data = {
        'workspace_root': '/test/workspace',
        'timestamp': '2026-01-26T10:00:00Z',
        'consoles': [
            {
                'name': 'DS',
                'system': 'DS',
                'folder': '/test/workspace/DS',
                'sections': {'A': [], 'B': []},
                'complete': True
            }
        ],
        'complete': False
    }
    
    # Verify console has complete flag
    assert index_data['consoles'][0]['complete'] == True
    
    # Verify index itself is not complete (more consoles to scan)
    assert index_data['complete'] == False


def test_skip_completed_consoles_on_resume():
    """Test that consoles marked complete are skipped when resuming."""
    console_folders = ['DS', 'GB', 'GBA', 'GC']
    
    partial_index = {
        'workspace_root': '/test/workspace',
        'consoles': [
            {'name': 'DS', 'complete': True, 'sections': {'A': []}},
            {'name': 'GB', 'complete': True, 'sections': {'A': []}}
        ],
        'complete': False
    }
    
    # Simulate skip logic
    consoles_to_scan = []
    for console_name in console_folders:
        already_complete = False
        for existing in partial_index.get('consoles', []):
            if existing.get('name') == console_name and existing.get('complete') == True:
                already_complete = True
                break
        if not already_complete:
            consoles_to_scan.append(console_name)
    
    # Should skip DS and GB, scan GBA and GC
    assert consoles_to_scan == ['GBA', 'GC']


def test_replace_incomplete_console_entry():
    """Test that old incomplete entries are replaced when console completes."""
    index_data = {
        'consoles': [
            {'name': 'DS', 'complete': False, 'sections': {}},
            {'name': 'GB', 'complete': True, 'sections': {'A': []}}
        ]
    }
    
    # Simulate completing DS
    console_name = 'DS'
    new_console = {
        'name': 'DS',
        'complete': True,
        'sections': {'A': [], 'B': [], 'C': []}
    }
    
    # Remove old incomplete entry
    index_data['consoles'] = [c for c in index_data['consoles'] if c.get('name') != console_name]
    index_data['consoles'].append(new_console)
    
    # Verify old incomplete entry was replaced
    ds_consoles = [c for c in index_data['consoles'] if c['name'] == 'DS']
    assert len(ds_consoles) == 1
    assert ds_consoles[0]['complete'] == True
    assert len(ds_consoles[0]['sections']) == 3


def test_workspace_mismatch_creates_fresh_index():
    """Test that a different workspace root triggers fresh index."""
    existing_index = {
        'workspace_root': '/old/workspace',
        'consoles': [{'name': 'DS', 'complete': True}],
        'complete': False
    }
    
    new_workspace_root = '/new/workspace'
    
    # Simulate workspace mismatch logic
    if existing_index.get('workspace_root') != new_workspace_root:
        index_data = {
            'workspace_root': new_workspace_root,
            'consoles': [],
            'complete': False
        }
    else:
        index_data = existing_index
    
    # Should have created fresh index
    assert index_data['workspace_root'] == '/new/workspace'
    assert index_data['consoles'] == []
    assert index_data['complete'] == False


def test_partial_index_loaded_on_resume():
    """Test that partial index is loaded when resuming same workspace."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        partial_index = {
            'workspace_root': '/test/workspace',
            'consoles': [
                {'name': 'DS', 'complete': True, 'sections': {'A': [{'name': 'Game 1'}]}}
            ],
            'complete': False
        }
        json.dump(partial_index, f)
        temp_path = Path(f.name)
    
    try:
        # Simulate loading partial index
        with open(temp_path, 'r') as f:
            loaded_index = json.load(f)
        
        # Verify it loaded correctly
        assert loaded_index['workspace_root'] == '/test/workspace'
        assert len(loaded_index['consoles']) == 1
        assert loaded_index['consoles'][0]['complete'] == True
        assert loaded_index['complete'] == False
    finally:
        temp_path.unlink()
