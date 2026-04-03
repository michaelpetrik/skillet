---
name: publish-skill-to-skillet
description: Publish or sync a local Codex skill bundle into the skillet repository under skills/<category>/<skill-name>, including SKILL.md, bundled resources, CHANGELOG.md, and skills/README.md updates.
category: Misc
version: 1.0.0
---

# Publish Skill To Skillet

Use this skill when the user wants to publish a local skill into the `skillet` repository or refresh an existing published copy.

## Workflow

1. Run:

```bash
python3 /Users/michal/.codex/skills/publish-skill-to-skillet/scripts/publish_skill_to_skillet.py <skill-dir-or-SKILL.md> <category>
```

2. Default target is the remote repository:

```text
michaelpetrik/skillet (branch: main)
```

3. Optional flags:
   - `--repo <path>` to force publishing into a local skillet checkout instead of the default remote mode
   - `--remote <owner/repo>` to override the default remote target
   - `--remote-url <git-url>` to override the clone URL in `--remote` mode, for example an SSH URL
   - `--branch <branch>` to choose the remote branch in `--remote` mode
   - `--commit-message <message>` to override the generated commit message in `--remote` mode
   - `--target-name <name>` to override the published directory name
   - `--dry-run` to inspect the diff without writing files

4. The script publishes the full skill bundle:
   - `SKILL.md`
   - bundled resources such as `scripts/`, `references/`, and `agents/`
   - `CHANGELOG.md`
   - `skills/README.md` entry for the category

5. Publication rules:
   - Normalize published `SKILL.md` metadata to include `category` and `version`
   - If the target skill does not exist, create `CHANGELOG.md` with an initial release entry
   - If the target skill already exists, compare the source bundle to the published bundle and write a new changelog entry only when something actually changed
   - Do not invent changelog content; base it on the detected file diff

6. After running, report:
   - published target path
   - resulting version
   - added, changed, and removed files
   - whether `CHANGELOG.md` and `skills/README.md` changed
   - in `--remote` mode, also the pushed commit SHA when a push actually happened

7. If `no_changes` is `true`, tell the user the published copy already matches the source bundle.

## Examples

Remote mode from any directory:

```bash
python3 /Users/michal/.codex/skills/publish-skill-to-skillet/scripts/publish_skill_to_skillet.py /Users/michal/.codex/skills/codex-langfuse-hook tracing --dry-run
```

Remote mode with actual push to `main`:

```bash
python3 /Users/michal/.codex/skills/publish-skill-to-skillet/scripts/publish_skill_to_skillet.py /Users/michal/.codex/skills/codex-langfuse-hook tracing
```

Explicit local checkout mode:

```bash
python3 /Users/michal/.codex/skills/publish-skill-to-skillet/scripts/publish_skill_to_skillet.py /Users/michal/.codex/skills/codex-langfuse-hook tracing --repo /Users/michal/Projects/skillet
```

## Notes

- Default mode is remote and does not touch any existing local `skillet` checkout.
- It uses a temporary shallow clone, applies the same publication logic, creates one commit, pushes it, and then cleans the temp directory unless `--keep-temp` is used.
- Remote pushes still require working git credentials for the target repository.
