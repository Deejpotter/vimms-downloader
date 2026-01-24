import json
import tempfile
from download_vimms import VimmsDownloader
from pathlib import Path


def test_project_root_config_applied(tmp_path):
    # Create a fake project root with a config that sets extract_files to False
    pr = tmp_path / 'proj'
    pr.mkdir()
    cfg = {
        "defaults": {
            "extract_files": False
        }
    }
    with open(pr / 'vimms_config.json', 'w', encoding='utf-8') as f:
        json.dump(cfg, f)

    # Construct downloader pointing at project_root
    dl = VimmsDownloader(download_dir=str(tmp_path / 'ROMs'), system='DS', project_root=str(pr))

    assert dl.extract_files is False
