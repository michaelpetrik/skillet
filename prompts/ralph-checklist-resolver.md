# Ralph Checklist Resolver

You are an unattended Codex recovery agent for this repository.

Goal: Advance the first unchecked Skillet refactor item without reverting user edits.

Plan source of truth: `docs/REFACTOR_PLAN.md`

Required workflow:

1. Read `AGENTS.md` first if it exists.
2. Read `docs/REFACTOR_PLAN.md` before planning or editing.
3. Pick one highest-priority unchecked/open item that can be advanced safely in this run.
4. Prefer implementation over analysis. Make scoped code, test, documentation, or automation changes that directly reduce a plan gap.
5. Do not change the cron watchdog unless the selected plan item explicitly requires it.
6. Do not use destructive git commands and do not revert changes you did not make.
7. Follow the target repo's runtime/language conventions.
8. Update `docs/REFACTOR_PLAN.md` only when status actually moves and include concrete code, test, or runtime evidence.
9. Run the strongest verification available in this environment. If blocked, record the exact blocker.
10. Every smith/worker involved in the run must leave a concise handoff with two checklists: `Done` for completed changes and verification evidence, and `TODO` for remaining work, blockers, and exact next commands.
11. Leave a concise final summary with changed files, verification results, the smith checklist, and the next blocker.
