from src.metadata import _parse_popularity_from_html, score_to_stars


def test_parse_popularity_basic():
    html = """<html><body><div>Overall 8.38 (21 votes)</div></body></html>"""
    parsed = _parse_popularity_from_html(html)
    assert parsed is not None
    score, votes = parsed
    assert abs(score - 8.38) < 0.001
    assert votes == 21


def test_parse_popularity_no_votes():
    html = """<html><body><div>Overall: 7.0</div></body></html>"""
    parsed = _parse_popularity_from_html(html)
    assert parsed == (7.0, 0)


def test_score_to_stars():
    assert score_to_stars(0) == 1
    assert score_to_stars(1.9) == 1
    assert score_to_stars(2.0) == 2
    assert score_to_stars(3.9) == 2
    assert score_to_stars(5.0) == 3
    assert score_to_stars(7.5) == 4
    assert score_to_stars(9.9) == 5