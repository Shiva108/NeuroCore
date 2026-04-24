# Security Guide

NeuroCore is designed to handle sensitive memory artifacts. Treat repository
publication and local operator configuration as separate concerns.

## Never Commit Secrets

Keep these files local only:

- `.env`
- `secrets.json`
- `preferences.json`
- `token.json`
- anything under `data/` or `outputs/`

The repository ships only example files so contributors can see the expected
shape without exposing real credentials.

## API Keys And Production URLs

- Do not paste real API keys into README examples, issues, PRs, or screenshots.
- Do not publish Postgres or Neon connection strings in discussions or CI logs.
- Prefer environment variables for runtime credentials and rotate any key that is
  accidentally exposed.

## Safe Publication Checklist

1. Confirm `.gitignore` is present before initializing Git.
2. Review staged files for `.env`, `token.json`, `secrets.json`, or database
   files.
3. Run `python -m neurocore.governance.validation` to catch obvious secret-like
   values in tracked files.
4. Redact screenshots if they ever include IDs, URLs, or operational metadata.

## Sensitive Data Handling

- Use the sealed sensitivity path for data that should not appear in normal
  retrieval flows.
- Keep admin operations disabled unless explicitly needed.
- Avoid enabling optional adapters in public demos unless they are configured and
  tested for the environment you are using.
