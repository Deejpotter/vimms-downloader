"""Test rating extraction from section pages."""
import pytest
from downloader_lib.parse import parse_games_from_section


def test_rating_extraction_from_section():
    """Test that ratings are extracted from section page HTML."""
    html_content = '''
    <table class="rounded centered cellpadding1 hovertable striped">
        <tbody>
            <tr>
                <td><a href="/vault/18376">Ace Attorney Investigations: Miles Edgeworth (USA)</a></td>
                <td>USA</td>
                <td>1</td>
                <td>EN</td>
                <td>8.4</td>
            </tr>
            <tr>
                <td><a href="/vault/18377">Another Game (EU)</a></td>
                <td>EU</td>
                <td>1</td>
                <td>EN</td>
                <td>7.2</td>
            </tr>
            <tr>
                <td><a href="/vault/18378">Game Without Rating (USA)</a></td>
                <td>USA</td>
                <td>1</td>
                <td>EN</td>
                <td>none</td>
            </tr>
        </tbody>
    </table>
    '''
    
    games = parse_games_from_section(html_content, 'A')
    
    assert len(games) == 3
    
    # First game should have rating
    assert games[0]['name'] == 'Ace Attorney Investigations: Miles Edgeworth (USA)'
    assert games[0]['game_id'] == '18376'
    assert 'rating' in games[0]
    assert games[0]['rating'] == 8.4
    
    # Second game should have rating
    assert games[1]['name'] == 'Another Game (EU)'
    assert games[1]['game_id'] == '18377'
    assert 'rating' in games[1]
    assert games[1]['rating'] == 7.2
    
    # Third game should not have rating (was "none")
    assert games[2]['name'] == 'Game Without Rating (USA)'
    assert games[2]['game_id'] == '18378'
    assert 'rating' not in games[2]


def test_rating_extraction_handles_missing_column():
    """Test that parser doesn't break when rating column is missing."""
    html_content = '''
    <table class="rounded centered cellpadding1 hovertable striped">
        <tbody>
            <tr>
                <td><a href="/vault/18376">Ace Attorney Investigations: Miles Edgeworth (USA)</a></td>
                <td>USA</td>
                <td>1</td>
            </tr>
        </tbody>
    </table>
    '''
    
    games = parse_games_from_section(html_content, 'A')
    
    assert len(games) == 1
    assert games[0]['name'] == 'Ace Attorney Investigations: Miles Edgeworth (USA)'
    assert 'rating' not in games[0]  # No rating column, so no rating


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
