# Tooling Matrix

## JavaScript / TypeScript

- Baseline quality:
- `eslint` + `@eslint/js` + `typescript-eslint`
- `oxlint` with deny-warnings mode
- `prettier`
- Architecture and dependency boundaries:
- `dependency-cruiser`
- `eslint-plugin-import`
- `eslint-plugin-boundaries`
- Dependency hygiene:
- `knip`
- Security:
- `eslint-plugin-security`
- `eslint-plugin-no-unsanitized`
- `npm audit --audit-level=high`
- `gitleaks` (recommended)

## Next.js

- Add:
- `eslint-config-next`
- `@next/bundle-analyzer` (bundle regression awareness)
- `@lhci/cli` (offline lighthouse runs and thresholds)
- Prefer App Router aware linting and route boundary checks.

## Python

- Quality:
- `ruff` (lint + format)
- `mypy` (typing)
- `pytest`
- Security:
- `bandit`
- `pip-audit`
- `gitleaks` (recommended)

## Go

- Quality:
- `golangci-lint`
- `go test ./...`
- Security:
- `govulncheck`
- `gosec`

## Rust

- Quality:
- `cargo fmt --check`
- `cargo clippy --all-targets --all-features -- -D warnings`
- `cargo nextest run` (or `cargo test`)
- Security:
- `cargo audit`

## JVM (Java/Kotlin)

- Quality:
- `spotbugs` / `detekt` / `checkstyle` (depending on stack)
- build-tool-native tests and check tasks
- Security:
- dependency-check and SBOM/vulnerability scan tool compatible with build system

## Universal policy

- Keep one canonical command per category:
- `quality`
- `security`
- `offline` / `static`
- Run hooks through repo-owned scripts.
- Fail deterministically: no interactive prompts, no best-effort mode in required gates.
