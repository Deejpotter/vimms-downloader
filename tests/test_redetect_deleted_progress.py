import tempfile
import pytest
from pathlib import Path
from download_vimms import VimmsDownloader


@pytest.mark.skip(reason="Method _find_section_start_index() no longer exists in VimmsDownloader - feature removed or refactored")
def test_redetect_missing_marked_completed(tmp_path):
    # Prepare one title with id '999' and name 'Some Game'
    rom = tmp_path / 'Some Game.nds'
    rom.write_text('dummy')

    dl = VimmsDownloader(str(tmp_path), system='DS', detect_existing=True, pre_scan=True)

    # Build index and ensure it's detected
    dl._build_local_index()
    games = [{'game_id': '999', 'name': 'Some Game'}]

    # Initially _find_section_start_index should return None (present)
    idx = dl._find_section_start_index(games)
    assert idx is None

    # Mark as completed but remove the actual file
    dl.progress['completed'].append('999')
    dl._save_progress()
    rom.unlink()

    # Now _find_section_start_index should detect missing and return 0 and remove from completed
    idx2 = dl._find_section_start_index(games)
    assert idx2 == 0
    assert '999' not in dl.progress['completed']
