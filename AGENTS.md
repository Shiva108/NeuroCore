# Repository Guidelines

## Project Structure & Module Organization
This repository contains a working Python implementation, and `docs/ssd/`
remains the active contract source of truth for the core system. Keep the
layout predictable as code, docs, and ecosystem modules evolve:

- `src/` for application code
- `tests/` for automated tests
- `assets/` for static files such as images or sample data
- `docs/` for design notes, architecture decisions, and onboarding material
- `extensions/`, `primitives/`, `recipes/`, `skills/`, `dashboards/`,
  `integrations/`, and `schemas/` for ecosystem contributions
- `.claude/commands/` for reusable slash-command prompt files kept out of the repo root

Current repo-specific notes:

- keep `docs/ssd/` aligned with any architectural or scope change
- keep ecosystem contribution docs and metadata aligned with the current runtime
  behavior
- keep `.claude/commands/` prompts discovery-first and consistent with repo reality
- do not introduce alternative top-level planning folders when `docs/` already covers that need

Prefer small, focused modules. Mirror `src/` paths inside `tests/` where practical, for example `src/api/client.js` and `tests/api/test_client.js`.

## Build, Test, and Development Commands
Core entrypoints are already defined in this repository. Prefer documented
commands instead of ad hoc scripts.

Recommended patterns:

- `python scripts/bootstrap.py` for the fastest local setup
- `make test` or `pytest` to run the test suite
- `make lint` to run formatting and static checks
- `make validate` or `python -m neurocore.governance.validation` to run the
  repo contract checks
- `neurocore serve http` and `neurocore serve mcp` for the blessed local
  runtime paths

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
Use Conventional Commits for repository history, for example `feat: add API
client` or `fix: handle empty config`.

PRs should include:

- a short description of the change
- linked issue or task reference when available
- test evidence
- screenshots or sample output for UI- or UX-facing changes

## Configuration & Security
Do not commit secrets, credentials, or local environment files. Keep sample configuration in checked-in templates such as `.env.example`, and document required variables in `docs/` or the project README.

If external repositories or articles influence the design, adapt ideas rather than copying upstream code or docs verbatim unless license and attribution requirements are clearly satisfied.
