from pathlib import Path
from archive.run_vimms import main


def test_canonical_falls_back_to_local_repo(tmp_path, capsys):
    # Create a data folder that does NOT contain download_vimms.py
    data = tmp_path / 'H_drive'
    data.mkdir()

    # Call main pointing src at the data folder; the runner should still succeed
    main(['--src', str(data), '--dry-run'])

    captured = capsys.readouterr()
    assert 'Dry-run mode: planned runs' in captured.out

