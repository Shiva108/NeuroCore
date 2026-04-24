---
description: Fetch, review, stage, commit, push, and verify git state using a safe, non-destructive workflow.
---

# Git Workflow

Perform a safe git workflow for the current repository.

## Step 1: Confirm Repository State

- If the current directory is not a Git repository, stop and report that clearly.
- Do not initialize a new repository, add a remote, or infer hosting defaults unless the user explicitly asks.
- Otherwise determine the current branch and inspect working tree state.
- Review recent commits and remote tracking information before making changes.

## Step 2: Sync Carefully

- Fetch remote refs first.
- If the branch has diverged from its upstream, prefer rebasing local commits on top of remote work.
- If conflicts appear and they are not straightforward, stop and explain the blocker.
- Never force push unless the user explicitly asks.

## Step 3: Review and Stage

- Review changed and untracked files before staging.
- Prefer staging specific files over broad staging when practical.
- Do not stage obvious secrets, credentials, or local environment files.

## Step 4: Commit

- If there is nothing to commit, say so plainly.
- Otherwise write a concise commit message that reflects the actual change.
- Do not amend existing commits unless the user explicitly asks.

## Step 5: Push and Verify

- Push to the current branch's upstream, using `-u` only when needed.
- If the push fails due to remote changes, sync once and retry.
- Finish by confirming whether the working tree is clean and whether the branch is in sync.

## Rules

- Never use `--no-verify` unless the user explicitly asks.
- Never use destructive reset or checkout commands unless explicitly requested.
- Summarize what happened in plain language rather than pasting raw git status headers.
