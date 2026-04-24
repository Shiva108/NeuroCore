---
description: Create a spec-driven design package and implementation plan for a feature, subsystem, or project initiative in this repository.
---

# Spec-Driven Design Implementation Plan

Create a complete, implementation-ready spec package for the requested work in this repository.

Task: `$ARGUMENTS`

If the request is underspecified, infer the most likely project goal from the surrounding repo context and state your assumptions clearly.

If `docs/ssd/` already exists, update the existing package in place instead of creating duplicate design files.

## Deliverables

Produce documentation that is clear enough for another engineer or agent to implement without guessing. Prefer storing the output under `docs/ssd/` unless the repo already has a better-established design-doc location. Create `docs/ssd/` first if it does not exist.

Recommended files:

- `docs/ssd/architecture.md`
- `docs/ssd/specification.md`
- `docs/ssd/implementation-plan.md`

Also reconcile with nearby guidance such as `AGENTS.md`, `.claude/commands/README.md`, and any checked-in task tracker if they materially affect implementation shape.

If a single document is a better fit for the current repo, say so and keep the structure clear inside that file.

## What the Spec Package Should Cover

### 1. Architecture

- problem statement
- goals and non-goals
- major components and responsibilities
- data flow or request flow
- dependencies and integration points
- key constraints and tradeoffs

### 2. Functional Specification

- expected behavior
- public interfaces, inputs, outputs, and schemas
- failure modes and edge cases
- configuration needs
- migration or compatibility concerns, if any

### 3. Implementation Plan

Provide numbered, actionable steps that:

- are sequential and testable
- name any files or directories to create or update when that matters
- note validations after meaningful milestones
- separate setup, core implementation, and follow-up hardening work

### 4. Verification

Include:

- test strategy
- acceptance criteria
- rollout or handoff notes when relevant

## Working Style

- Use repository reality first: existing languages, frameworks, and folder conventions
- Prefer the template structure `src/`, `tests/`, `assets/`, and `docs/` when no stronger convention exists
- Do not invent technology requirements that the repo does not imply unless the task explicitly calls for them
- If the repo is still docs-first, make the package explicit about what is decided now versus deferred until runtime selection

## Output Structure

Render the result in this order:

1. Architecture overview
2. Specification details
3. Implementation plan
4. Test and validation plan
5. Assumptions
