# Go Variant

Use this reference when the active repo is Go-first or when Go is the changed surface.

## Prefer these sources of truth

- `go.mod` and `go.sum` for the module graph and Go version.
- `.gitnexus/` plus the official GitNexus skills under `.claude/skills/gitnexus/`, and only minimal GitNexus instructions in `AGENTS.md` or local rules when the repo is large enough to benefit from graph-aware analysis.
- A version-controlled manifest for auxiliary tools such as `gofumpt`, `goimports`, `golangci-lint`, `govulncheck`, `gosec`, `pkgsite`, `gomarkdoc`, `goplantuml`, and `go-callvis`.
- Pinned renderer versions when the docs stack needs them, typically `plantuml` and Graphviz `dot`.
- A checked-in bootstrap script that installs pinned tools from that manifest.

Good homes for the auxiliary manifest:

- `scripts/ci/tool_versions.sh`
- `mise.toml`
- a repo-local equivalent that does not use `@latest`

## Fresh-repo default

If the repo has no local guardrails yet, a good baseline is:

- GitNexus installation and `npx gitnexus analyze` bootstrap for non-trivial repos, plus local rules that require the official GitNexus impact-analysis workflow before editing shared symbols and `detect_changes` before commit;
- a pinned manifest plus `scripts/ci/install_dev_tools.sh`;
- `.githooks/pre-commit` with an installer or checked-in `core.hooksPath` activation step, plus a diff-aware `scripts/ci/secret_scan.sh` that runs before the broader quality gate;
- `.pre-commit-config.yaml` only as a complement to the repo-owned hook path, not as the sole proof that local hooks are enforced;
- `scripts/ci/run_quality_gates.sh` as the thin orchestrator;
- `scripts/ci/go_docs_gate.sh` or a repo-local equivalent for offline documentation generation and rendering;
- `scripts/devel/pkgsite.sh` or a repo-local equivalent to browse local Go docs without network access;
- `scripts/ci/run_security_review.sh` for security-specific checks;
- dedicated checks for secrets, handoff, and Docker builds if the repo ships containers.

## Quality gate content

Prefer the repo-pinned equivalent of:

- GitNexus exploration and impact analysis before editing externally referenced symbols;
- formatter and import order checks;
- `go mod tidy -diff` when dependency manifests changed;
- `go vet`;
- `golangci-lint`;
- `go test ./...`;
- `go test -race ./...` when supported on the target platform;
- `go build ./...`.

If the repo already exposes a local gate, call that instead of inlining the commands again.

## Documentation gate content

Prefer the repo-pinned equivalent of:

- `pkgsite` as the local Go doc browser or offline viewer path;
- `gomarkdoc` to generate committed Markdown reference docs from exported Go packages;
- `goplantuml` to emit structural PlantUML source for package and type relationships;
- `go-callvis` to emit call-graph source such as DOT for runtime or package-level call paths;
- `plantuml` and Graphviz `dot` to render committed SVG artifacts from generated source formats;
- a stable docs index or `README` section that links or embeds the rendered artifacts.

Treat the Go documentation stack as incomplete if it uses only one of these categories. The baseline should cover:

- browsable local API docs;
- committed static reference docs;
- a structure visualization;
- a call-graph visualization or an explicitly documented smoke fallback when upstream tooling cannot analyze the full module.

If `go-callvis` cannot analyze the full repo because of upstream loader or language-version limitations, keep the tool pinned and exercised through a deterministic offline smoke graph, then classify full-repo callgraph coverage as `partial` rather than pretending the control is absent or fully enforced.

## Local security review content

Prefer the repo-pinned equivalent of:

- targeted `gosec` on changed packages or affected modules;
- `govulncheck ./...` or the repo's equivalent vulnerability check, with honest status if advisory data is network-backed;
- diff-aware secret scanning over staged content, including blocked secret-like files such as `.env`, `.pem`, `.key`, and `.p12`, wired into the local pre-commit path before broader gates;
- Docker and runtime checks when the repo ships containers;
- manual review of auth, input validation, injection boundaries, templates, shell calls, and outbound requests.

`gosec` and `govulncheck` are control points, not complete security proof.

## Status rules

- If the repo requires dependency vulnerability checks but only a networked path exists, mark that control `partial` or `blocker`, not `enforced`.
- If a non-trivial Go repo has no GitNexus or equivalent graph-aware impact-analysis workflow, treat that as `blocker` or `partial` until installed and documented.
- If a Go repo has only `.pre-commit-config.yaml` but no repo-owned hook entrypoint plus activation path, hook wiring stays `partial` or `blocker`, not `enforced`.
- If a Go repo lacks a diff-aware staged secret scan in the local hook path before the broader quality gate, secret scanning stays `blocker` or `policy-only`.
- If a Go repo has no pinned offline docs gate, or the docs stack is not selected from established Go tooling, treat documentation enforcement as `blocker` or `partial`, not optional.
- If docs generation depends on unpinned `plantuml`, Graphviz, or other renderers, documentation enforcement is `partial` or `blocker`.
- If `go test -race` is unsupported on the repo's target platform, mark it `N/A` with the platform constraint.
- If there is no production Dockerfile and no smoke path, Docker/runtime checks are `N/A`.
- If the repo requires split authorship, the handoff artifact is mandatory before implementation.
