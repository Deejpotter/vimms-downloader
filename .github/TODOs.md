# TODOs for vimms-downloader

This file tracks the work planned and completed for this repository. Keep the most recent 10 completed items.

- [x] (Completed) Add `.github/copilot-instructions.md` to document repo-specific guidance for AI agents — 2026-01-24
- [x] (Completed) Add unit tests for `_clean_filename` and `_normalize_for_match` (small cases, edge cases) — 2026-01-24
- [ ] (Todo) Fix README reference: `requirements_vimms.txt` vs `requirements.txt` (update docs or add the file)
- [ ] (Todo) Add integration tests for `VimmsDownloader.get_game_list_from_section` using recorded HTML fixtures

- NOTE: Per owner preference, do NOT add CI workflows. Keep tests local and lightweight; run with `pytest` locally. If you want CI later, open a new TODO.

- [ ] (Todo) Improve extraction path when `py7zr` is missing (document and optionally auto-install or warn clearly)
- [x] (Completed) Add small test harness for `run_vimms.py --dry-run` behavior — 2026-01-24
- [x] (Completed) Allow `src_root` to be read from `vimms_config.json` and ignore obvious non-console folders when scanning workspace root — 2026-01-24

---

Planned cleanup & simplification (detailed plan)

Priority A — Safe, low-risk, high-value (implement first)
- [x] (Completed) Centralize filename cleaning and normalization into `utils/filenames.py` (moved `_clean_filename` and `_normalize_for_match` and updated callers) — 2026-01-24
    - substeps:
      - added `utils/filenames.py` and exported `clean_filename`, `normalize_for_match`
      - updated `clean_filenames.py` to import and use `clean_filename`
      - updated `download_vimms.py` to use `normalize_for_match` and `clean_filename`
      - updated tests to target utilities and fixed regressions
- [x] (Completed) Centralize ROM/archive extension lists and defaults in `utils/constants.py` — 2026-01-24
    - substeps:
      - added `utils/constants.py` (ROM_EXTENSIONS, ARCHIVE_EXTENSIONS, USER_AGENTS)
      - replaced duplicated ROM extension lists in `download_vimms.py`
      - added `tests/test_constants.py` to validate basic coverage of constants

Priority B — Medium-risk refactors (after A, add tests)
- [ ] (Todo) Extract HTML parsing & network helpers from `VimmsDownloader` into `download_vimms.parse` / `download_vimms.fetch` modules
    - substeps:
      - add parsing helpers and unit tests with saved HTML fixtures
      - refactor `VimmsDownloader.get_game_list_from_section` and `get_download_url` to call helpers
- [ ] (Todo) Add targeted tests for retry/backoff and 429 handling
- [ ] (Todo) Add extraction tests (zip/.7z) using monkeypatch/stubs for `py7zr` and `zipfile`

Priority C — Nice-to-have / packaging / docs
- [ ] (Todo) Add minimal `pyproject.toml` and make package installable for better test isolation
- [ ] (Todo) Move CLI code to `cli.py` (thin wrapper) and expose library functions for programmatic use
- [ ] (Todo) Add optional integration harness for manual downloads (safe, header-only checks)

Notes & workflow:
- Before starting a task, mark it In Progress and post a short plan. After completing, mark Completed and keep only last 10 completed tasks.
- We'll do Priority A now. I'll update this TODOs file as we progress.

(End of list)
