#!/usr/bin/env python3
"""Publish a snapshot of the current project into michaelpetrik/project-notes.

Mirrors the publishing model of publish_skill_to_skillet.py: shallow clone,
write artifacts, commit, push, clean up. The artifact is a single NOTES.md
file describing the project (purpose, tech stack, skills, milestones,
goals, important info) plus an entry in the top-level README.md index.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path


DEFAULT_REMOTE_SLUG = "michaelpetrik/project-notes"
NOTES_FILE = "NOTES.md"
INDEX_README = "README.md"
USER_NOTES_HEADING = "## User notes"
HISTORY_HEADING = "## History"


# ---------- argument parsing ---------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a project snapshot into michaelpetrik/project-notes."
    )
    parser.add_argument("--project-root", help="Path to the project to record. Defaults to cwd.")
    parser.add_argument("--target-name", help="Subdirectory name in the index repo. Defaults to project basename.")
    parser.add_argument("--remote", default=DEFAULT_REMOTE_SLUG, help="Target repo slug.")
    parser.add_argument("--remote-url", help="Optional clone URL override (e.g. SSH).")
    parser.add_argument("--branch", default="main", help="Remote branch.")
    parser.add_argument("--commit-message", help="Override auto-generated commit message.")
    parser.add_argument("--repo", help="Path to a local checkout of the index repo. Bypasses remote mode.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without writing or pushing.")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary clone for inspection.")
    return parser.parse_args()


# ---------- project metadata gathering ----------------------------------------


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def first_paragraph(text: str) -> str:
    lines = text.splitlines()
    buf: list[str] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            if started:
                break
            continue
        if not stripped:
            if started:
                break
            continue
        started = True
        buf.append(stripped)
    return " ".join(buf).strip()


def extract_section(text: str, heading_pattern: str) -> str:
    pattern = re.compile(
        rf"(?ms)^##\s+{heading_pattern}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(text)
    if not match:
        return ""
    return match.group("body").strip()


def detect_purpose(project_root: Path) -> tuple[str, str | None]:
    for filename in ("AGENTS.md", "CLAUDE.md", "README.md"):
        candidate = project_root / filename
        if candidate.exists():
            text = read_text_safe(candidate)
            paragraph = first_paragraph(text)
            if paragraph:
                return paragraph, filename
    return "", None


def detect_tech_stack(project_root: Path) -> list[str]:
    stack: list[str] = []

    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        stack.append("Node.js / npm")
        framework_hints = {
            "next": "Next.js",
            "react": "React",
            "vue": "Vue",
            "svelte": "Svelte",
            "@angular/core": "Angular",
            "express": "Express",
            "fastify": "Fastify",
            "vite": "Vite",
            "astro": "Astro",
            "remix": "Remix",
            "nuxt": "Nuxt",
        }
        for key, label in framework_hints.items():
            if key in deps:
                stack.append(label)
        if "typescript" in deps:
            stack.append("TypeScript")

    pyproject = project_root / "pyproject.toml"
    requirements = project_root / "requirements.txt"
    if pyproject.exists() or requirements.exists():
        stack.append("Python")
        text = ""
        if pyproject.exists():
            text += read_text_safe(pyproject)
        if requirements.exists():
            text += "\n" + read_text_safe(requirements)
        text_lower = text.lower()
        framework_hints = {
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "pydantic": "Pydantic",
            "sqlalchemy": "SQLAlchemy",
            "anthropic": "Anthropic SDK",
            "openai": "OpenAI SDK",
            "langchain": "LangChain",
        }
        for key, label in framework_hints.items():
            if key in text_lower:
                stack.append(label)

    if (project_root / "Cargo.toml").exists():
        stack.append("Rust / Cargo")
    if (project_root / "go.mod").exists():
        stack.append("Go")
    if (project_root / "Gemfile").exists():
        stack.append("Ruby")
    if (project_root / "composer.json").exists():
        stack.append("PHP / Composer")
    if (project_root / "pom.xml").exists():
        stack.append("Java / Maven")
    if (project_root / "build.gradle").exists() or (project_root / "build.gradle.kts").exists():
        stack.append("Gradle")
    if any((project_root / name).exists() for name in ("Dockerfile", "docker-compose.yml", "compose.yml")):
        stack.append("Docker")
    if (project_root / "Package.swift").exists() or list(project_root.glob("*.xcodeproj")):
        stack.append("Swift / Xcode")
    if list(project_root.glob("*.xcworkspace")):
        stack.append("Xcode workspace")

    seen = set()
    deduped = []
    for item in stack:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def detect_skills(project_root: Path) -> list[str]:
    skills: set[str] = set()
    for skills_dir in (project_root / ".claude" / "skills", project_root / ".agents" / "skills"):
        if skills_dir.is_dir():
            for entry in skills_dir.iterdir():
                if entry.is_dir() or entry.is_symlink():
                    skills.add(entry.name)
    return sorted(skills)


def detect_git_remote(project_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    url = result.stdout.strip()
    return url or None


def detect_default_branch(project_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    branch = result.stdout.strip()
    return branch or None


# ---------- NOTES.md rendering -------------------------------------------------


def render_notes(
    target_name: str,
    project_root: Path,
    purpose: str,
    purpose_source: str | None,
    tech_stack: list[str],
    skills: list[str],
    git_remote: str | None,
    git_branch: str | None,
    milestones: str,
    goals: str,
    important: str,
    user_notes: str,
    history: str,
) -> str:
    today = date.today().isoformat()
    lines: list[str] = []
    lines.append(f"# {target_name}")
    lines.append("")
    lines.append(f"_Last updated: {today}_")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    if purpose:
        lines.append(purpose)
        if purpose_source:
            lines.append("")
            lines.append(f"_(extracted from `{purpose_source}`)_")
    else:
        lines.append("_No purpose detected — add an AGENTS.md or README.md to the project, or fill in the User notes section below._")
    lines.append("")

    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **Local path:** `{project_root}`")
    if git_remote:
        lines.append(f"- **Git remote:** `{git_remote}`")
    if git_branch:
        lines.append(f"- **Branch:** `{git_branch}`")
    lines.append("")

    lines.append("## Tech stack")
    lines.append("")
    if tech_stack:
        for item in tech_stack:
            lines.append(f"- {item}")
    else:
        lines.append("_No tech stack detected._")
    lines.append("")

    lines.append("## Skills")
    lines.append("")
    if skills:
        for item in skills:
            lines.append(f"- `{item}`")
    else:
        lines.append("_No project-local skills detected._")
    lines.append("")

    lines.append("## Milestones")
    lines.append("")
    lines.append(milestones if milestones else "_None recorded._")
    lines.append("")

    lines.append("## Goals")
    lines.append("")
    lines.append(goals if goals else "_None recorded._")
    lines.append("")

    lines.append("## Important info")
    lines.append("")
    lines.append(important if important else "_None recorded._")
    lines.append("")

    lines.append(USER_NOTES_HEADING)
    lines.append("")
    lines.append(user_notes if user_notes else "_(Hand-written notes — preserved across re-publications.)_")
    lines.append("")

    lines.append(HISTORY_HEADING)
    lines.append("")
    lines.append(history if history else f"- {today} — initial entry")
    lines.append("")

    return "\n".join(lines)


def split_managed_and_user(existing_text: str) -> tuple[str, str]:
    """Return (user_notes_body, history_body) extracted from a previously published NOTES.md."""
    user_notes = ""
    history = ""
    if not existing_text:
        return user_notes, history

    user_match = re.search(
        rf"(?ms)^{re.escape(USER_NOTES_HEADING)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        existing_text,
    )
    if user_match:
        user_notes = user_match.group("body").strip()
        if user_notes.startswith("_(") and user_notes.endswith(")_"):
            user_notes = ""

    history_match = re.search(
        rf"(?ms)^{re.escape(HISTORY_HEADING)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        existing_text,
    )
    if history_match:
        history = history_match.group("body").strip()

    return user_notes, history


# ---------- diff for history line ---------------------------------------------


def changed_sections(old: str, new: str) -> list[str]:
    section_names = ["Purpose", "Metadata", "Tech stack", "Skills", "Milestones", "Goals", "Important info"]
    changed: list[str] = []
    for name in section_names:
        if extract_section(old, re.escape(name)) != extract_section(new, re.escape(name)):
            changed.append(name)
    return changed


def append_history_line(existing_history: str, today: str, sections: list[str]) -> str:
    if not sections:
        suffix = "no detected changes"
    else:
        suffix = "updated " + ", ".join(s.lower() for s in sections)
    new_line = f"- {today} — {suffix}"
    if not existing_history:
        return new_line
    return new_line + "\n" + existing_history


# ---------- README index ------------------------------------------------------


def build_index_entry(target_name: str, purpose: str) -> str:
    summary = purpose or "_no purpose recorded_"
    summary = summary.replace("\n", " ").strip()
    if len(summary) > 200:
        summary = summary[:197].rstrip() + "..."
    return f"- **[{target_name}](./{target_name}/{NOTES_FILE})** — {summary}\n"


def update_index_readme(readme_path: Path, target_name: str, purpose: str) -> tuple[str, bool]:
    intro = (
        "# Project Notes\n\n"
        "Personal index of projects I work on. Each subdirectory is a project snapshot "
        f"(`{NOTES_FILE}`) describing purpose, tech stack, milestones, goals, and important info.\n\n"
        "## Projects\n\n"
    )
    current = readme_path.read_text(encoding="utf-8") if readme_path.exists() else intro
    if "## Projects" not in current:
        current = current.rstrip() + "\n\n## Projects\n\n"

    entry = build_index_entry(target_name, purpose)

    line_pattern = re.compile(
        rf"(?m)^- \*\*\[[^\]]+\]\(\./{re.escape(target_name)}/{re.escape(NOTES_FILE)}\)\*\*.*?\n"
    )
    if line_pattern.search(current):
        updated = line_pattern.sub(entry, current, count=1)
    else:
        section_pattern = re.compile(r"(?ms)^## Projects\s*$\n(?P<body>.*?)\Z")
        match = section_pattern.search(current)
        if match:
            body = match.group("body")
            lines = [line for line in body.splitlines() if line.strip()]
            lines.append(entry.rstrip())
            lines = sorted(set(lines), key=lambda line: line.lower())
            new_body = "\n".join(lines) + "\n"
            updated = current[: match.start("body")] + new_body
        else:
            updated = current.rstrip() + "\n\n" + entry

    if not updated.endswith("\n"):
        updated += "\n"
    return updated, updated != current


# ---------- git plumbing -------------------------------------------------------


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    command = ["git", *args]
    try:
        return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"git command failed: {' '.join(command)}\n"
            f"cwd: {cwd}\n"
            f"stdout:\n{exc.stdout}\n"
            f"stderr:\n{exc.stderr}"
        ) from exc


def prepare_remote_checkout(remote_slug: str, remote_url: str | None, branch: str) -> tuple[Path, Path]:
    temp_parent = Path(tempfile.mkdtemp(prefix="publish-repo-notes-"))
    repo_root = temp_parent / "repo"
    clone_url = remote_url or f"https://github.com/{remote_slug}.git"
    run_git(["clone", "--depth", "1", "--branch", branch, clone_url, str(repo_root)], cwd=temp_parent)
    return repo_root, temp_parent


def commit_and_push(
    repo_root: Path,
    branch: str,
    commit_message: str,
    paths: list[str],
) -> dict[str, object]:
    run_git(["add", "--", *paths], cwd=repo_root)
    status = run_git(["status", "--short", "--", *paths], cwd=repo_root).stdout.strip()
    if not status:
        return {"pushed": False, "commit_message": commit_message, "commit_sha": None, "git_status": ""}
    run_git(["commit", "-m", commit_message], cwd=repo_root)
    commit_sha = run_git(["rev-parse", "HEAD"], cwd=repo_root).stdout.strip()
    run_git(["push", "origin", branch], cwd=repo_root)
    return {"pushed": True, "commit_message": commit_message, "commit_sha": commit_sha, "git_status": status}


# ---------- main publication flow ---------------------------------------------


def publish_into_repo(
    repo_root: Path,
    project_root: Path,
    target_name: str,
    dry_run: bool,
) -> dict[str, object]:
    if not repo_root.exists():
        raise SystemExit(f"Index repo does not exist: {repo_root}")

    target_dir = repo_root / target_name
    target_notes_path = target_dir / NOTES_FILE
    readme_path = repo_root / INDEX_README
    target_previously_existed = target_notes_path.exists()

    purpose, purpose_source = detect_purpose(project_root)
    tech_stack = detect_tech_stack(project_root)
    skills = detect_skills(project_root)
    git_remote = detect_git_remote(project_root)
    git_branch = detect_default_branch(project_root)

    agents_text = read_text_safe(project_root / "AGENTS.md")
    milestones = extract_section(agents_text, r"Milestones?")
    goals = extract_section(agents_text, r"Goals?")
    important = extract_section(agents_text, r"(Notes|Important|Important info)")

    existing_text = target_notes_path.read_text(encoding="utf-8") if target_previously_existed else ""
    user_notes, existing_history = split_managed_and_user(existing_text)

    today = date.today().isoformat()

    preview_history = existing_history if target_previously_existed else f"- {today} — initial entry"

    new_notes = render_notes(
        target_name=target_name,
        project_root=project_root,
        purpose=purpose,
        purpose_source=purpose_source,
        tech_stack=tech_stack,
        skills=skills,
        git_remote=git_remote,
        git_branch=git_branch,
        milestones=milestones,
        goals=goals,
        important=important,
        user_notes=user_notes,
        history=preview_history,
    )

    if target_previously_existed:
        sections = changed_sections(existing_text, new_notes)
        if sections:
            new_history = append_history_line(existing_history, today, sections)
            new_notes = render_notes(
                target_name=target_name,
                project_root=project_root,
                purpose=purpose,
                purpose_source=purpose_source,
                tech_stack=tech_stack,
                skills=skills,
                git_remote=git_remote,
                git_branch=git_branch,
                milestones=milestones,
                goals=goals,
                important=important,
                user_notes=user_notes,
                history=new_history,
            )
        notes_changed = sections != [] or new_notes != existing_text
    else:
        sections = []
        notes_changed = True

    readme_content, readme_updated = update_index_readme(readme_path, target_name, purpose)

    files_written: list[str] = []
    if notes_changed:
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_notes_path.write_text(new_notes, encoding="utf-8")
        files_written.append(f"{target_name}/{NOTES_FILE}")
    if readme_updated:
        if not dry_run:
            readme_path.write_text(readme_content, encoding="utf-8")
        files_written.append(INDEX_README)

    no_changes = not (notes_changed or readme_updated)

    return {
        "project_root": str(project_root),
        "target_name": target_name,
        "target_relative_path": f"{target_name}/{NOTES_FILE}",
        "target_previously_existed": target_previously_existed,
        "purpose_detected": bool(purpose),
        "purpose_source": purpose_source,
        "tech_stack": tech_stack,
        "skills": skills,
        "git_remote": git_remote,
        "git_branch": git_branch,
        "changed_sections": sections,
        "files_written": files_written,
        "readme_updated": readme_updated,
        "no_changes": no_changes,
        "dry_run": dry_run,
        "rendered_notes": new_notes if dry_run else None,
    }


def build_commit_message(result: dict[str, object], explicit: str | None) -> str:
    if explicit:
        return explicit
    target_name = result["target_name"]
    verb = "Update" if result["target_previously_existed"] else "Add"
    return f"{verb} project notes for {target_name}"


def main() -> None:
    args = parse_args()

    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else Path.cwd().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"Project root is not a directory: {project_root}")

    target_name = args.target_name or project_root.name
    if not target_name:
        raise SystemExit("Could not derive target name from project root.")

    if args.repo and (args.remote_url or args.remote != DEFAULT_REMOTE_SLUG):
        # `--repo` overrides remote mode entirely; warn-via-error for clarity.
        if args.remote_url:
            raise SystemExit("--remote-url cannot be combined with --repo.")

    temp_parent: Path | None = None
    if args.repo:
        repo_root = Path(args.repo).expanduser().resolve()
        mode = "local"
    else:
        repo_root, temp_parent = prepare_remote_checkout(
            remote_slug=args.remote,
            remote_url=args.remote_url,
            branch=args.branch,
        )
        mode = "remote"

    try:
        result = publish_into_repo(
            repo_root=repo_root,
            project_root=project_root,
            target_name=target_name,
            dry_run=args.dry_run,
        )
        result["mode"] = mode
        result["repo_root"] = str(repo_root)

        if mode == "remote":
            result["remote"] = args.remote
            result["remote_branch"] = args.branch
            result["remote_url"] = args.remote_url or f"https://github.com/{args.remote}.git"

            if not args.dry_run and not result["no_changes"]:
                push_paths = [
                    f"{target_name}/{NOTES_FILE}",
                    INDEX_README,
                ]
                push_result = commit_and_push(
                    repo_root=repo_root,
                    branch=args.branch,
                    commit_message=build_commit_message(result, args.commit_message),
                    paths=push_paths,
                )
                result.update(push_result)
            else:
                result["pushed"] = False

        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        if temp_parent and not args.keep_temp:
            shutil.rmtree(temp_parent, ignore_errors=True)


if __name__ == "__main__":
    main()
