#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from detect_stack import detect_existing_guardrails, detect_frameworks, detect_languages, detect_package_manager


def js_ts_tools(frameworks: list[str]) -> dict[str, list[str]]:
    dev = [
        "eslint",
        "@eslint/js",
        "typescript-eslint",
        "eslint-plugin-import",
        "eslint-plugin-security",
        "eslint-plugin-sonarjs",
        "oxlint",
        "dependency-cruiser",
        "knip",
    ]
    if "nextjs" in frameworks:
        dev.extend(["eslint-config-next", "@next/bundle-analyzer", "@lhci/cli"])
    return {"devDependencies": sorted(set(dev))}


def python_tools() -> dict[str, list[str]]:
    return {"pip": ["ruff", "mypy", "bandit", "pip-audit", "pytest"]}


def go_tools() -> dict[str, list[str]]:
    return {"go_install": ["golangci-lint", "govulncheck", "gosec"]}


def rust_tools() -> dict[str, list[str]]:
    return {"cargo": ["clippy", "cargo-audit", "cargo-nextest"]}


def install_commands(package_manager: str, tool_spec: dict[str, list[str]]) -> list[str]:
    commands: list[str] = []
    if "devDependencies" in tool_spec:
        joined = " ".join(tool_spec["devDependencies"])
        if package_manager == "pnpm":
            commands.append(f"pnpm add -D {joined}")
        elif package_manager == "yarn":
            commands.append(f"yarn add -D {joined}")
        elif package_manager == "bun":
            commands.append(f"bun add -d {joined}")
        else:
            commands.append(f"npm i -D {joined}")
    if "pip" in tool_spec:
        commands.append(f"python3 -m pip install {' '.join(tool_spec['pip'])}")
    if "go_install" in tool_spec:
        commands.append("go install " + " ".join(tool_spec["go_install"]))
    if "cargo" in tool_spec:
        commands.extend(
            [
                "cargo clippy --all-targets --all-features -- -D warnings",
                "cargo install cargo-audit cargo-nextest",
            ]
        )
    return commands


def gate_contract() -> dict[str, list[str]]:
    return {
        "offline_quality": [
            "format check",
            "lint/static analysis (deny warnings)",
            "type checking",
            "architecture/dependency boundary checks",
            "tests",
        ],
        "offline_security": [
            "secrets scan",
            "dependency vulnerability scan",
            "manual-review obligations report",
        ],
        "hooks": [
            "pre-commit -> quality",
            "pre-push -> quality + security",
        ],
    }


def to_markdown(plan: dict) -> str:
    lines: list[str] = []
    lines.append("# Offline Gates Plan")
    lines.append("")
    lines.append("## Detected Stack")
    lines.append(f"- Package manager: `{plan['stack']['package_manager']}`")
    lines.append(f"- Languages: `{', '.join(plan['stack']['languages']) or 'none'}`")
    lines.append(f"- Frameworks: `{', '.join(plan['stack']['frameworks']) or 'none'}`")
    lines.append("")
    lines.append("## Install Commands")
    for cmd in plan["install_commands"]:
        lines.append(f"- `{cmd}`")
    lines.append("")
    lines.append("## Deterministic Gate Contract")
    lines.append("- Quality: " + ", ".join(plan["gate_contract"]["offline_quality"]))
    lines.append("- Security: " + ", ".join(plan["gate_contract"]["offline_security"]))
    lines.append("- Hooks: " + ", ".join(plan["gate_contract"]["hooks"]))
    lines.append("")
    lines.append("## Required Repository Artifacts")
    lines.append("- `scripts/ci/run_quality_gates.sh` (or framework-equivalent)")
    lines.append("- `scripts/ci/run_security_review.sh` (or framework-equivalent)")
    lines.append("- `scripts/ci/run_offline_static_gates.sh` (or framework-equivalent)")
    lines.append("- `.githooks/pre-commit` and `.githooks/pre-push`")
    lines.append("- Instruction policy file (`AGENTS.md` recommended)")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic offline gate plan.")
    parser.add_argument("--repo", default=".", help="Path to repository root.")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    parser.add_argument("--output", default="", help="Optional output file path.")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    stack = {
        "package_manager": detect_package_manager(repo),
        "languages": detect_languages(repo),
        "frameworks": detect_frameworks(repo),
        "existing_guardrails": detect_existing_guardrails(repo),
    }

    tool_spec: dict[str, list[str]] = {}
    if any(language in stack["languages"] for language in ("typescript", "javascript")):
        tool_spec.update(js_ts_tools(stack["frameworks"]))
    if "python" in stack["languages"]:
        tool_spec.update(python_tools())
    if "go" in stack["languages"]:
        tool_spec.update(go_tools())
    if "rust" in stack["languages"]:
        tool_spec.update(rust_tools())

    plan = {
        "stack": stack,
        "tool_spec": tool_spec,
        "install_commands": install_commands(stack["package_manager"], tool_spec),
        "gate_contract": gate_contract(),
    }

    if args.format == "markdown":
        content = to_markdown(plan)
    else:
        content = json.dumps(plan, indent=2, ensure_ascii=True) + "\n"

    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
