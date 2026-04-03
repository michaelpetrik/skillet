# Analyst Design

## Design Personas That Create Useful Tension

Use personas or frames to create real disagreement pressure, not decorative voice changes. Good persona axes:

- Method: first-principles, empirical, historical analogies, systems view.
- Incentive: operator, regulator, buyer, counterparty, skeptic.
- Risk posture: growth-seeking, conservative, failure-mode focused.
- Time horizon: near-term execution, medium-term adaptation, long-run strategy.
- Evidence standard: strict source discipline, pragmatic synthesis, adversarial challenge.
- Work product: comparison rubric owner, evidence cartographer, red-flag hunter, architecture mapper, scenario stress tester.

Weak personas:

- Different writing styles with the same reasoning mandate.
- Cosmetic labels with no distinct questions.
- Multiple analysts all told to "be comprehensive."
- Analysts differentiated only by domain labels while still consuming the same source set and rubric.

## Prevent Duplication

For each analyst, specify:

- Primary question: the one thing this analyst must answer.
- Secondary questions: supporting angles it may cover.
- Explicit exclusions: what it must leave for others.
- Evidence responsibility: what sources or signals it should prioritize.
- Output length cap: enough to think clearly, not enough to ramble.

Useful anti-duplication patterns:

- Give each analyst one owned table, matrix, or section.
- Assign different source families or stakeholder lenses.
- Require each analyst to state where another analyst is likely to disagree.
- Cap overlap by banning generic restatement of the task.
- For investigations, assign timeline ownership, claim-verification ownership, or counter-hypothesis ownership.
- For codebase work, assign concrete repo surfaces such as architecture, runtime path, data model, or change-risk.

## Write Scopes

- Analyst scope: only their own artifact. No cross-editing, no reconciliation.
- Consolidator scope: only the merged artifact and conflict map.
- Reviewer scope: critique plus patch or revision notes. Do not restart the whole analysis unless the synthesis is structurally broken.
- Validator scope: checks, edge cases, and pass/fail conditions. Do not let validation become a second reviewer unless necessary.

This separation keeps accountability clear and reduces drift.

## Deliverable Contracts

Use a lightweight contract for analyst outputs:

```text
Title
Bottom line
Evidence
Evidence quality or freshness notes
Assumptions
Counter-signals or failure modes
Questions for consolidation
```

Use a lightweight contract for the consolidator:

```text
Final answer or artifact
Why this synthesis wins
Where analysts disagreed
Residual uncertainty
What would change the conclusion
```

Adjust the consolidator contract to the task:

- Comparative research: include criteria table, weighting assumptions, and condition-specific winners.
- Due diligence: include red flags, unknowns, required follow-up, and decision gates.
- Literature scan: include consensus, contested claims, evidence tiers, and gap list.
- Structured brainstorming: include clustered options, novelty-preserving merges, and feasibility or impact filters only if requested.
- Codebase analysis: include system model, key interfaces or flows, and likely change impact.
- Risk assessment: include prioritized register, triggers, mitigations, and residual exposure.

Use a lightweight contract for the reviewer:

```text
What is overstated or under-supported
What frame is missing
Required corrections
Revised conclusion or approval conditions
```

Reviewer emphasis by task:

- Brainstorming: check novelty collapse, duplicate clustering mistakes, and over-pruning.
- Comparative research: check unfair criteria, hidden weighting, and apples-to-oranges comparisons.
- Due diligence: check missing downside workstreams and false comfort from absent evidence.
- Literature scan: check citation drift, consensus inflation, and unsupported generalization across studies.
- Codebase analysis: check speculation versus direct evidence and whether the output ignored available repo tooling.

Use a lightweight contract for the validator:

```text
What was checked
What broke or held
Confidence and limits
```

## Prompting Guidance

Common packet for all analysts:

- Task and desired final artifact.
- Scope boundaries.
- Evidence bar.
- Deadline or effort budget.
- Required output contract.

Per-analyst additions:

- Distinct frame.
- Explicit non-goals.
- One question they uniquely own.
- Required evidence family or repo surface they must inspect first.

Consolidator prompt:

- Provide the original task framing and analyst outputs.
- Ask for one coherent artifact, not a committee transcript.
- Require disagreements, assumptions, and uncertainty to remain visible.
- Tell it whether the task should converge to one answer, preserve multiple options, or do both.

Reviewer prompt:

- Provide the consolidated artifact and analyst outputs.
- Ask for the strongest critique first.
- Allow direct correction, but require the reviewer to explain why the change is necessary.
- Ask explicitly whether the workflow over-structured the task, over-converged, or created false independence.

Validator prompt:

- Provide the final artifact and only the materials needed to test it.
- Ask for breakpoints, edge cases, or claim-verification results.
- Avoid telling the validator what outcome you expect.
- For codebase or technical work, prefer reproducible checks over opinionated review.
