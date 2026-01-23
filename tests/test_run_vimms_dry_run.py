import json
from pathlib import Path
from run_vimms import main


def test_run_vimms_dry_run_lists_planned_folders(tmp_path, capsys):
    # Prepare a fake workspace root with two console folders
    root = tmp_path
    (root / 'DS').mkdir()
    (root / 'GBA').mkdir()

    # Create a simple config to mark GBA inactive
    cfg = {
        "folders": {
            "DS": {"active": True},
            "GBA": {"active": False}
        }
    }
    with open(root / 'vimms_config.json', 'w', encoding='utf-8') as f:
        json.dump(cfg, f)

    # Place a stub canonical downloader so runner doesn't abort
    (root / 'download_vimms.py').write_text('# stub')

    # Run runner in dry-run mode targeting our tmp workspace
    main(['--src', str(root), '--dry-run'])

    captured = capsys.readouterr()
    assert 'Dry-run mode: planned runs' in captured.out
    assert 'DS' in captured.out
    assert 'GBA' in captured.out
