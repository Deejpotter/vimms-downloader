import json
import sys
from pathlib import Path
from download_vimms import VimmsDownloader


def test_categorize_by_rating_moves_file(tmp_path, monkeypatch):
    # Setup download dir with a ROM file
    download_dir = tmp_path / 'ROMs'
    download_dir.mkdir()
    rom = download_dir / 'PHC Product Test.nds'
    rom.write_text('dummy')

    # Create a fake metadata module (get_game_popularity) so _categorize_by_rating can use it
    fake_meta = type('M', (), {})()
    def fake_get_game_popularity(url, session=None, cache_path=None, logger=None):
        return (8.62, 13)
    fake_meta.get_game_popularity = fake_get_game_popularity
    sys.modules['metadata'] = fake_meta

    dl = VimmsDownloader(download_dir=str(download_dir), system='DS', detect_existing=False, pre_scan=False, project_root=str(tmp_path))

    # Call categorize on the existing file (provide score directly)
    dl._categorize_by_rating(rom, score=8.62)

    expected = download_dir / 'rating' / '8' / rom.name
    assert expected.exists()


def test_categorize_existing_uses_webui_index(tmp_path):
    # Prepare project root with src/webui_index.json containing a DS entry
    project_root = tmp_path / 'project'
    (project_root / 'src').mkdir(parents=True)

    webui_index = {
        'workspace_root': str(tmp_path),
        'consoles': [
            {
                'name': 'DS',
                'system': 'DS',
                'folder': str(tmp_path / 'DS'),
                'sections': {
                    'P': [
                        {'id': '6063', 'name': 'PHC Product Test (VERIFY)', 'rating': 8.62}
                    ]
                }
            }
        ]
    }
    with open(project_root / 'src' / 'webui_index.json', 'w', encoding='utf-8') as f:
        json.dump(webui_index, f)

    # Create download folder and a file whose cleaned/normalized name matches the webui title
    download_dir = tmp_path / 'DS' / 'ROMs'
    download_dir.mkdir(parents=True)
    rom = download_dir / 'PHC Product Test.nds'
    rom.write_text('dummy')

    dl = VimmsDownloader(download_dir=str(download_dir), system='DS', detect_existing=False, pre_scan=False, project_root=str(project_root))

    moved = dl.categorize_existing_files()
    assert moved == 1
    assert (download_dir / 'rating' / '8' / rom.name).exists()

    # Ensure local index still detects the file after moving
    dl._build_local_index()
    match = dl.is_game_present('PHC Product Test (VERIFY)')
    assert match is not None
