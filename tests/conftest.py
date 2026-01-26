"""Pytest configuration for vimms-downloader tests."""
import sys
from pathlib import Path

# Add cli directory to path so tests can import CLI modules
cli_dir = Path(__file__).parent.parent / 'cli'
if str(cli_dir) not in sys.path:
    sys.path.insert(0, str(cli_dir))
