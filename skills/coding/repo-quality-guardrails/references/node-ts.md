# Node.js and TypeScript Variant

Use this reference when the active repo is Node.js, JavaScript, or TypeScript.

## Prefer these sources of truth

- `package.json` plus exactly one checked-in lockfile.
- A pinned runtime and package-manager declaration such as `packageManager`, `.nvmrc`, `.node-version`, `volta`, or `mise.toml`.
- GitNexus or an equivalent code-intelligence workflow when the repo is large enough that cross-module impact and refactor safety matter, preferably through the official GitNexus CLI and skill set.
- A checked-in bootstrap script that installs the pinned package manager and local CLI tools.
- A pinned docs stack selected from established local tooling: `TypeDoc` for TypeScript API docs, `JSDoc` for JavaScript-first repos, and `dependency-cruiser` or `madge` plus Graphviz for architecture graphs.

Do not treat global `npm`, `pnpm`, or `yarn` state as policy.

## Fresh-repo default

If the repo has no local guardrails yet, a good baseline is:

- GitNexus installation and indexing for non-trivial Node.js or TypeScript repos, plus local rules for the official GitNexus impact-analysis flow before editing widely used modules or public APIs;
- a pinned Node and package-manager manifest plus `scripts/ci/install_dev_tools.sh`;
- `.githooks/pre-commit` with an installer, or a repo-local hook config that calls one checked-in entrypoint;
- `scripts/ci/run_quality_gates.sh` as the thin orchestrator;
- `scripts/ci/docs_gate.sh` or a repo-local equivalent for offline docs generation and graph rendering;
- `scripts/ci/run_security_review.sh` for security-specific checks;
- dedicated secret-scan, handoff, and Docker/runtime checks where relevant.

## Quality gate content

Prefer the repo-pinned equivalent of:

- GitNexus or equivalent code-intelligence checks before risky refactors, API shape changes, or edits in shared modules;
- formatting, for example `prettier --check`;
- linting, for example `eslint`;
- type checking for TypeScript, for example `tsc --noEmit`;
- tests through the repo's normal entrypoint;
- lockfile and package-manager consistency checks.

If the repo is JavaScript-only and has no type-checking layer, TypeScript checks can be `N/A`. State that explicitly.

## Documentation gate content

Prefer the repo-pinned equivalent of:

- `TypeDoc` for TypeScript API docs, or `JSDoc` when the repo is JavaScript-first;
- `dependency-cruiser` or `madge` to generate dependency or architecture graphs;
- Graphviz or the repo's pinned renderer when the graph tool emits DOT or a similar source format;
- a stable docs index or `README` section that exposes the generated offline docs and diagrams.

Do not treat Storybook, Docusaurus, or a product-doc site alone as the engineering documentation gate unless the repo also proves API and architecture documentation generation from source.

## Local security review content

Prefer the repo-pinned equivalent of:

- diff-aware secret scanning;
- static security lint or rules that are checked into the repo;
- Docker and runtime hardening checks when the repo ships containers or deployable runtime images;
- manual review of auth, SSR or template rendering, `eval`, `Function`, `child_process`, SQL or command boundaries, and outbound requests.

Dependency vulnerability audit only counts as `enforced` when the repo provides a pinned local advisory mirror or cache strategy. If it depends on live registry queries, mark it `partial` or `blocker`.

Manual review can be required, but it is never `enforced` by itself.

## Status rules

- Missing lockfile or unpinned package manager is a `blocker`, not `N/A`.
- If a non-trivial Node.js or TypeScript repo has no GitNexus or equivalent impact-analysis path, mark that as `blocker`, `partial`, or `policy-only`, not acceptable by default.
- If the repo lacks a pinned offline docs gate built on established local tooling, mark documentation enforcement as `blocker` or `partial`.
- Missing secret scanning is a `blocker` or `policy-only`, never `N/A`.
- Docker/runtime checks are `N/A` only when the repo ships no production container or runtime package.
- If the repo requires split authorship, the handoff artifact is mandatory before implementation.
