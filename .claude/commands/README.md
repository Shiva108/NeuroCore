# Command Prompts

This folder is the canonical home for reusable slash-command prompt files in this repository.

Guidelines:

- Store runnable command prompts here, not in the repository root.
- Keep prompts generic to the current repo unless a file is intentionally project-specific.
- Prefer discovery-first instructions over hardcoded toolchains, file counts, or paths.
- Scale commands to repo reality. This repo now uses a Python + `pytest` workflow, so prompts should not pretend the runtime is still undecided.
- Prompts that mention storage, adapters, or governance should reflect the implemented SQLite, FastAPI, MCP, and repo-gate surfaces instead of a hypothetical future stack.
- Any command that can edit files should say what is safe to auto-apply versus what still requires explicit confirmation.
- When prompts reference each other, use `.claude/commands/<name>.md`.

Recommended organization:

- One command per file
- Kebab-case filenames
- Short frontmatter with a generic `description`

The repository root should stay focused on source, tests, docs, assets, and core project files.
