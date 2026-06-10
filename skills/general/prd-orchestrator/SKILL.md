---
name: prd-orchestrator
description: Orchestrate a gated PRD workflow across discovery-process, grill-me, and prd. Use when the user wants an end-to-end product planning flow from a raw idea or scattered notes to a pressure-tested final PRD with working docs under projects/<slug>/. If one of the required skills is missing, detect it and install it with `npx skills` before continuing.
category: General
version: 1.0.0
---

# PRD Orchestrator

## Overview

Run one strict pipeline:
`discovery-process` -> `grill-me` -> `prd`.

Use this when the user wants the three skills to work together cleanly instead of
competing or reopening each other's decisions.

## Workflow Contract

- Fixed order:
  `discovery-process` first,
  `grill-me` second,
  `prd` last.
- `grill-me` never starts from a blank idea.
- `prd` never starts from raw notes while critical decisions are still open.
- Locked decisions stay locked unless a contradiction appears.
- If evidence already exists in repo files, inspect files before asking the user.

## Output Contract

- Derive a short slug from the initiative name.
- Work in `projects/<slug>/`.
- Create or update these files:
  - `discovery-summary.md`
  - `decision-log.md`
  - `prd.md`
- Start from these templates:
  - `assets/discovery-summary-template.md`
  - `assets/decision-log-template.md`
- Resume in place if files already exist.
  Do not overwrite confirmed facts.

## Phase 0: Preflight

- Verify the three dependency skills exist before using the pipeline:
  `discovery-process`,
  `grill-me`,
  `prd`.
- Check both project and global skill scope:
  - `npx -y skills ls --json`
  - `npx -y skills ls -g --json`
- If all three are present, continue.
- If any are missing, install the missing ones before continuing.
- Establish the initiative name and target slug.
- Gather source material:
  user prompt,
  repo docs,
  notes,
  links,
  existing project files.
- Inspect existing `projects/<slug>/` files first.
- Reuse confirmed facts.
  Do not ask for information that is already documented.
- If the repo already has planning notes elsewhere, mirror only stable facts into the
  three working docs.

### Missing Skill Recovery

- Missing `discovery-process`:
  `npx -y skills add https://github.com/deanpeters/product-manager-skills -g -a codex -s discovery-process -y`
- Missing `grill-me`:
  `npx -y skills add https://github.com/alirezarezvani/claude-skills -g -a codex -s grill-me -y`
- Missing `prd`:
  `npx -y skills add https://github.com/github/awesome-copilot -g -a codex -s prd -y`
- After installation, run the list commands again and verify the skill now exists.
- If installation fails, stop and report which skill is still missing and why.
- If the current runtime does not auto-load newly installed skills in the same turn, read the
  installed `SKILL.md` files directly from `~/.agents/skills/<skill-name>/SKILL.md` and
  continue using those instructions.
- Do not skip this recovery step.
  The pipeline depends on all three skills being available.

## Phase 1: Discovery Gate

Use `discovery-process` to understand the problem before any pressure test or PRD draft.

### Required outputs

- Fill `discovery-summary.md`.
- Capture at least:
  - problem statement
  - target users or personas
  - current behavior or workflow
  - evidence
  - assumptions and hypotheses
  - success metrics
  - constraints
  - non-goals or out-of-scope
  - open questions

### Gate to continue

Do not move to `grill-me` until these are explicit:
- primary problem
- primary user
- measurable success signal
- draft v1 scope hypothesis
- hard constraints, if any
- explicit open questions list

If one of these is missing, stay in discovery.

## Phase 2: Decision Closure Gate

Use `grill-me` only on the unresolved or conflicting parts of the discovery summary.

### How to run it

- Walk open questions depth-first.
- Ask one question per turn.
- Provide a recommended answer with each question.
- If the answer is in files or notes, inspect first and confirm with evidence.
- After each resolved branch, update `decision-log.md`.

### What goes into `decision-log.md`

- locked decisions
- rejected options
- remaining TBDs
- decision rationale
- dependencies
- major risks or watchouts

### Gate to continue

Do not move to `prd` while any critical TBD remains in:
- problem definition
- target user
- success metrics
- v1 scope
- core workflow
- hard constraint that changes architecture or delivery

Low-risk implementation detail TBDs may remain, but they must be marked explicitly.

## Phase 3: PRD Draft Gate

Use `prd` after discovery and decision closure are strong enough.

### Inputs for `prd`

- `discovery-summary.md` is the problem source of truth.
- `decision-log.md` is the decision source of truth.
- Existing repo constraints remain valid unless contradicted.

### Drafting rules

- Follow the `prd` skill schema.
- Ask new questions only if they are required to complete the schema or resolve a
  contradiction.
- Do not reopen locked decisions without naming the contradiction.
- If something remains unknown, mark it `TBD`.
  Do not invent it.
- Keep non-goals explicit.

## Final QA

Before finishing, verify:
- the three docs agree on users, scope, and metrics
- each success metric is measurable
- each critical decision in the PRD has a matching entry in `decision-log.md`
- no critical TBD remains hidden in prose
- rejected options and non-goals are visible enough to stop scope creep

## Resume Rules

- If only `discovery-summary.md` exists, continue Phase 1 or 2.
- If `decision-log.md` exists with critical TBDs, resume Phase 2.
- If `prd.md` exists without the two working docs, backfill them before major revision.
- On later revisions, update the three docs in order:
  discovery facts,
  decision log,
  PRD.

## Templates

- Use `assets/discovery-summary-template.md` for discovery handoff.
- Use `assets/decision-log-template.md` for decision closure handoff.
- Copy the template structure, then replace placeholders with real content.
