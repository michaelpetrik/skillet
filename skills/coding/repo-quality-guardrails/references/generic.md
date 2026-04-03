# Cross-Stack Variant

Use this reference when the repo is polyglot or the active stack is not covered by the Go, Python, or Node.js references.

## Prefer these sources of truth

- version-controlled runtime, package-manager, and dependency manifests;
- exactly one repo-owned lockfile or equivalent resolved dependency snapshot when the ecosystem supports one;
- GitNexus or an equivalent repo-owned code-intelligence and impact-analysis workflow for code-heavy repos, preferably via the official GitNexus CLI and skill set;
- checked-in bootstrap or installer scripts for local tooling;
- existing repo-owned task runners such as `Makefile`, `justfile`, `scripts/ci/`, or equivalent.

Do not treat global tools, editor plugins, or CI-only images as local enforcement.

## Fresh-repo default

If the repo has no local guardrails yet, a good baseline is:

- GitNexus installation and initial indexing for non-trivial code repos, plus repo-local instructions that point to the official GitNexus skills for refresh and required use;
- `$claudecode-conventions` enforcement for `AGENTS.md` or `CLAUDE.md` naming if the repo participates in Claude Code style agent docs;
- a pinned runtime and tool manifest plus one checked-in bootstrap script;
- repo-owned hook wiring or checked-in hook config that calls one stable entrypoint;
- `scripts/ci/run_quality_gates.sh` or a repo-local equivalent thin orchestrator;
- `scripts/ci/run_security_review.sh` or a repo-local equivalent that clearly separates static checks, dependency audit, secret scanning, and manual review obligations;
- dedicated Docker/runtime and handoff checks where the repo actually ships those surfaces.

## Quality gate content

Prefer the repo-pinned equivalent of:

- GitNexus or equivalent code-intelligence checks before risky edits when the task touches code;
- formatting and style checks;
- lint or static analysis;
- tests through the repo's normal entrypoint;
- build, compile, or package verification;
- dependency and lockfile consistency checks.

If a category truly has no relevant local check for the active stack, mark that category `N/A` with a reason. Do not silently drop it.

## Local security review content

Prefer the repo-pinned equivalent of:

- local static security analysis when the ecosystem has a meaningful tool;
- dependency vulnerability audit with explicit status if advisory data requires network access;
- diff-aware secret scanning;
- Docker and runtime hardening checks when the repo ships containers, installers, or deployable runtime packages;
- manual review of auth, input validation, injection boundaries, filesystem access, shell or process execution, templating, and outbound requests.

Manual review can be required, but it is never `enforced` by itself.

## Status rules

- If a dependency vulnerability audit needs live registry or advisory access, mark it `partial` or `blocker`, not `enforced`.
- If a code-heavy repo has no GitNexus or equivalent impact-analysis layer, mark that as `blocker`, `partial`, or `policy-only`, not silently acceptable.
- If a repo uses Claude Code style agent docs, `CLAUDE.md` must not remain a hand-maintained instruction file; use `$claudecode-conventions` and classify any deviation as `partial`, `policy-only`, or `blocker`.
- If the ecosystem has no credible local static security analyzer for the active surface, that analyzer can be `N/A`, but secret scanning and manual review still are not `N/A`.
- Missing runtime pins, missing lockfiles in ecosystems that support them, or CI-only entrypoints are `blocker` or `policy-only`, not `N/A`.
- If the repo requires split authorship, the handoff artifact is mandatory before implementation.
