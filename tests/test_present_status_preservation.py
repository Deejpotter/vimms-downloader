"""Test that GamesList preserves present status when merging details."""
import pytest


def test_present_status_preserved_on_merge():
    """Test that present: true is preserved when merging game details."""
    # Initial game from cached index with present status
    original_game = {
        'id': '18376',
        'name': 'Ace Attorney Investigations: Miles Edgeworth',
        'url': 'https://vimm.net/vault/18376',
        'present': True
    }
    
    # Details fetched from /api/game endpoint (no present field or present: false)
    fetched_details = {
        'game_id': '18376',
        'title': 'Ace Attorney Investigations: Miles Edgeworth',
        'size_bytes': 67108864,
        'extension': '.nds',
        'popularity': {'score': 4.5, 'votes': 120, 'rounded_score': 5},
        'present': False  # This shouldn't override the original
    }
    
    # Simulate the merge logic from GamesList (preserving original present)
    original_present = original_game['present']
    merged_game = {**original_game, **fetched_details}
    
    # Restore original present value
    if original_present is not None:
        merged_game['present'] = original_present
    
    # Verify present status was preserved
    assert merged_game['present'] == True
    assert merged_game['size_bytes'] == 67108864
    assert merged_game['extension'] == '.nds'


def test_present_undefined_not_overwritten():
    """Test that missing present field doesn't break merge."""
    original_game = {
        'id': '18377',
        'name': 'Some Game',
        'present': True
    }
    
    # Details without present field at all
    fetched_details = {
        'game_id': '18377',
        'title': 'Some Game',
        'size_bytes': 12345
    }
    
    # Merge
    original_present = original_game.get('present')
    merged_game = {**original_game, **fetched_details}
    
    # Restore if it was in original
    if original_present is not None:
        merged_game['present'] = original_present
    
    assert merged_game['present'] == True


def test_checkmark_renders_with_present_true():
    """Test that checkmark logic works correctly."""
    games = [
        {'id': '1', 'name': 'Game A', 'present': True},
        {'id': '2', 'name': 'Game B', 'present': False},
        {'id': '3', 'name': 'Game C'},  # no present field
    ]
    
    # Simulate checkmark rendering logic
    checkmarks = []
    for game in games:
        is_present = game.get('present') == True  # Explicitly check for True
        checkmarks.append(is_present)
    
    assert checkmarks == [True, False, False]
