---
name: "Maintenance guidance"
description: "Small-scope maintenance & housekeeping rules"
applyTo: ".github/**"
---

- Keep `.github/TODOs.md` updated before and after every task (use statuses: Todo, In Progress, Completed).
- Update `.github/copilot-instructions.md` when adding or changing agent rules; prefer small edits and preserve historical notes.
- When changing project layout (e.g., migrating Python `archive/` -> TypeScript `src/`), update `.github/*` docs to reflect the new structure and developer workflows.
- Use `.instructions.md` files for focused guidance and include YAML frontmatter with `applyTo` to scope automatically.
- Avoid adding CI unless owner approves; if tests are added, include a minimal GitHub Actions workflow that only runs `pytest`.
- Add entries to `requirements.txt` when introducing new test/runtime dependencies.
- For any change that touches files with user data or deletion behavior, include a clear description, test plan, and recovery steps in the PR.
