#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def has_any(repo: Path, patterns: list[str]) -> bool:
    for pattern in patterns:
        if any(repo.glob(pattern)):
            return True
    return False


def detect_package_manager(repo: Path) -> str:
    if (repo / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (repo / "yarn.lock").exists():
        return "yarn"
    if (repo / "bun.lockb").exists() or (repo / "bun.lock").exists():
        return "bun"
    if (repo / "package-lock.json").exists():
        return "npm"
    if (repo / "poetry.lock").exists():
        return "poetry"
    if (repo / "uv.lock").exists():
        return "uv"
    if (repo / "Pipfile.lock").exists():
        return "pipenv"
    if (repo / "Cargo.lock").exists():
        return "cargo"
    if (repo / "go.sum").exists():
        return "go"
    return "unknown"


def detect_languages(repo: Path) -> list[str]:
    languages: set[str] = set()
    patterns = {
        "typescript": ["**/*.ts", "**/*.tsx"],
        "javascript": ["**/*.js", "**/*.jsx", "**/*.mjs", "**/*.cjs"],
        "python": ["**/*.py"],
        "go": ["**/*.go"],
        "rust": ["**/*.rs"],
        "java": ["**/*.java", "**/*.kt"],
        "ruby": ["**/*.rb"],
        "php": ["**/*.php"],
        "csharp": ["**/*.cs"],
    }
    for language, globs in patterns.items():
        if has_any(repo, globs):
            languages.add(language)
    return sorted(languages)


def detect_frameworks(repo: Path) -> list[str]:
    frameworks: set[str] = set()

    package_jsons = list(repo.glob("**/package.json"))
    package_blob = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore") for p in package_jsons
    )

    if "next" in package_blob or has_any(
        repo, ["**/next.config.js", "**/next.config.mjs", "**/next.config.ts"]
    ):
        frameworks.add("nextjs")
    if "vite" in package_blob or has_any(repo, ["**/vite.config.ts", "**/vite.config.js"]):
        frameworks.add("vite")
    if "react" in package_blob:
        frameworks.add("react")
    if "nuxt" in package_blob:
        frameworks.add("nuxt")
    if "svelte" in package_blob:
        frameworks.add("svelte")
    if "angular" in package_blob or has_any(repo, ["**/angular.json"]):
        frameworks.add("angular")

    if has_any(repo, ["**/pyproject.toml", "**/requirements*.txt"]):
        py_text = "\n".join(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in repo.glob("**/pyproject.toml")
        )
        req_text = "\n".join(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in repo.glob("**/requirements*.txt")
        )
        if "fastapi" in py_text or "fastapi" in req_text:
            frameworks.add("fastapi")
        if "django" in py_text or "django" in req_text:
            frameworks.add("django")
        if "flask" in py_text or "flask" in req_text:
            frameworks.add("flask")

    if (repo / "go.mod").exists():
        frameworks.add("go")
    if (repo / "Cargo.toml").exists():
        frameworks.add("rust")
    if (repo / "pom.xml").exists() or (repo / "build.gradle").exists():
        frameworks.add("jvm")

    return sorted(frameworks)


def detect_existing_guardrails(repo: Path) -> dict[str, bool]:
    return {
        "scripts_ci": (repo / "scripts" / "ci").exists(),
        "githooks_dir": (repo / ".githooks").exists(),
        "pre_commit_hook": (repo / ".githooks" / "pre-commit").exists(),
        "pre_push_hook": (repo / ".githooks" / "pre-push").exists(),
        "github_actions": (repo / ".github" / "workflows").exists(),
        "agents_md": (repo / "AGENTS.md").exists(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect project stack and existing guardrail infrastructure."
    )
    parser.add_argument("--repo", default=".", help="Path to repository root.")
    parser.add_argument(
        "--output",
        default="",
        help="Optional output file path. Prints to stdout when omitted.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    result = {
        "repo": str(repo),
        "package_manager": detect_package_manager(repo),
        "languages": detect_languages(repo),
        "frameworks": detect_frameworks(repo),
        "existing_guardrails": detect_existing_guardrails(repo),
    }

    blob = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).write_text(blob + "\n", encoding="utf-8")
    else:
        print(blob)


if __name__ == "__main__":
    main()
