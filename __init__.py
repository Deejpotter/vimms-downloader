"""Vimm downloader package.

Expose convenient entry points for top-level scripts to call.
"""

# Make package import-safe for test collection: guard relative imports so pytest can
# import the package top-level without a known parent package. When tests run in
# normal package context these will be set correctly.
try:
    from .run_vimms import main as run_main  # re-exported for convenience
    from .download_vimms import main as download_main
except Exception:
    # Fall back to None when relative imports aren't available during test collection
    run_main = None
    download_main = None

__all__ = ["run_main", "download_main"]
