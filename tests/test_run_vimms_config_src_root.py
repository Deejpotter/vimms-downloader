import json
from pathlib import Path
from run_vimms import main


def test_run_vimms_respects_src_root_in_config(tmp_path, capsys):
    # Create a separate project root with a DS folder and a stub downloader
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'DS').mkdir()
    (project / 'download_vimms.py').write_text('# stub')

    # Create a config that points src_root at that project
    cfg = {
        'src': str(project)
    }
    cfg_path = tmp_path / 'vimms_config.json'
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f)

    # Call main with --config pointing to our config file and --dry-run
    main(['--config', str(cfg_path), '--dry-run'])

    captured = capsys.readouterr()
    assert 'Dry-run mode: planned runs' in captured.out
    assert 'DS' in captured.out
