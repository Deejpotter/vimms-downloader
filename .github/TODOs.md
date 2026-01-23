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

(End of list)
