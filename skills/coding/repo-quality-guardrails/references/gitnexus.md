# GitNexus

Treat GitNexus as one of the highest-value guardrails for non-trivial code repositories. It is not a formatter or linter; it is the repo-owned code-intelligence and impact-analysis layer that makes edits, refactors, and reviews safer.

## Prefer the official GitNexus skill stack

Do not invent a bespoke GitNexus workflow if the official GitNexus skills and generated repo context can do the job.

Prefer these official skills and artifacts:

- `gitnexus-cli` for install, indexing, refresh, cleanup, and registry status;
- `gitnexus-exploring` for architecture and code-understanding work;
- `gitnexus-impact-analysis` for blast-radius checks before edits and pre-commit scope verification;
- `gitnexus-refactoring` for rename, extract, split, and other structural changes;
- `gitnexus-debugging` when the task is failure analysis;
- `gitnexus-guide` as the reference for tools, resources, and schema;
- the GitNexus-generated context block in `AGENTS.md` or equivalent repo docs, if present.

This skill should steer the repo toward using those official GitNexus skills and generated context, not toward copying large custom GitNexus sections into local policy files.

## Default Rule

- If the repo already uses GitNexus, enforce it.
- If the repo is a meaningful source-code repo and has no equivalent code-graph or impact-analysis system, classify that gap honestly. Install and configure GitNexus only when the task scope is to close the missing-control gap, not during audit by reflex.
- If the repo is tiny, throwaway, or not actually code-centric, GitNexus can be `N/A`, but say why explicitly.

Equivalent tools only count if they provide materially similar local capabilities for:

- concept search over code structure, not just text grep;
- symbol context and caller or callee discovery;
- impact analysis before edits;
- pre-commit or pre-merge changed-scope verification;
- safe rename or refactor assistance.

If those are missing, treat the repo as not having an equivalent.

## What "installed and configured" means

Do not call GitNexus `enforced` just because `npx gitnexus` happens to work on one machine. The repo should have all or most of these:

- `.gitnexus/` index or a documented bootstrap path to create it;
- official GitNexus skills available under `.claude/skills/gitnexus/` or an equivalent repo-local GitNexus skill distribution;
- GitNexus referenced from `AGENTS.md`, `rules/`, or equivalent local engineering policy, ideally through the generated GitNexus context block instead of hand-written prose;
- a local installation or bootstrap step, usually `npx gitnexus analyze`, documented in repo-owned instructions;
- a freshness rule for stale indexes;
- explicit edit workflow requirements such as impact analysis before changing externally used symbols and `detect_changes` before commit.

Good bootstrap path:

```bash
npx gitnexus analyze
```

If the repo wants semantic search and can afford embeddings, the bootstrap may use:

```bash
npx gitnexus analyze --embeddings
```

Recommended setup sequence:

1. Use the official `gitnexus-cli` skill to run `npx gitnexus analyze` from the repo root.
2. Verify the index via `npx gitnexus status` or `gitnexus://repo/{name}/context`.
3. Reuse the generated GitNexus block in `AGENTS.md` if GitNexus writes one. Do not manually expand it unless the repo has a real local deviation to document.
4. Point repo workflow guidance at the official GitNexus skills instead of embedding long custom instructions in local docs.

Do not replace an existing equivalent local workflow just to standardize names. If the repo already has a materially similar graph-aware system, document the equivalence and any real gaps instead of forcing a migration.

## Minimum enforcement expectations

If GitNexus exists, the repo should require the local equivalent of:

- use the official `gitnexus-exploring` flow for code understanding before falling back to broad text search;
- use the official `gitnexus-impact-analysis` flow before editing functions, classes, methods, or other externally used symbols;
- warn or stop on HIGH or CRITICAL impact;
- run changed-scope detection before commit or merge;
- use the official `gitnexus-refactoring` flow instead of blind find-and-replace when refactoring symbols.

For repos that expose these controls in `AGENTS.md` only, status is `policy-only` or `partial` until local execution paths and developer habit are made concrete.

## Status rules

| Status | When to use |
| --- | --- |
| `enforced` | GitNexus is installed or bootstrapable from repo-owned instructions, indexed for the repo, wired into local instructions, and edit or commit workflow requires it in practice. |
| `partial` | GitNexus exists, but indexing is stale, optional, undocumented, CI-only, or not consistently required before edit or commit. |
| `policy-only` | The repo says to use GitNexus, but there is no working local setup or enforcement path. |
| `blocker` | The repo expects safe impact-aware edits, but has neither GitNexus nor an equivalent and no honest fallback workflow. |
| `N/A` | The repo is not a meaningful source-code surface for graph-based analysis, or the task does not touch code. State that explicitly. |

## Honest fallback when GitNexus cannot be active yet

If GitNexus is temporarily unavailable, incomplete, or still being installed, require a documented fallback instead of pretending the control passed. Good fallback ingredients:

- language-native symbol tools such as `gopls`, LSP references, or framework-aware IDE queries;
- focused `rg` or code search;
- narrower refactor scope;
- extra targeted tests around the affected symbols;
- explicit note in the handoff or review record that GitNexus was unavailable.

This is `partial`, not `enforced`.

## Integration with the rest of the guardrail stack

GitNexus should influence:

- local editing workflow;
- review expectations;
- refactor rules;
- task records or handoff notes for high-risk changes;
- repo docs that tell developers when to refresh the index.

Keep local AGENTS additions minimal:

- prefer the GitNexus-generated context block if present;
- point to the official GitNexus skills by name or path instead of pasting long custom workflows;
- only add extra local GitNexus rules when the repo truly has a stricter local requirement than the official GitNexus defaults.

It does not replace tests, static analysis, or security review. It complements them by reducing blind edits and hidden blast radius.
