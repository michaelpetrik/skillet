# Python Variant

Use this reference when the active repo is Python-first or when Python is the changed surface.

## Prefer these sources of truth

- `pyproject.toml` as the primary manifest when available.
- A pinned lockfile such as `uv.lock`, `poetry.lock`, or hashed requirements generated from a checked-in source file.
- A version-controlled runtime pin such as `.python-version`, `mise.toml`, or an equivalent repo-owned manifest.
- GitNexus or an equivalent code-intelligence workflow when the repo is large enough that impact-aware edits matter, preferably through the official GitNexus CLI and skill set.
- A checked-in bootstrap script for pinned CLI tools.
- A pinned Python documentation stack, typically `pdoc` for local API docs and static HTML plus `pydeps` and `pyreverse` with Graphviz for dependency and structure visuals. If the repo already has healthy `Sphinx` or `MkDocs` automation, preserve it instead of layering a second stack.

Avoid ambient virtualenv state as policy. The repo needs a checked-in source of truth.

## Fresh-repo default

If the repo has no local guardrails yet, a good baseline is:

- GitNexus installation and indexing for non-trivial Python repos, plus local rules that require the official GitNexus exploration and impact-analysis flows before risky edits;
- a pinned interpreter and tool manifest plus `scripts/ci/install_dev_tools.sh`;
- `.githooks/pre-commit` with an installer, or `.pre-commit-config.yaml` with local hooks only;
- `scripts/ci/run_quality_gates.sh` as the thin orchestrator;
- `scripts/ci/python_docs_gate.sh` or a repo-local equivalent for offline docs generation and rendering;
- `scripts/devel/pdoc.sh` or a repo-local equivalent when the repo wants a local documentation browser;
- `scripts/ci/run_security_review.sh` for security-specific checks;
- dedicated secret-scan, handoff, and Docker/runtime checks where relevant.

## Quality gate content

Prefer the repo-pinned equivalent of:

- GitNexus or equivalent code-intelligence checks before structural refactors or edits to widely used modules;
- formatting, for example `ruff format --check` or `black --check`;
- linting, for example `ruff check` or `flake8`;
- type checking when the repo uses typing, for example `mypy` or `pyright`;
- tests through the repo's normal entrypoint, usually `pytest`;
- dependency and lockfile hygiene checks tied to the repo's package workflow.

If the repo is plain Python without a typing discipline, type checking can be `N/A`. State that explicitly.

## Documentation gate content

Prefer the repo-pinned equivalent of:

- `pdoc` for local browsing and static HTML API docs;
- `pydeps` for import and dependency graphs;
- `pyreverse` with Graphviz for package or class UML-style diagrams;
- a stable docs index or `README` section that exposes generated docs and rendered SVG or PNG artifacts offline.

If the repo already has a mature `Sphinx` or `MkDocs` stack with pinned local entrypoints, preserve that as the primary generator and add architecture visualization only if it is missing. Do not introduce a second documentation framework without a clear gap.

## Local security review content

Prefer the repo-pinned equivalent of:

- offline static security scanning, for example `bandit` or locally pinned Semgrep rules;
- diff-aware secret scanning;
- Docker and runtime hardening checks when the repo ships containers or runtime images;
- manual review of deserialization, template rendering, shell execution, SQL boundaries, auth, and secret handling.

Dependency vulnerability audit only counts as `enforced` when the repo provides a pinned local advisory mirror or cache strategy. If it depends on live network queries, mark it `partial` or `blocker`.

Manual review can be required, but it is never `enforced` by itself.

## Status rules

- No lockfile or hashed requirements path is a `blocker`, not `N/A`.
- If a non-trivial Python repo has no GitNexus or equivalent impact-analysis path, mark that as `blocker`, `partial`, or `policy-only`, not acceptable by default.
- If a Python repo has no pinned offline docs gate, or the docs stack relies on ad hoc ambient tools instead of established local tooling, mark documentation enforcement as `blocker` or `partial`.
- Missing secret scanning is a `blocker` or `policy-only`, never `N/A`.
- Docker/runtime checks are `N/A` only when the repo ships no production container or runtime package.
- If the repo requires split authorship, the handoff artifact is mandatory before implementation.
