import tempfile
from pathlib import Path
from src.download_vimms import VimmsDownloader


def test_categorize_downloaded_file(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        roms = Path(td)
        # create dummy file
        f = roms / 'Some Game (USA).nds'
        f.write_text('dummy')

        dl = VimmsDownloader(str(roms), system='DS', detect_existing=False, pre_scan=False)

        # stub get_game_popularity to return high score
        def fake_get(url, session=None, cache_path=None, logger=None):
            return (8.5, 12)

        monkeypatch.setattr('src.metadata.get_game_popularity', fake_get)

        dl._categorize_downloaded_file(f, '999')

        # check file moved
        target = roms / 'stars' / '5' / f.name
        assert target.exists()
