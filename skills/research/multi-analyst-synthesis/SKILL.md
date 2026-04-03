---
name: multi-analyst-synthesis
description: Parallel multi-pass analysis for comparative research, due diligence, literature scans, decision memo prep, structured brainstorming, multi-source synthesis, product or market research, risk assessment, investigative work, codebase analysis, and other knowledge-work where distinct analytic perspectives should work in parallel before one consolidator and one critical reviewer shape the final deliverable. Use when the task is ambiguous, high-stakes, evidence-rich, or benefits from competing frames; avoid for simple fact lookups, deterministic transforms, routine drafting, narrow tasks with one obvious authoritative path, or cases where direct tools answer the question better than orchestration.
category: Research
version: 1.0.0
---

# Multi-Analyst Synthesis

Use this pattern when one agent would likely anchor too early, flatten disagreement, or miss important frames. Default topology: `3 analysts -> 1 xhigh consolidator -> 1 critical reviewer -> optional validation pass`.

## Workflow

1. Decide whether the pattern is justified. If the task is small, deterministic, or single-path, do not use it.
2. Define the final deliverable before launching analysts: target output, decision question, constraints, evidence bar, freshness needs, and deadline.
3. Run parallel analysts with intentionally different scopes. Keep overlap low and ask for uncertainties, not polished prose.
4. Hand analyst outputs to one consolidator. Have it produce the right merged deliverable for the task: recommendation, comparison matrix, evidence map, ranked option set, architecture readout, risk register, or investigation memo, plus a conflict map and open-risk list.
5. Hand the consolidated artifact to one critical reviewer. Have it find overreach, bias, weak generalization, and missing disconfirming evidence, then revise or annotate.
6. Add a light validation pass only when the result can be pressure-tested without collapsing independence.

## Operating Rules

- Use `3` analysts by default. Use `2` when the task is a constrained comparison or a quick diligence pass. Increase only when you can define another genuinely distinct frame.
- Give each analyst the same core task packet plus a unique mandate and explicit exclusions.
- Match the output shape to the task. Do not force every run into a single recommendation memo.
- Keep write scopes separate: analysts do not edit each other, the consolidator owns the merged artifact, the reviewer owns critique and corrections, the validator only checks.
- Prefer primary or directly inspectable evidence when the task allows it. Make source hierarchy and recency explicit for market, diligence, scientific, legal, or rapidly changing topics.
- For codebase or technical investigation, use direct repo evidence, code search, tests, traces, or graph tools first; use multi-analyst orchestration only when multiple interpretations or decision frames are genuinely in play.
- Prefer evidence, assumptions, and disagreements over style or verbosity.
- Persist intermediate outputs only when they are useful for auditability, reproducibility, or later reuse.
- Abort the pattern if analysts are producing cosmetic restatements, false consensus, or coordination overhead with no new signal.

## Common Fits

- Comparative research: analysts split by rubric, stakeholder lens, or scenario; consolidator outputs a normalized comparison and recommendation conditions.
- Due diligence: analysts split by commercial, operational, financial, legal, technical, or failure-mode lenses; final output is a red-flag register with unknowns and decision gates.
- Structured brainstorming: analysts generate options from distinct constraints or worldviews; consolidator clusters and ranks instead of collapsing novelty too early.
- Literature scan: analysts split by theme, methodology, evidence quality, or contradictory schools of thought; final output is an evidence map, gaps, and confidence tiers.
- Decision memo prep: analysts surface option value, execution cost, risk, and reversibility; consolidator produces a memo, reviewer checks whether the memo actually supports the decision.
- Multi-source synthesis and investigation: analysts split by source family, timeline, and adversarial interpretation; final output keeps provenance and contradictions visible.
- Codebase analysis: analysts split by architecture, runtime path, data flow, and change risk only when the question is interpretive or decision-oriented rather than a direct lookup.
- Product or market research: analysts separate user demand, competitors, economics, go-to-market, and execution risk, with explicit freshness requirements.
- Risk assessment: analysts cover base case, failure modes, adversarial behavior, and mitigation levers; final output is a prioritized risk register with triggers.

## Common Misfits

- Simple factual lookups, one-document summaries, or routine drafting.
- Tasks with one authoritative method or direct tool path, such as a single grepable code answer, a straightforward spreadsheet transform, or policy extraction from one short source.
- Work where coordination cost would exceed analytic value.
- Cases where you cannot produce genuinely distinct analyst mandates.
- Brainstorming sessions that only need rapid idea volume and lightweight pruning rather than evidence-backed synthesis.

## References

- Read [references/orchestration.md](references/orchestration.md) for task fit, analyst-count rules, workflow, validation integrity, and storage conventions.
- Read [references/analyst-design.md](references/analyst-design.md) for persona design, anti-duplication tactics, write scopes, and deliverable contracts.
