import pytest
from clean_filenames import clean_filename

@pytest.mark.parametrize("orig, expected", [
    ("005 4426__MY_GAME_(EU).nds", "MY Game.nds"),
    ("Super_Mario.nds", "Super Mario.nds"),
    ("123 4567_POKEMON_(USA).nds", "Pokemon.nds"),
    ("THE_LEGEND_OF_ZELDA_(EU).nds", "THE Legend of Zelda.nds"),
])
def test_clean_filename(orig, expected):
    assert clean_filename(orig) == expected
