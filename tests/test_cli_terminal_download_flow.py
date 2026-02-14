import subprocess
import sys
from pathlib import Path
from download_vimms import detect_console_from_folder


def test_detect_console_from_folder_returns_none_for_non_console(tmp_path):
    # Non-console folder name should not map to a Vimm console
    dir = tmp_path / 'ROMs'
    dir.mkdir()
    assert detect_console_from_folder(dir) is None


def test_download_cli_prints_warning_for_unknown_folder(tmp_path):
    # Invoke the CLI script against an ambiguous folder and assert the warning is printed
    folder = tmp_path / 'ROMs'
    folder.mkdir()

    python = sys.executable
    cmd = [python, 'cli/download_vimms.py', '--folder', str(folder)]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    out = proc.stdout + proc.stderr
    assert 'WARNING: Could not auto-detect console' in out
    # CLI should exit cleanly even when it cannot detect the console
    assert proc.returncode == 0
