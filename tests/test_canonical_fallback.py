from pathlib import Path
from run_vimms import main


def test_canonical_falls_back_to_local_repo(tmp_path, capsys):
    # Create a data folder that does NOT contain download_vimms.py
    data = tmp_path / 'H_drive'
    data.mkdir()

    # Call main pointing src at the data folder; since data lacks canonical, runner should
    # fall back to repo-local canonical (which exists in the test workspace)
    main(['--src', str(data), '--dry-run'])

    captured = capsys.readouterr()
    assert 'Falling back to local repo canonical' in captured.out
    assert 'Dry-run mode: planned runs' in captured.out
