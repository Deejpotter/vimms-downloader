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

    # Place a stub canonical downloader in cli/ folder so runner doesn't abort
    cli_dir = root / 'cli'
    cli_dir.mkdir()
    (cli_dir / 'download_vimms.py').write_text('# stub')

    # Run runner in dry-run mode targeting our tmp workspace
    main(['--src', str(root), '--dry-run'])

    captured = capsys.readouterr()
    assert 'Dry-run mode: planned runs' in captured.out
    assert 'DS' in captured.out
    # GBA is marked active=false, so it should NOT appear in the output
    assert 'GBA' not in captured.out or 'Skipping' in captured.out
