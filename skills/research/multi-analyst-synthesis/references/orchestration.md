# Orchestration

## Use This Pattern When

- The task benefits from materially different frames, not just extra effort.
- The evidence is mixed, incomplete, high-volume, or likely to induce anchoring.
- The output matters enough that a second-order critique is worth the overhead.
- You need a high-quality deliverable rather than a pile of notes: recommendation, comparison matrix, evidence map, diligence memo, risk register, architecture readout, investigation brief, or structured option set.

## Do Not Use This Pattern When

- A single authoritative source or deterministic procedure can answer the question.
- The task is routine drafting, formatting, summarization of one short source, or a narrow lookup.
- Time or token budget is so tight that coordination would crowd out actual analysis.
- You cannot define distinct analyst scopes without large overlap.
- Validation would be fake because the validator would only restate the same reasoning.
- The task is primarily divergent ideation and does not need evidence-backed convergence yet.
- Direct inspection tools answer faster and better than orchestration, such as code search, a queryable data table, a benchmark harness, or a single source of truth.
- The available evidence is so thin that multiple analysts would only hallucinate independence.

## Choose Analyst Count

- `2 analysts`: Use for constrained compare/contrast or moderate ambiguity with two clear frames.
- `3 analysts`: Default. Use for most research, synthesis, diligence, and policy extraction tasks.
- `4 analysts`: Use for high-stakes work with one additional orthogonal frame such as legal, market, operational, or failure-mode analysis.
- `5+ analysts`: Rare. Use only when the task naturally decomposes into non-overlapping slices and you can afford a heavier consolidation step.

Increase analyst count only if one of these is true:

- Another frame would likely change the recommendation.
- Another evidence family needs dedicated ownership.
- Another stakeholder or regime meaningfully changes interpretation.

If none apply, keep the team smaller.

## Run The Workflow

### 1. Frame The Task

Define these before dispatch:

- Final artifact type: memo, recommendation, matrix, extracted policy, option set, risk register, evidence map, architecture readout, investigation brief, brainstorm set.
- Success criteria: what a good output must enable.
- Constraints: time horizon, jurisdiction, audience, scope boundaries, source rules.
- Evidence standard: what counts as support and how uncertainty should be stated.
- Freshness and provenance rules: how current the evidence must be, which sources outrank others, and what must be directly verified.

Before you launch analysts, decide whether the task needs convergence, divergence, or both:

- Convergent tasks: decision memo prep, due diligence, risk assessment, product recommendation, codebase change analysis. Expect one final position plus explicit caveats.
- Divergent-then-curated tasks: structured brainstorming, literature scanning, exploratory market mapping. Preserve multiple viable options or schools of thought before ranking or pruning.
- Mixed tasks: comparative research or investigations often need both a normalized comparison and a final recommendation.

### 2. Partition The Work

Pick one partitioning logic and stay consistent:

- Lens-based: strategy, operations, legal, economics, risk.
- Source-based: primary sources, secondary synthesis, expert commentary, market data.
- Stakeholder-based: buyer, regulator, operator, counterparty.
- Scenario-based: base case, upside, downside, adversarial case.
- Time-based: immediate, medium-term, long-term implications.

Avoid mixed partitions unless the task truly needs them. If you do mix them, write down ownership explicitly so analysts do not collapse into generic overlap.

Good task-to-partition examples:

- Comparative research: rubric-based or stakeholder-based partitions.
- Due diligence: workstream partitions such as commercial, legal, technical, operational.
- Literature scan: methodology, theme, or evidence-quality partitions.
- Codebase analysis: subsystem, runtime path, data flow, and change-risk partitions.
- Product or market research: user need, competitor dynamics, economics, channel, operational feasibility.
- Risk assessment: scenario-based plus mitigation ownership.

### 3. Run Analysts In Parallel

Give every analyst:

- The same task packet.
- A unique mandate.
- Explicit non-goals to reduce duplication.
- A required output contract.

Require analysts to report:

