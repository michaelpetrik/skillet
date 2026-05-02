---
name: repo-notes
description: Record metadata about the current project (purpose, tech stack, milestones, goals, skills, important info) into a personal index repository michaelpetrik/project-notes. Use this when the user just set up a new repo, wants to register the current project in their personal notes index, or asks to "zaznamenat projekt", "uložit info o projektu", "publish project notes".
category: General
version: 1.0.0
---

# Repo Notes

Use this skill to publish a snapshot of the current project into the personal index repo `michaelpetrik/project-notes`. Each project gets its own subdirectory named after the project root's basename (the same as `pwd | xargs basename`), containing a single `NOTES.md` file plus an entry in the top-level `README.md` index.

This is the project-level analogue of `publish-skill-to-skillet`: same publishing model (shallow clone → write → commit → push), but the artifact is project metadata, not a skill bundle.

## When To Use

- The user just finished setting up a new repo and wants it tracked in their personal project index.
- The user says: "zaznamenej tenhle projekt", "uložit do project-notes", "publish project notes", "register this repo in my notes".
- The user asks to refresh the recorded notes for the current project (tech stack changed, new milestone, new goal).

Do NOT use this skill for:

- Editing AGENTS.md or README.md inside the current project (just edit them directly).
- Generating documentation in `docs/` (use `create-docs` instead).
- Cross-project search (the index repo is just a flat collection of NOTES.md files).

## Workflow

1. Resolve the project root. Default is the current working directory; the user can override with an explicit path.

2. Gather metadata from the project root (the script does this automatically — do NOT pre-read these files into your context unless the user wants to review the result):
   - **Purpose** — first non-empty paragraph of `AGENTS.md` (preferred), falling back to `README.md`.
   - **Tech stack** — detected from `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`, `pom.xml`, `build.gradle`, `Dockerfile`, `docker-compose.yml`, plus framework hints (Next.js, FastAPI, Django, etc.).
   - **Skills** — detected from `.claude/skills/`, `.agents/skills/`, and any skill references in `AGENTS.md` / `CLAUDE.md`.
   - **Git remote** — `git remote get-url origin` if available.
   - **Milestones / Goals / Important info** — explicit sections in `AGENTS.md` if present (`## Milestones`, `## Goals`, `## Notes`), otherwise left for the user to fill in.

3. Run the publish script:

```bash
python3 /Users/michal/.agents/skills/repo-notes/scripts/publish_repo_notes.py
```

   With explicit overrides:

```bash
python3 /Users/michal/.agents/skills/repo-notes/scripts/publish_repo_notes.py \
  --project-root /path/to/project \
  --target-name custom-folder-name \
  --remote michaelpetrik/project-notes \
  --branch main
```

4. Always run with `--dry-run` first if the user hasn't explicitly said "push it" — show them the rendered NOTES.md and let them confirm before committing.

5. The script publishes:
   - `<basename>/NOTES.md` — the project snapshot
   - `README.md` — top-level index entry for the project (alphabetical by basename)

6. Publication rules (mirrors `publish-skill-to-skillet`):
   - First publication → write NOTES.md and add a `## Initial entry — <date>` history line.
   - Subsequent publication → diff against the existing NOTES.md; if anything changed, append a `## Updated — <date>` history line listing what changed (purpose, tech stack, skills, etc.). If nothing changed, report `no_changes: true` and skip the commit.
   - Never delete user-authored sections (Milestones, Goals, custom notes added directly in the index repo). The script preserves anything under a `## User notes` heading verbatim.

7. After running, report to the user:
   - target path in the index repo (`<basename>/NOTES.md`)
   - whether this is initial publication or update
   - what changed (added/changed sections)
   - pushed commit SHA (in remote mode, when something was pushed)
   - if `no_changes: true`, tell the user the index already matches.

## Script Flags

- `--project-root <path>` — override the project to record (default: cwd).
- `--target-name <name>` — override the subfolder name (default: basename of project root).
- `--remote <owner/repo>` — override the target repo (default: `michaelpetrik/project-notes`).
- `--remote-url <git-url>` — override the clone URL (e.g. SSH).
- `--branch <branch>` — remote branch (default: `main`).
- `--commit-message <message>` — override the auto-generated commit message.
- `--repo <path>` — publish to a local checkout of the index repo instead of remote mode.
- `--dry-run` — print the rendered NOTES.md and the diff plan without writing or pushing.
- `--keep-temp` — keep the temporary clone in `--remote` mode for inspection.

## Bootstrapping The Index Repo

If the target repo does not exist yet, the script will fail at `git clone`. In that case, create the repo first:

```bash
gh repo create michaelpetrik/project-notes --private --description "Personal index of projects I work on" --add-readme
```

Then re-run the skill.

## Examples

Record the current project into the index, dry-run first:

```bash
python3 /Users/michal/.agents/skills/repo-notes/scripts/publish_repo_notes.py --dry-run
```

Push for real:

```bash
python3 /Users/michal/.agents/skills/repo-notes/scripts/publish_repo_notes.py
```

Record a project from a different path under a custom folder name:

```bash
python3 /Users/michal/.agents/skills/repo-notes/scripts/publish_repo_notes.py \
  --project-root /Users/michal/Development/web/foo \
  --target-name foo-frontend
```

## Notes

- Default mode is remote and does not touch any local checkout of the index repo.
- The script uses a temporary shallow clone, applies the publication logic, creates one commit, pushes, and cleans up the temp directory unless `--keep-temp` is passed.
- The target repo `michaelpetrik/project-notes` is private — the user needs working `gh` / git credentials.
- The `User notes` section in the published `NOTES.md` is preserved across re-publications. Use it for hand-written context that the script cannot infer.
