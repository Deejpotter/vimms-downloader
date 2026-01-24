# Compatibility shim for historical imports and CLI
# Exposes the canonical downloader from `src.download_vimms` while keeping
# the top-level script location stable for the runner (`run_vimms.py`).
from src.download_vimms import *  # noqa: F401,F403

if __name__ == "__main__":
    main()
