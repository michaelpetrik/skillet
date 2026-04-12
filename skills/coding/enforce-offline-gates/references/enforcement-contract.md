# Enforcement Contract

## Mandatory gate properties

- Execute fully offline for baseline pass/fail.
- Run deterministically across developer machines and CI.
- Use versioned repository scripts as single source of truth.
- Fail on required warning classes (or convert warnings to errors).

## Mandatory workflow

1. Detect stack.
2. Select compatible tools.
3. Install and pin dependencies.
4. Wire gate scripts.
5. Wire git hooks.
6. Execute RED -> GREEN -> REFACTOR validation.
7. Record evidence and unresolved exceptions.

## Minimal repository artifacts

- `scripts/ci/run_quality_gates.sh` (or equivalent)
- `scripts/ci/run_security_review.sh` (or equivalent)
- `scripts/ci/run_offline_static_gates.sh` (or equivalent)
- `.githooks/pre-commit`
- `.githooks/pre-push`
- hook installer script
- policy document with non-bypass language (`AGENTS.md` preferred)

## Hook contract

- `pre-commit`:
- Run fast deterministic quality gates.
- Reject commit on failure.
- `pre-push`:
- Run full quality and security gates.
- Reject push on failure.

## Non-bypass policy text (recommended)

- MUST ALWAYS run required gate entrypoints before merge/release.
- MUST ALWAYS use repo-owned scripts for hooks and CI.
- MUST NEVER bypass hooks with `--no-verify` except explicit, time-bounded exception.
- MUST NEVER mark task done when any required gate is failed or skipped.

## Verification evidence

- Keep exact command log and exit status for:
- offline gates
- quality gates
- security gates
- Include summary:
- installed tools and versions
- changed files
- remaining low-risk findings (if accepted by policy)