- Main claim or proposed answer.
- Key evidence.
- Assumptions.
- Uncertainties and disconfirming facts.
- What the consolidator must reconcile.
- Any source-quality or freshness caveats that materially weaken the finding.

### 4. Consolidate Once

Use one high-capability consolidator. Give it analyst outputs and the original task framing. Ask it to:

- Merge overlapping findings.
- Resolve or surface disagreements.
- Produce the right final artifact for the task, not always one recommendation memo.
- Preserve an uncertainty and risk section.
- State what evidence is strong versus provisional.

Do not ask the consolidator to emulate all analysts again. Its job is merger and decision hygiene.

Artifact-specific consolidation guidance:

- Comparative research: normalize criteria, expose weighting assumptions, and separate "best overall" from "best under condition X."
- Due diligence: emphasize red flags, unknowns, dependency risks, and explicit go or no-go gates.
- Structured brainstorming: cluster ideas, remove duplicates, keep distinctive options visible, and score or filter only if the task asked for it.
- Literature scan: separate consensus from contested findings, tag evidence quality, and keep research gaps visible.
- Codebase analysis: produce a system model, key call paths, constraints, and likely change impact rather than speculative prose.
- Product or market research: distinguish user signal, competitor signal, economic signal, and execution risk; flag stale evidence.
- Risk assessment: prioritize by severity, likelihood, detectability, and mitigation leverage.

### 5. Review Critically

Use one critical reviewer with permission to challenge the whole structure. Ask it to inspect:

- Overreach or false precision.
- Framing bias and missing counter-frames.
- Weak generalization from thin evidence.
- Hidden assumptions, omitted tradeoffs, or one-sided comparisons.
- Whether the final artifact actually answers the original task.
- Whether the output shape fits the task, or whether the workflow forced premature convergence.

Let the reviewer either:

- Patch the consolidated artifact directly, or
- Attach a concise correction memo plus required edits.

For brainstorming or exploratory scans, the reviewer should test for novelty loss, premature ranking, and missing option categories rather than flattening everything into one conservative answer.

### 6. Validate Lightly

Add validation only when it can falsify or stress-test something real. Good validation targets:

- Compare extracted policies against source text.
- Check whether decision criteria match the stated recommendation.
- Run edge cases or counterexamples against the final framework.
- Verify claim coverage against cited evidence.
- Check whether a brainstorm survives simple feasibility filters.
- Re-check market or investigative claims against fresher primary sources.
- Reproduce a codebase claim with direct repo evidence, tests, traces, or graph queries.
- Check whether a literature summary preserves the actual disagreement structure of the cited work.

Skip validation when it would only produce ceremonial agreement.

## Protect Validation Integrity

- Do not tell the validator what you think is wrong.
- Pass the artifact and the minimum source material needed to test it.
- Keep validation prompts task-shaped, not diagnosis-shaped.
- Use a different frame from the reviewer when possible.
- Ask for pass/fail conditions, edge cases, or breaks in reasoning, not a rewrite unless the validator finds a concrete issue.

## Common Failure Modes

- Decorative plurality: analysts use different labels but perform the same reasoning.
- Premature convergence: the consolidator collapses a compare, brainstorm, or literature scan into one answer too early.
- False objectivity: a weighted matrix or memo implies precision unsupported by evidence quality.
- Correlated evidence: all analysts depend on the same secondary summaries and only appear independent.
- Process drag: too many analysts or too much storage and ceremony for the value at stake.
- Tool avoidance: orchestration is used where direct code, data, or source inspection should have been the primary method.

## Store Outputs

Store only what helps the task. Default pattern:

```text
work/
  analysts/
    01-<frame>.md
    02-<frame>.md
    03-<frame>.md
  synthesis/
    consolidated.md
  review/
    critique.md
  validation/
    check.md
  final/
    deliverable.md
```

Storage rules:

- Keep analyst files immutable after handoff.
- Keep the consolidated artifact separate from the final deliverable if review or validation may change it.
- Preserve a short risk or uncertainty register when auditability matters.
- If the user does not need persistent intermediates, summarize them and keep only the final deliverable plus one review note.
