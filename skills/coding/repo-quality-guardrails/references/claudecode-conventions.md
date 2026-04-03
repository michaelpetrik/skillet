# Claude Code Conventions

Use `$claudecode-conventions` for Claude Code documentation naming and compatibility cleanup. Do not re-specify the same rule set in bespoke repo prose unless the repo truly has a stricter local variant.

## Required rule

- `AGENTS.md` is the canonical project-level agent instruction file.
- `CLAUDE.md` must not exist as a normal maintained document.
- If `CLAUDE.md` exists for compatibility, it must be exactly one of:
  - a symlink resolving to `AGENTS.md`, or
  - a regular file whose exact content is:

```markdown
@AGENTS.md
```

Anything else is non-compliant.

## Enforcement workflow

1. Verify `AGENTS.md` exists at the relevant repo root.
2. If `CLAUDE.md` does not exist, status is `enforced` or `N/A` depending on repo policy.
3. If `CLAUDE.md` exists:
   - merge any actionable rules into `AGENTS.md` without duplication;
   - replace `CLAUDE.md` with a relative symlink to `AGENTS.md` if symlinks are supported;
   - otherwise replace it with a file whose exact content is `@AGENTS.md`.
4. Verify postcondition: `CLAUDE.md` is only the symlink or exact redirect file above.

## Status rules

| Status | When to use |
| --- | --- |
| `enforced` | `AGENTS.md` exists and any `CLAUDE.md` is absent, a correct symlink, or an exact `@AGENTS.md` redirect. |
| `partial` | `AGENTS.md` exists, but `CLAUDE.md` still contains extra prose, stale content, or an unresolved compatibility state. |
| `policy-only` | The repo says to use `AGENTS.md`, but there is no actual cleanup of an existing `CLAUDE.md`. |
| `blocker` | `CLAUDE.md` exists as a normal maintained file, or `CLAUDE.md` exists while `AGENTS.md` is missing. |
| `N/A` | The repo does not use Claude Code style agent docs at all. |

## Installation note

If `$claudecode-conventions` is available locally but not globally discoverable, install or publish it into the global Codex skills directory before relying on it as a standard part of the guardrail stack.
