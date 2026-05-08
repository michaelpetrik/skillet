# Orchestration — When and How to Spawn Sub-Agents

This skill scales from a single-pass extraction (small input) up to an 8-agent multi-analyst-synthesis (mixed sources, large surface).

## Decision tree

```
Is the input a single small artifact (< 50 nodes / 1 screen / 1 config)?
  YES → single-pass (this agent does everything)
  NO  → continue

Is the input a single source type, but large (50–500 nodes / 2–5 screens)?
  YES → 3-agent fanout
  NO  → continue

Is the input a single source type, very large (500+ nodes / 6+ screens)?
  YES → 6-agent fanout
  NO  → continue

Is the input MIXED (e.g., .pen + url + screenshots + tailwind config)?
  YES → 8-agent multi-analyst-synthesis
```

## Topologies

### 1) Single-pass (default for tiny inputs)

No `Task` calls. Do all phases inline.

### 2) 3-agent

Run in parallel via three `Task` calls:

```
Task[1] = Token-Auditor       → token tree
Task[2] = Component-Auditor   → component manifest
Task[3] = Pattern-Detector    → spacing/type/motion rhythm
```

Then this agent (consolidator) merges and runs Builder + Reviewer inline.

### 3) 6-agent

Add Visual-Analyst (image/url) or Code-Parser (code), DS-Architect, and Reviewer.

```
Task[1] = Token-Auditor
Task[2] = Component-Auditor
Task[3] = Pattern-Detector
Task[4] = Visual-Analyst   OR   Code-Parser   (depending on input mode)
Task[5] = DS-Architect
Task[6] = Builder
```

Reviewer runs inline as the gate.

### 4) 8-agent multi-analyst-synthesis (mixed sources)

```
Task[1] = Token-Auditor
Task[2] = Component-Auditor
Task[3] = Pattern-Detector
Task[4] = Visual-Analyst
Task[5] = Code-Parser
Task[6] = DS-Architect
Task[7] = Builder
Task[8] = Reviewer
```

Run analysts (1–5) in parallel. Then DS-Architect (6) consolidates. Then Builder (7) materializes. Then Reviewer (8) gates.

## Dispatch templates

Each analyst has a prompt template in `agents/`. The orchestrator fills placeholders:

| Placeholder | Source |
|---|---|
| `{{input_pen_doc}}` | path to `.pen` file |
| `{{image_path}}` | path to PNG/JPG |
| `{{url}}` | live page URL |
| `{{repo_root}}` | local code repo root |
| `{{token_taxonomy}}` | inline reference to `tokens-taxonomy.md` |
| `{{atomic_rules}}` | inline reference to `atomic-design.md` |
| `{{prior_token_tree}}` | output from Token-Auditor (Builder & Reviewer) |
| `{{component_manifest}}` | output from Component-Auditor (Builder & Reviewer) |

## Communication contract

Every analyst returns **structured JSON-shaped markdown** with these top-level keys:

```yaml
findings:           # the analyst's primary output
  ...
evidence:           # source citations (node IDs, hex values, URLs, file:line)
  ...
uncertainty:        # flagged items needing user input
  ...
handoff:            # what the next agent needs to know
  next: <agent-name>
  context: ...
```

Reviewer's report adds:

```yaml
verdict: pass | fail | pass-with-warnings
issues: [...]
fixes_applied: [...]
```

## Hard rules

- Never spawn more agents than the topology requires for the surface size — wasteful.
- Never run analysts sequentially when they're independent — always parallel `Task` dispatch.
- Builder is **always single-instance** (no parallel writes to the same `.pen` or filesystem).
- Reviewer is **always last** and runs inline as the gate; do not spawn a separate `Task` for review unless the surface is so large that the consolidator cannot hold it.
