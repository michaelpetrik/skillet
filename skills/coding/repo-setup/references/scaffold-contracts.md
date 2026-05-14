# Scaffold Contracts

## Canonical File Tree

```text
.ralph/
  ralph.yaml
  loops/
    01-bootstrap-quality.yaml
    02-tdd-spark-change.yaml
    03-release-deploy-observe.yaml
  contracts/
    spark-locked-task.md
  state/
    task-state.schema.yaml
  templates/
    handoff.md
    release-checklist.md
  runs/
    .gitkeep

docs/
  architecture/
    NNNN-ralph-ai-development-orchestration.md
  ai-development/
    ralph-orchestration.md
    tdd-split-rules.md
    spark-prompt-contract.md
    handoffs/
      .gitkeep
  release/
    deployment-flow.md
```

`runs/` may be gitignored if it stores raw local agent traces. Sanitized handoff summaries should be committed under `docs/ai-development/handoffs/` when useful for audit.

## Loop Config Shape

Use this structure as a repo contract unless the real Ralph runtime requires a different schema:

```yaml
schema_version: 1
id: tdd-spark-change
policy_mode: true
purpose: normal feature, bugfix, and refactor loop
states:
  - intake
  - analyzed
  - locked_task
  - red_tests
  - spark_impl
  - verified
  - reviewed
  - release_candidate
hard_rules:
  - test_author.agent_id must not equal implementation_author.agent_id
  - implementation model must be Codex Spark unless explicitly overridden
  - implementation worker must not edit tests for the same task
  - implementation worker must stay inside owned_paths
gates:
  - spec-reviewed
  - adr-current
  - red-test-proof
  - green-test-proof
  - scope-check
  - quality-command
  - secret-scan
  - gitnexus-detect-changes
```

## Task State Template

```yaml
schema_version: 1
task_id: DASH-001
feature_id: DASH
status: locked_task
title: Short imperative title
risk_tier: C1

decisions_locked: true
adr_refs:
  - docs/architecture/0001-example.md

authors:
  orchestrator: null
  test_author: null
  implementation_author: null
  reviewer: null
  release_operator: null

scope:
  read: []
  write: []
  forbidden: []
  max_files_changed: 3

acceptance_criteria:
  - id: AC1
    text: Given ..., when ..., then ...

definition_of_done:
  - Red test authored by a separate instance.
  - Implementation authored by Codex Spark.
  - Quality command passes.
  - Scope and handoff gates pass.

test_handoff:
  required: true
  red_expected: true
  failing_command: null
  expected_failure: null
  evidence_path: null

implementation:
  model: gpt-5.3-codex-spark
  prompt_contract: .ralph/contracts/spark-locked-task.md
  stop_conditions:
    - needs architecture decision
    - needs test edits
    - needs forbidden path
    - needs new dependency

gate_results: []
release_handoff: null
```

## ADR Template

```md
# NNNN Short Decision Title

Date:
Status: Proposed | Accepted | Superseded
Feature:
Owner:

## Context

## Decision

## Alternatives Considered

## Consequences

## Security / Operations Impact

## Affected Tasks

## Reversal Criteria
```

## Handoff Template

```md
# Handoff: TASK-ID

Run:
Task:
From:
To:
State From:
State To:

## Inputs

- Spec:
- ADRs:
- Owned paths:
- Forbidden paths:

## Evidence

- Red command:
- Red result:
- Green command:
- Green result:
- Quality command:
- Secret scan:
- GitNexus:

## Authorship

- Test author:
- Implementation author:
- Reviewer:
- Split authorship verified: yes/no

## Notes
```

## Release Checklist Template

```md
# Release Checklist: RELEASE-ID

Version:
Commit:
Image tag:
Image digest:
Target environment:
Rollback target:

## Gates

- [ ] Quality command passed
- [ ] Docker image built
- [ ] Compose config valid
- [ ] Health endpoint passed
- [ ] Smoke route passed
- [ ] Observability check passed
- [ ] Rollback command documented
- [ ] Approval recorded

## Release Notes

## Rollback

## Audit
```
