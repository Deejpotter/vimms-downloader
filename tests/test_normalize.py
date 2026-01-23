import pytest
from download_vimms import VimmsDownloader
from pathlib import Path

@pytest.fixture
def dl(tmp_path):
    # Use a temporary directory for any disk interactions
    d = VimmsDownloader(download_dir=str(tmp_path), system='DS', detect_existing=False, pre_scan=False)
    return d

@pytest.mark.parametrize("input_str, expected", [
    ("Super_Mario.nds", "super mario"),
    ("The-Legend.of:Zelda!.nds", "the legend of zelda"),
    ("GAME.NAME (EU)", "game name"),
    ("my_game  (USA).7z", "my game"),
])
def test_normalize_for_match(dl, input_str, expected):
    assert dl._normalize_for_match(input_str) == expected
