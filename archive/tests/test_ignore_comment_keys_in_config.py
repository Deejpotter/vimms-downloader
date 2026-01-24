import json
from pathlib import Path
from archive.run_vimms import main


def test_ignore_comment_keys_in_config(tmp_path, capsys):
    # Create project root with config that includes a _comment key and a DS folder
    project = tmp_path / 'proj'
    project.mkdir()
    (project / 'DS').mkdir()
    cfg = {
        'folders': {
            '_comment': 'metadata',
            'DS': {'active': True}
        }
    }
    cfg_path = project / 'vimms_config.json'
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f)

    # Run main using this config
    main(['--config', str(cfg_path), '--dry-run'])

    captured = capsys.readouterr()
    assert 'Dry-run mode: planned runs' in captured.out
    assert 'DS' in captured.out
    # Ensure no message about skipping '_comment'
    assert "Skipping configured folder '_comment'" not in captured.out
