#!/usr/bin/env python3
from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover
    dotenv_values = None


REQUIRED_GLOBAL_VARS = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
)

HOOK_EVENTS = ("SessionStart", "Stop")


def load_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    if dotenv_values is not None:
        values = dotenv_values(path)
        return {key: str(value).strip() for key, value in values.items() if value is not None}

    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        result[key.strip()] = value.strip().strip("'\"")
    return result


def write_text_if_changed(path: Path, content: str) -> bool:
    current = None
    if path.exists():
        current = path.read_text(encoding="utf-8")
    if current == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def ensure_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def render_template(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    home = str(Path.home())
    return content.replace("/Users/michal", home)


def load_hooks_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"hooks": {}}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SystemExit(f"Unexpected top-level structure in {path}")
    hooks = parsed.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"Invalid hooks object in {path}")
    return parsed


def ensure_hook_command(config: dict[str, Any], event: str, command: str) -> bool:
    hooks = config.setdefault("hooks", {})
    event_list = hooks.setdefault(event, [])
    if not isinstance(event_list, list):
        raise SystemExit(f"Invalid hook list for event {event}")

    target_block: dict[str, Any] | None = None
    for block in event_list:
        if isinstance(block, dict) and isinstance(block.get("hooks"), list) and "matcher" not in block:
            target_block = block
            break

    if target_block is None:
        target_block = {"hooks": []}
        event_list.append(target_block)

    hook_entries = target_block.setdefault("hooks", [])
    for entry in hook_entries:
        if isinstance(entry, dict) and entry.get("type") == "command" and entry.get("command") == command:
            return False

    hook_entries.append({"type": "command", "command": command})
    return True


def main() -> int:
    skill_dir = Path(__file__).resolve().parents[1]
    templates_dir = Path(__file__).resolve().parent / "templates"
    codex_home = Path.home() / ".codex"
    hooks_dir = codex_home / "hooks"
    hooks_json_path = codex_home / "hooks.json"

    template_map = {
        templates_dir / "langfuse_stop_export.py": hooks_dir / "langfuse_stop_export.py",
        templates_dir / "langfuse_stop_export.sh": hooks_dir / "langfuse_stop_export.sh",
        templates_dir / "langfuse.env.example": codex_home / "langfuse.env.example",
    }

    changed_files: list[str] = []
    for source, target in template_map.items():
        content = render_template(source)
        if write_text_if_changed(target, content):
            changed_files.append(str(target))
        if target.suffix in {".py", ".sh"}:
            ensure_executable(target)

    hook_command = str(hooks_dir / "langfuse_stop_export.sh")
    hooks_config = load_hooks_json(hooks_json_path)
    hooks_changed = False
    installed_events: list[str] = []
    for event in HOOK_EVENTS:
        changed = ensure_hook_command(hooks_config, event, hook_command)
        hooks_changed = hooks_changed or changed
        installed_events.append(event)

    if hooks_changed or not hooks_json_path.exists():
        hooks_json_path.write_text(json.dumps(hooks_config, indent=2) + "\n", encoding="utf-8")
        if str(hooks_json_path) not in changed_files:
            changed_files.append(str(hooks_json_path))

    global_env_path = codex_home / ".env"
    global_env = load_dotenv(global_env_path)
    missing_global_vars = [name for name in REQUIRED_GLOBAL_VARS if not global_env.get(name)]

    result = {
        "ok": True,
        "skill_dir": str(skill_dir),
        "codex_home": str(codex_home),
        "written_files": changed_files,
        "hooks_json_path": str(hooks_json_path),
        "hooks_installed": installed_events,
        "hook_command": hook_command,
        "global_env_path": str(global_env_path),
        "example_env_path": str(codex_home / "langfuse.env.example"),
        "missing_global_vars": missing_global_vars,
        "local_override_filenames": [".codex.env", ".env.local", ".env"],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
