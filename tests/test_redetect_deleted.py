import tempfile
import pytest
from pathlib import Path
from download_vimms import VimmsDownloader


@pytest.mark.skip(reason="Method _prune_local_index() no longer exists in VimmsDownloader - feature removed or refactored")
def test_prune_removes_empty_directory(tmp_path):
    # Create a per-title directory containing a ROM file
    title_dir = tmp_path / 'Some Game'
    title_dir.mkdir()
    rom = title_dir / 'Some Game.nds'
    rom.write_text('dummy')

    dl = VimmsDownloader(str(tmp_path), system='DS', detect_existing=True, pre_scan=False)

    # Build index and ensure the title is detected
    dl._build_local_index()
    matches = dl.find_all_matching_files('Some Game')
    assert matches, 'Expected to find the ROM before deletion'

    # Remove the ROM file, leaving the directory behind
    rom.unlink()

    # Prune the index and check that the title is no longer detected
    dl._prune_local_index()
    matches_after = dl.find_all_matching_files('Some Game')
    assert not matches_after, 'Expected no matches after removing the ROM file'
