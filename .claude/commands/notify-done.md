---
description: Execute a task normally and send a short completion notification if a supported notification connector is available.
---

# Notify Done

Treat `$ARGUMENTS` as the task to execute.

## Goal

Complete the requested work end to end, then send exactly one short notification when the task is complete or blocked.

## Execution Rules

1. Do the work using the repository's normal workflow.
2. Before the final response, send one brief notification if a supported connector or notification tool is available in the current runtime.
3. Prefer configured connectors such as Slack when they are actually available in the current session.
4. Do not assume the repository contains helper scripts or local notification wrappers.
5. If no supported notification path is available, finish the task normally and report that the notification could not be sent.
6. Never send duplicate notifications for the same task.

## Notification Content

Keep the message short and safe:

- task summary
- success or blocked status
- repository or folder name if helpful
- branch name if available
- one-line outcome summary

Do not include secrets, tokens, or large code excerpts.

If the notification connector rejects the action or lacks permissions, do not retry aggressively; finish the task and mention the limitation once.
