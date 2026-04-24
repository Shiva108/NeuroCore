# Repository Guidelines

## Project Structure & Module Organization
This repository is currently in a docs-first planning phase. There are no application source files yet, and `docs/ssd/` is the active implementation source of truth. Keep the layout predictable as code is added:

- `src/` for application code
- `tests/` for automated tests
- `assets/` for static files such as images or sample data
- `docs/` for design notes, architecture decisions, and onboarding material
- `.claude/commands/` for reusable slash-command prompt files kept out of the repo root

Current repo-specific notes:

- keep `docs/ssd/` aligned with any architectural or scope change
- keep `.claude/commands/` prompts discovery-first and consistent with repo reality
- do not introduce alternative top-level planning folders when `docs/` already covers that need

Prefer small, focused modules. Mirror `src/` paths inside `tests/` where practical, for example `src/api/client.js` and `tests/api/test_client.js`.

## Build, Test, and Development Commands
No build, test, or local run commands are defined in this repository yet. When adding tooling, expose one clear entrypoint per task and document it here.

Until a runtime is selected, docs-only and prompt-only changes normally have no automated validation beyond a careful consistency pass.

Recommended patterns:

- `make dev` or `npm run dev` to start a local development workflow
- `make test` or `pytest` / `npm test` to run the full test suite
- `make lint` or `npm run lint` to run formatting and static checks

Avoid ad hoc one-off scripts when a standard project command can be added instead.

## Coding Style & Naming Conventions
Use 4 spaces for Python and 2 spaces for JavaScript, JSON, YAML, and Markdown lists. Prefer descriptive filenames and avoid ambiguous names like `utils2`.

- Use `snake_case` for Python files and test names
- Use `kebab-case` for directory names
- Use `PascalCase` for class names and `camelCase` for JavaScript/TypeScript functions

If you add a formatter or linter, wire it into the repository entrypoints before opening a PR.

## Testing Guidelines
Place tests under `tests/` and name them after the behavior they verify, such as `test_auth_login.py` or `user-form.test.ts`. Add tests with every behavior change or bug fix. Prefer fast, deterministic tests over network-dependent checks.

## Commit & Pull Request Guidelines
This workspace is not initialized as a Git repository yet, so no established commit convention can be inferred. Use Conventional Commits once version control is initialized, for example `feat: add API client` or `fix: handle empty config`.

PRs should include:

- a short description of the change
- linked issue or task reference when available
- test evidence
- screenshots or sample output for UI- or UX-facing changes

## Configuration & Security
Do not commit secrets, credentials, or local environment files. Keep sample configuration in checked-in templates such as `.env.example`, and document required variables in `docs/` or the project README.

If external repositories or articles influence the design, adapt ideas rather than copying upstream code or docs verbatim unless license and attribution requirements are clearly satisfied.
