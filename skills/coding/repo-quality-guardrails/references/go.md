# Go Variant

Use this reference when the active repo is Go-first or when Go is the changed surface.

## Prefer these sources of truth

- `go.mod` and `go.sum` for the module graph and Go version.
- `.gitnexus/` plus the official GitNexus skills under `.claude/skills/gitnexus/`, and only minimal GitNexus instructions in `AGENTS.md` or local rules when the repo is large enough to benefit from graph-aware analysis.
- A version-controlled manifest for auxiliary tools such as `gofumpt`, `goimports`, `golangci-lint`, `govulncheck`, and `gosec`.
- A checked-in bootstrap script that installs pinned tools from that manifest.

Good homes for the auxiliary manifest:

- `scripts/ci/tool_versions.sh`
- `mise.toml`
- a repo-local equivalent that does not use `@latest`

## Fresh-repo default

If the repo has no local guardrails yet, a good baseline is:

- GitNexus installation and `npx gitnexus analyze` bootstrap for non-trivial repos, plus local rules that require the official GitNexus impact-analysis workflow before editing shared symbols and `detect_changes` before commit;
- a pinned manifest plus `scripts/ci/install_dev_tools.sh`;
- `.githooks/pre-commit` with an installer, or `.pre-commit-config.yaml` with a local repo-owned entrypoint;
- `scripts/ci/run_quality_gates.sh` as the thin orchestrator;
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

## Local security review content

Prefer the repo-pinned equivalent of:

- targeted `gosec` on changed packages or affected modules;
- `govulncheck ./...` or the repo's equivalent vulnerability check, with honest status if advisory data is network-backed;
- diff-aware secret scanning;
- Docker and runtime checks when the repo ships containers;
- manual review of auth, input validation, injection boundaries, templates, shell calls, and outbound requests.

`gosec` and `govulncheck` are control points, not complete security proof.

## Status rules

- If the repo requires dependency vulnerability checks but only a networked path exists, mark that control `partial` or `blocker`, not `enforced`.
- If a non-trivial Go repo has no GitNexus or equivalent graph-aware impact-analysis workflow, treat that as `blocker` or `partial` until installed and documented.
- If `go test -race` is unsupported on the repo's target platform, mark it `N/A` with the platform constraint.
- If there is no production Dockerfile and no smoke path, Docker/runtime checks are `N/A`.
- If the repo requires split authorship, the handoff artifact is mandatory before implementation.
