#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path


DEFAULT_REPO = Path("/Users/michal/Projects/skillet")
DEFAULT_INSTALL_REPO_SLUG = "michaelpetrik/skillet"
README_RELATIVE_PATH = Path("skills/README.md")
CHANGELOG_NAME = "CHANGELOG.md"
SKILL_FILE = "SKILL.md"


@dataclass
class FrontmatterDocument:
    has_frontmatter: bool
    frontmatter_lines: list[str]
    body: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a local Codex skill bundle into the skillet repository."
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Path to the source skill directory or its SKILL.md file.",
    )
    parser.add_argument(
        "category",
        nargs="?",
        help="Published category slug, e.g. tracing or general.",
    )
    parser.add_argument("--source", dest="source_flag", help=argparse.SUPPRESS)
    parser.add_argument("--category", dest="category_flag", help=argparse.SUPPRESS)
    parser.add_argument(
        "--repo",
        help="Path to a local skillet checkout. When omitted, publish goes to remote mode by default.",
    )
    parser.add_argument(
        "--remote",
        help=f"Publish to a remote GitHub repository without a local checkout, e.g. michaelpetrik/skillet. Defaults to {DEFAULT_INSTALL_REPO_SLUG}.",
    )
    parser.add_argument(
        "--remote-url",
        help="Optional git clone URL for --remote, e.g. git@github.com:michaelpetrik/skillet.git.",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Remote branch to clone and push in --remote mode. Defaults to main.",
    )
    parser.add_argument(
        "--commit-message",
        help="Optional commit message for --remote mode.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary clone used by --remote for inspection instead of deleting it.",
    )
    parser.add_argument(
        "--target-name",
        help="Optional published skill directory name. Defaults to the source skill directory name.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the publication plan without writing or pushing files.",
    )
    args = parser.parse_args()

    if args.source and args.source_flag and args.source != args.source_flag:
        parser.error("Pass source either positionally or via --source, not both with different values.")
    if args.category and args.category_flag and args.category != args.category_flag:
        parser.error("Pass category either positionally or via --category, not both with different values.")

    args.source = args.source or args.source_flag
    args.category = args.category or args.category_flag

    if not args.source or not args.category:
        parser.error("source and category are required.")

    delattr(args, "source_flag")
    delattr(args, "category_flag")
    return args


def resolve_source_root(source: str) -> Path:
    source_path = Path(source).expanduser().resolve()
    if source_path.is_file():
        if source_path.name != SKILL_FILE:
            raise SystemExit(f"Expected {SKILL_FILE} or a skill directory, got: {source_path}")
        return source_path.parent
    if source_path.is_dir():
        return source_path
    raise SystemExit(f"Source path does not exist: {source_path}")


def slug_to_title(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.replace("_", "-").split("-") if part)


def parse_document(text: str) -> FrontmatterDocument:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            raw_frontmatter = text[4:end]
            body = text[end + 5 :]
            return FrontmatterDocument(True, raw_frontmatter.splitlines(), body)
    return FrontmatterDocument(False, [], text)


def extract_frontmatter_value(lines: list[str], key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.+?)\s*$")
    for line in lines:
        match = pattern.match(line)
        if match:
            return match.group(1).strip().strip("'\"")
    return None


def set_frontmatter_fields(lines: list[str], category_title: str, version: str) -> list[str]:
    result: list[str] = []
    for line in lines:
        if re.match(r"^(category|version):\s*", line):
            continue
        result.append(line)

    insert_at = len(result)
    for index, line in enumerate(result):
        if re.match(r"^description:\s*", line):
            insert_at = index + 1
            break

    result[insert_at:insert_at] = [f"category: {category_title}", f"version: {version}"]
    return result


def build_document(lines: list[str], body: str) -> str:
    if not lines:
        return body
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def canonical_skill_text(text: str) -> str:
    document = parse_document(text)
    if not document.has_frontmatter:
        return text
    filtered = [
        line
        for line in document.frontmatter_lines
        if not re.match(r"^(category|version):\s*", line)
    ]
    return build_document(filtered, document.body)


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if "__pycache__/" in relative or relative.endswith(".pyc") or relative.endswith(".DS_Store"):
            continue
        files[relative] = path
    return files


