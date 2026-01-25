import json
import tempfile
import shutil
from pathlib import Path
from src.webapp import _find_missing_consoles


def test_find_missing_consoles_missing_and_partial(tmp_path):
    # create fake workspace with consoles DS and GBA
    ds = tmp_path / 'DS'
    gba = tmp_path / 'GBA'
    ds.mkdir()
    gba.mkdir()

    # index_data has only DS but with zero games (partial)
    index_data = {
        'workspace_root': str(tmp_path),
        'consoles': [
            {'name': 'DS', 'sections': {}}
        ]
    }

    res = _find_missing_consoles(str(tmp_path), index_data)
    assert 'GBA' in res['missing_on_disk']
    assert 'DS' in res['partial_in_index']
    assert 'GBA' in res['to_resync'] and 'DS' in res['to_resync']
