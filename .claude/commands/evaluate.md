---
description: Evaluate whether an external repo, local folder, or article contains ideas worth adopting into this project.
---

# Evaluate

Investigate whether the provided target has anything worth adopting, adapting, or explicitly skipping for this repository.

## Usage

```text
/evaluate <repo-url | local-path | article-url> [additional targets...] [focus notes]
```

Examples:

```text
/evaluate https://github.com/example/project
/evaluate /tmp/sample-app focus on testing patterns
/evaluate https://example.com/article prioritize architecture and DX ideas
/evaluate https://github.com/org/repo-a https://github.com/org/repo-b compare reusable patterns
```

## Workflow

1. Parse `$ARGUMENTS` into one or more targets plus optional evaluation notes.
2. Determine each target type:
   - GitHub repository
   - local folder or local repository
   - article, blog post, or documentation page
3. Validate access to each target before proceeding.
4. For repositories or folders:
   - inspect high-signal files first such as `README*`, `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Dockerfile*`, CI config, docs, and primary source directories
   - extract only concrete candidate additions such as architecture patterns, tooling choices, testing approaches, developer workflows, configuration structure, documentation patterns, or reusable implementation ideas
5. For articles:
   - extract only concrete and transferable ideas
   - distinguish implementation details from higher-level concepts
6. Compare findings against this repository's actual state before recommending them.
7. For external repositories or articles, assess license and reuse risk before suggesting adoption.

## Evaluation Criteria

Judge each candidate by:

- relevance to the current project/template
- implementation clarity
- maintenance cost
- compatibility with existing structure
- likely impact on developer workflow, reliability, or maintainability
- license fit and reuse safety

Prefer specific, implementable ideas over vague praise.
Do not recommend verbatim reuse from sources with restrictive or unclear licensing; prefer conceptual adaptation in those cases.

## Output Format

Render exactly these five sections:

## 1. Executive verdict

Choose one:

- `Yes, adopt now`
- `Yes, adapt selectively`
- `No meaningful addition`

Add one short paragraph explaining why.

## 2. Ranked beneficial additions

If there are worthwhile additions, render one markdown table with:

- `Rank`
- `Candidate`
- `Adopt type`
- `Why it matters`
- `Expected impact`
- `Integration fit`
- `Effort / complexity`
- `Risks / downsides`
- `Evidence`

Use these adoption labels exactly:

- `Directly adopt`
- `Adapt conceptually`

If there are no worthwhile additions, write `None`.

## 3. Why it helps

Explain how each accepted candidate improves this repository or template.

If section 2 is `None`, write `No meaningful additions identified.`

## 4. Expected impact

Summarize likely impact across:

- capability coverage
- workflow quality
- reliability
- operator or developer efficiency
- maintainability

## 5. Highest-impact next steps

Use exactly these buckets:

### Add now

### Consider later

### Skip

Keep items concrete and brief.