def is_semver(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"\d+\.\d+\.\d+", value))


def parse_semver(value: str) -> tuple[int, int, int]:
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def bump_patch(value: str | None) -> str:
    if not is_semver(value):
        return "1.0.0"
    major, minor, patch = parse_semver(value)
    return f"{major}.{minor}.{patch + 1}"


def choose_version(existing: str | None, source: str | None, target_exists: bool, changed: bool) -> str:
    if not target_exists:
        if is_semver(source):
            return source  # type: ignore[arg-type]
        return "1.0.0"

    if not changed:
        if is_semver(existing):
            return existing  # type: ignore[arg-type]
        if is_semver(source):
            return source  # type: ignore[arg-type]
        return "1.0.0"

    if is_semver(source) and is_semver(existing):
        if parse_semver(source) > parse_semver(existing):  # type: ignore[arg-type]
            return source  # type: ignore[arg-type]

    if is_semver(source) and not is_semver(existing):
        return source  # type: ignore[arg-type]

    return bump_patch(existing)


def extract_h1(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def build_readme_entry(
    category_slug: str,
    skill_name: str,
    display_name: str,
    description: str,
    install_repo_slug: str,
) -> str:
    return (
        f"- **[{display_name}](./{category_slug}/{skill_name}/SKILL.md)**: {description}\n\n"
        "  **Install using skills.sh:**\n\n"
        "  With `npm`:\n"
        "  ```bash\n"
        f"  npx skills add {install_repo_slug} --skill {skill_name}\n"
        "  ```\n\n"
        "  With `bun`:\n"
        "  ```bash\n"
        f"  bunx skills add {install_repo_slug} --skill {skill_name}\n"
        "  ```\n"
    )


def update_readme(
    readme_path: Path,
    category_slug: str,
    category_title: str,
    skill_name: str,
    display_name: str,
    description: str,
    install_repo_slug: str,
) -> tuple[str, bool]:
    intro = (
        "# Skillet Skills\n\n"
        "This directory contains specialized skills that extend the capabilities of AI agents working on this project.\n"
    )
    current = readme_path.read_text() if readme_path.exists() else intro
    entry = build_readme_entry(
        category_slug=category_slug,
        skill_name=skill_name,
        display_name=display_name,
        description=description,
        install_repo_slug=install_repo_slug,
    )

    entry_pattern = re.compile(
        rf"(?ms)^- \*\*\[[^\]]+\]\(\./{re.escape(category_slug)}/{re.escape(skill_name)}/SKILL\.md\)\*\*:.*?(?=^## |\Z)"
    )
    updated = current
    if entry_pattern.search(updated):
        updated = entry_pattern.sub(entry, updated, count=1)
        return updated, updated != current

    section_pattern = re.compile(rf"(?ms)^## {re.escape(category_title)}\n(.*?)(?=^## |\Z)")
    section_match = section_pattern.search(updated)
    if section_match:
        section_body = section_match.group(1).rstrip()
        replacement = (
            f"## {category_title}\n\n{section_body}\n\n{entry}"
            if section_body
            else f"## {category_title}\n\n{entry}"
        )
        updated = updated[: section_match.start()] + replacement + updated[section_match.end() :]
        return updated, updated != current

    updated = updated.rstrip() + f"\n\n## {category_title}\n\n{entry}"
    return updated + ("\n" if not updated.endswith("\n") else ""), updated != current


def build_changelog_entry(
    version: str,
    skill_name: str,
    category_title: str,
    added: list[str],
    changed: list[str],
    removed: list[str],
    initial_release: bool,
) -> str:
    today = date.today().isoformat()
    lines = [f"## [{version}] - {today}"]

    if initial_release:
        lines.extend(
            [
                "### Added",
                f"- Initial publication of the `{skill_name}` skill in the `{category_title}` category.",
            ]
        )
        for relative in added:
            if relative != SKILL_FILE:
                lines.append(f"- Added bundled resource `{relative}`.")
        return "\n".join(lines) + "\n"

    if added:
        lines.append("### Added")
        for relative in added:
            if relative == SKILL_FILE:
                lines.append("- Added the published `SKILL.md` entry.")
            else:
                lines.append(f"- Added bundled resource `{relative}`.")

    if changed:
        lines.append("### Changed")
        lines.append("- Synchronized the published skill bundle with the source skill.")
        for relative in changed:
            lines.append(f"- Updated `{relative}`.")

    if removed:
        lines.append("### Removed")
        for relative in removed:
            lines.append(f"- Removed stale published file `{relative}`.")

    return "\n".join(lines) + "\n"


def update_changelog(
    changelog_path: Path,
    version: str,
    skill_name: str,
    category_title: str,
    added: list[str],
    changed: list[str],
    removed: list[str],
    initial_release: bool,
) -> tuple[str, bool]:
    header = (
        "# Changelog\n\n"
        "All notable changes to this skill are documented in this file.\n\n"
        "The format is based on Keep a Changelog and this project uses Semantic Versioning.\n\n"
    )
    current = changelog_path.read_text() if changelog_path.exists() else header
    entry = build_changelog_entry(
        version=version,
        skill_name=skill_name,
        category_title=category_title,
        added=added,
        changed=changed,
        removed=removed,
        initial_release=initial_release,
    )

    if current.startswith("# Changelog"):
        header_match = re.match(r"(?s)\A(# Changelog.*?Semantic Versioning\.\n\n)", current)
        if header_match:
            updated = header_match.group(1) + entry + current[header_match.end() :].lstrip("\n")
        else:
            updated = header + entry + current[len(header) :].lstrip("\n")
    else:
        updated = header + entry + current.lstrip("\n")
    return updated, updated != current


def ensure_directory(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.write_text(content)


def copy_file(source: Path, target: Path, dry_run: bool) -> None:
    if dry_run:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def remove_path(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    command = ["git", *args]
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"git command failed: {' '.join(command)}\n"
            f"cwd: {cwd}\n"
            f"stdout:\n{exc.stdout}\n"
            f"stderr:\n{exc.stderr}"
        ) from exc


def resolve_install_repo_slug(repo_root: Path) -> str:
    try:
        result = run_git(["remote", "get-url", "origin"], cwd=repo_root)
    except SystemExit:
        return DEFAULT_INSTALL_REPO_SLUG

    remote_url = result.stdout.strip()
    patterns = [
        re.compile(r"^https://github\.com/(?P<slug>[^/]+/[^/.]+)(?:\.git)?$"),
        re.compile(r"^git@github\.com:(?P<slug>[^/]+/[^/.]+)(?:\.git)?$"),
    ]
    for pattern in patterns:
        match = pattern.match(remote_url)
        if match:
            return match.group("slug")
    return DEFAULT_INSTALL_REPO_SLUG


def prepare_remote_checkout(remote_slug: str, remote_url: str | None, branch: str) -> tuple[Path, Path]:
    temp_parent = Path(tempfile.mkdtemp(prefix="publish-skill-to-skillet-"))
    repo_root = temp_parent / "repo"
    clone_url = remote_url or f"https://github.com/{remote_slug}.git"
    run_git(["clone", "--depth", "1", "--branch", branch, clone_url, str(repo_root)], cwd=temp_parent)
    return repo_root, temp_parent


def build_commit_message(result: dict[str, object], explicit_message: str | None) -> str:
    if explicit_message:
        return explicit_message

    skill_name = str(result["skill_name"])
    category = str(result["category"])
    target_name = str(result["target_name"])
    version = str(result["version"])
    verb = "Publish" if not bool(result["target_previously_existed"]) else "Update"
    return f"{verb} skill {skill_name} to skills/{category}/{target_name} (v{version})"


def commit_and_push_remote_checkout(
    repo_root: Path,
    result: dict[str, object],
    branch: str,
    commit_message: str,
) -> dict[str, object]:
    tracked_paths = [
        README_RELATIVE_PATH.as_posix(),
        str(result["target_relative_root"]),
    ]
    run_git(["add", "-A", *tracked_paths], cwd=repo_root)

    status = run_git(["status", "--short", "--", *tracked_paths], cwd=repo_root).stdout.strip()
    if not status:
        return {
            "pushed": False,
            "commit_message": commit_message,
            "commit_sha": None,
            "git_status": "",
        }

    run_git(["commit", "-m", commit_message], cwd=repo_root)
    commit_sha = run_git(["rev-parse", "HEAD"], cwd=repo_root).stdout.strip()
    run_git(["push", "origin", branch], cwd=repo_root)
    return {
        "pushed": True,
        "commit_message": commit_message,
        "commit_sha": commit_sha,
        "git_status": status,
    }


def publish_into_repo(
    repo_root: Path,
    source_root: Path,
    category_slug: str,
    target_name: str,
    dry_run: bool,
    install_repo_slug: str,
) -> dict[str, object]:
    if not repo_root.exists():
        raise SystemExit(f"Skillet repo does not exist: {repo_root}")

    source_skill_path = source_root / SKILL_FILE
    if not source_skill_path.exists():
        raise SystemExit(f"Source skill is missing {SKILL_FILE}: {source_skill_path}")

    category_title = slug_to_title(category_slug)
    target_relative_root = Path("skills") / category_slug / target_name
    target_root = repo_root / target_relative_root
    target_skill_path = target_root / SKILL_FILE
    target_previously_existed = target_root.exists()

    source_skill_text = source_skill_path.read_text()
    source_document = parse_document(source_skill_text)
    source_name = extract_frontmatter_value(source_document.frontmatter_lines, "name") or target_name
    source_description = extract_frontmatter_value(source_document.frontmatter_lines, "description") or ""
    source_version = extract_frontmatter_value(source_document.frontmatter_lines, "version")
    display_name = extract_h1(source_document.body) or slug_to_title(source_name)

    source_files = collect_files(source_root)
    target_files = collect_files(target_root) if target_previously_existed else {}

    added: list[str] = []
    changed: list[str] = []
    removed: list[str] = []

    for relative, source_path in source_files.items():
        target_path = target_root / relative
        if not target_path.exists():
            added.append(relative)
            continue
        if relative == SKILL_FILE:
            if canonical_skill_text(source_path.read_text()) != canonical_skill_text(target_path.read_text()):
                changed.append(relative)
            continue
        if file_digest(source_path) != file_digest(target_path):
            changed.append(relative)

    for relative in target_files:
        if relative == CHANGELOG_NAME:
            continue
        if relative not in source_files:
            removed.append(relative)

    publication_changed = bool(added or changed or removed or not target_previously_existed)
    existing_skill_text = target_skill_path.read_text() if target_skill_path.exists() else ""
    existing_document = parse_document(existing_skill_text)
    existing_version = extract_frontmatter_value(existing_document.frontmatter_lines, "version")
    version = choose_version(
        existing=existing_version,
        source=source_version,
        target_exists=target_previously_existed,
        changed=publication_changed,
    )

    published_frontmatter = set_frontmatter_fields(
        source_document.frontmatter_lines,
        category_title=category_title,
        version=version,
    )
    published_skill_text = build_document(published_frontmatter, source_document.body)
    target_skill_needs_write = (
        not target_skill_path.exists() or target_skill_path.read_text() != published_skill_text
    )

    changelog_path = target_root / CHANGELOG_NAME
    changelog_updated = False
    changelog_content = ""
    if not target_previously_existed or publication_changed:
        changelog_content, changelog_updated = update_changelog(
            changelog_path=changelog_path,
            version=version,
            skill_name=source_name,
            category_title=category_title,
            added=added,
            changed=changed,
            removed=removed,
            initial_release=not target_previously_existed,
        )

    readme_path = repo_root / README_RELATIVE_PATH
    readme_content, readme_updated = update_readme(
        readme_path=readme_path,
        category_slug=category_slug,
        category_title=category_title,
        skill_name=source_name,
        display_name=display_name,
        description=source_description,
        install_repo_slug=install_repo_slug,
    )

    changed_files_written: list[str] = []
    removed_files_written: list[str] = []

    ensure_directory(target_root, dry_run)
    for relative, source_path in source_files.items():
        target_path = target_root / relative
        if relative == SKILL_FILE:
            if target_skill_needs_write:
                write_text(target_path, published_skill_text, dry_run)
                changed_files_written.append(target_path.relative_to(repo_root).as_posix())
            continue

        needs_copy = not target_path.exists() or file_digest(source_path) != file_digest(target_path)
        if needs_copy:
            copy_file(source_path, target_path, dry_run)
            changed_files_written.append(target_path.relative_to(repo_root).as_posix())

    for relative in removed:
        target_path = target_root / relative
        remove_path(target_path, dry_run)
        removed_files_written.append(target_path.relative_to(repo_root).as_posix())

    if changelog_updated:
        write_text(changelog_path, changelog_content, dry_run)
        changed_files_written.append(changelog_path.relative_to(repo_root).as_posix())

    if readme_updated:
        write_text(readme_path, readme_content, dry_run)
        changed_files_written.append(readme_path.relative_to(repo_root).as_posix())

    return {
        "source_root": str(source_root),
        "repo_root": str(repo_root),
        "target_root": str(target_root),
        "target_relative_root": target_relative_root.as_posix(),
        "target_name": target_name,
        "target_previously_existed": target_previously_existed,
        "skill_name": source_name,
        "display_name": display_name,
        "category": category_slug,
        "category_title": category_title,
        "install_repo_slug": install_repo_slug,
        "version": version,
        "added": added,
        "changed": changed,
        "removed": removed,
        "files_written": changed_files_written,
        "files_removed": removed_files_written,
        "changelog_updated": changelog_updated,
        "readme_updated": readme_updated,
        "dry_run": dry_run,
        "no_changes": not (
            target_skill_needs_write
            or changelog_updated
            or readme_updated
            or changed_files_written
            or removed_files_written
        ),
    }


def main() -> None:
    args = parse_args()
    if args.remote and args.repo:
        raise SystemExit("Use either --repo or --remote, not both.")
    if args.remote_url and args.repo:
        raise SystemExit("--remote-url cannot be combined with --repo.")

    source_root = resolve_source_root(args.source)
    category_slug = args.category.strip().strip("/").lower()
    if not category_slug:
        raise SystemExit("Category must not be empty.")

    target_name = args.target_name or source_root.name

    temp_parent: Path | None = None
    if args.repo:
        repo_root = Path(args.repo).expanduser().resolve()
        install_repo_slug = resolve_install_repo_slug(repo_root)
        mode = "local"
        remote_slug = None
    else:
        remote_slug = args.remote or DEFAULT_INSTALL_REPO_SLUG
        repo_root, temp_parent = prepare_remote_checkout(
            remote_slug=remote_slug,
            remote_url=args.remote_url,
            branch=args.branch,
        )
        install_repo_slug = remote_slug
        mode = "remote"

    try:
        result = publish_into_repo(
            repo_root=repo_root,
            source_root=source_root,
            category_slug=category_slug,
            target_name=target_name,
            dry_run=args.dry_run,
            install_repo_slug=install_repo_slug,
        )
        result["mode"] = mode

        if mode == "remote":
            result["remote"] = remote_slug
            result["remote_branch"] = args.branch
            result["remote_url"] = args.remote_url or f"https://github.com/{remote_slug}.git"
            result["temporary_repo_root"] = str(repo_root)

            if not args.dry_run and not bool(result["no_changes"]):
                push_result = commit_and_push_remote_checkout(
                    repo_root=repo_root,
                    result=result,
                    branch=args.branch,
                    commit_message=build_commit_message(result, args.commit_message),
                )
                result.update(push_result)
            else:
                result["pushed"] = False

        print(json.dumps(result, indent=2))
    finally:
        if temp_parent and not args.keep_temp:
            shutil.rmtree(temp_parent, ignore_errors=True)


if __name__ == "__main__":
    main()
