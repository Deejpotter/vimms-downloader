from pathlib import Path
import tempfile
from src.download_vimms import VimmsDownloader


def test_redetect_deleted_game():
    with tempfile.TemporaryDirectory() as td:
        rom_dir = Path(td) / 'ROMs'
        rom_dir.mkdir()

        # Create a dummy file for a different game
        (rom_dir / 'some other game.nds').write_text('dummy')

        # Create downloader with detect_existing enabled
        dl = VimmsDownloader(str(rom_dir), system='DS', detect_existing=True, pre_scan=False)

        # Simulate progress that says game 123 was completed
        dl.progress['completed'].append('123')

        # Stub find_all_matching_files to return no matches (file deleted)
        setattr(dl, 'find_all_matching_files', lambda name: [])

        # Stub get_download_url to avoid network calls and return None -> marks as failed
        setattr(dl, 'get_download_url', lambda url, gid: None)

        # Run download_game for the entry; it should detect deletion and remove from completed
        result = dl.download_game({'name': 'Deleted Game', 'game_id': '123', 'page_url': 'http://example'})

        assert '123' not in dl.progress['completed']
        assert not result
        # A failure record should be added for this game because get_download_url returned None
        assert any(f.get('game_id') == '123' for f in dl.progress['failed'])

        # Close any log handlers so TemporaryDirectory cleanup can remove files on Windows
        if getattr(dl, 'logger', None):
            for h in list(dl.logger.handlers):
                try:
                    h.close()
                except Exception:
                    pass
            dl.logger.handlers = []