#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import socket
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from langfuse import Langfuse


CODEX_HOME = Path.home() / ".codex"
SESSIONS_DIR = CODEX_HOME / "sessions"
STATE_DIR = CODEX_HOME / "langfuse-export"
SPOOL_DIR = STATE_DIR / "spool"
EXPORTED_DIR = STATE_DIR / "exported"
LOG_PATH = CODEX_HOME / "log" / "langfuse-export.log"
LOCK_PATH = STATE_DIR / "hook.lock"

OVERRIDE_FILENAMES = (".codex.env", ".env.local", ".env")
PROJECT_ENV_PATH_VAR = "CODEX_LANGFUSE_PROJECT_ENV_PATH"
DEFAULT_TIMEOUT_SECONDS = 4
DEFAULT_RAW_CHUNK_BYTES = 180_000
MAX_RECENT_TRANSCRIPTS = 120

SECRET_VALUE_PATTERNS = (
    re.compile(r"(?im)\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD))\s*=\s*([^\s\"']+|\"[^\"]*\"|'[^']*')"),
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)([A-Za-z0-9._\-+/=]+)"),
    re.compile(r"(?i)\b(sk|pk)-[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
)


@dataclass
class Settings:
    enabled: bool
    public_key: str | None
    secret_key: str | None
    base_url: str | None
    logical_project: str | None
    tags: list[str]
    user_id: str | None
    redaction_mode: str
    raw_chunk_bytes: int
    timeout_seconds: int
    cwd: Path
    override_path: Path | None


@dataclass
class Snapshot:
    session_id: str
    trace_id: str
    transcript_path: Path
    transcript_sha256: str
    transcript_size: int
    hook_event: str
    cwd: Path
    repo_root: str | None
    cli_version: str | None
    source: str | None
    started_at: str | None
    last_event_at: str | None
    summary: dict[str, Any]
    raw_chunks: list[str]
    tool_names: list[str]


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hook-input-file", type=Path, required=True)
    return parser.parse_args()


def parse_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def parse_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(str(value).strip())
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        output.append(cleaned)
    return output


def redact_text(text: str, mode: str) -> str:
    if mode != "basic" or not text:
        return text

    redacted = text

    def assignment_replacer(match: re.Match[str]) -> str:
        return f"{match.group(1)}=<redacted>"

    redacted = SECRET_VALUE_PATTERNS[0].sub(assignment_replacer, redacted)
    redacted = SECRET_VALUE_PATTERNS[1].sub(r"\1<redacted>", redacted)
    for pattern in SECRET_VALUE_PATTERNS[2:]:
        redacted = pattern.sub("<redacted>", redacted)
    return redacted


def redact_object(value: Any, mode: str) -> Any:
    if mode != "basic":
        return value
    if isinstance(value, str):
        return redact_text(value, mode)
    if isinstance(value, list):
        return [redact_object(item, mode) for item in value]
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            if re.search(r"(key|token|secret|password)", key, re.IGNORECASE):
                output[key] = "<redacted>" if item not in (None, "") else item
            else:
                output[key] = redact_object(item, mode)
        return output
    return value


def load_env_file(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    values = dotenv_values(path)
    return {key.strip(): str(value).strip() for key, value in values.items() if value is not None}


def load_non_empty_env_file(path: Path | None) -> dict[str, str]:
    return {key: value for key, value in load_env_file(path).items() if value}


def resolve_project_env_path(cwd: Path) -> Path | None:
    explicit_path = os.environ.get(PROJECT_ENV_PATH_VAR)
    if explicit_path:
        candidate = Path(explicit_path).expanduser()
        if candidate.is_file():
            return candidate.resolve()

    fallback = cwd.resolve() / ".codex" / ".env"
    if fallback.is_file():
        return fallback.resolve()
    return None


def find_nearest_override(cwd: Path) -> Path | None:
    current = cwd.resolve()
    for directory in [current, *current.parents]:
        for filename in OVERRIDE_FILENAMES:
            candidate = directory / filename
            if candidate.is_file():
                return candidate
    return None


def resolve_settings(cwd: Path) -> Settings:
    global_env = load_env_file(CODEX_HOME / ".env")
    override_path = find_nearest_override(cwd)
    override_env = load_env_file(override_path)
    project_env_path = resolve_project_env_path(cwd)
    project_env = load_non_empty_env_file(project_env_path)

    merged: dict[str, str] = {}
    merged.update(global_env)
    merged.update({key: value for key, value in os.environ.items() if isinstance(value, str)})
    merged.update(override_env)
    merged.update(project_env)

    enabled = parse_bool(merged.get("CODEX_LANGFUSE_ENABLED"), True)
    public_key = merged.get("LANGFUSE_PUBLIC_KEY")
    secret_key = merged.get("LANGFUSE_SECRET_KEY")
    base_url = merged.get("LANGFUSE_BASE_URL") or merged.get("LANGFUSE_HOST")
    logical_project = merged.get("CODEX_LANGFUSE_PROJECT")
    tags = unique_strings(
        ["codex", "stop-hook", *merged.get("CODEX_LANGFUSE_TAGS", "").split(",")]
        + ([f"project:{logical_project}"] if logical_project else [])
    )
    user_id = merged.get("CODEX_LANGFUSE_USER_ID") or os.environ.get("USER")
    redaction_mode = (merged.get("CODEX_LANGFUSE_REDACTION_MODE") or "basic").strip().lower()
    raw_chunk_bytes = parse_int(
        merged.get("CODEX_LANGFUSE_RAW_CHUNK_BYTES"),
        default=DEFAULT_RAW_CHUNK_BYTES,
        minimum=10_000,
        maximum=800_000,
    )
    timeout_seconds = parse_int(
        merged.get("CODEX_LANGFUSE_TIMEOUT_SECONDS"),
        default=DEFAULT_TIMEOUT_SECONDS,
        minimum=1,
        maximum=20,
    )

    if not enabled or not public_key or not secret_key or not base_url:
        enabled = False

    return Settings(
        enabled=enabled,
        public_key=public_key,
        secret_key=secret_key,
        base_url=base_url,
        logical_project=logical_project,
        tags=tags,
        user_id=user_id,
        redaction_mode=redaction_mode,
        raw_chunk_bytes=raw_chunk_bytes,
        timeout_seconds=timeout_seconds,
        cwd=cwd.resolve(),
        override_path=override_path.resolve() if override_path else None,
    )


def read_hook_payload(path: Path) -> tuple[str, dict[str, Any]]:
    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw:
        return "", {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return raw, parsed
    except json.JSONDecodeError:
        pass
    return raw, {}


def infer_hook_event(payload: dict[str, Any]) -> str:
    event = payload.get("hook_event_name") or payload.get("event") or payload.get("type")
    if event == "agent-turn-complete":
        return "Stop"
    return str(event or "unknown")


def find_recursive_key(value: Any, wanted_keys: set[str]) -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in wanted_keys and isinstance(item, str) and item.strip():
                return item.strip()
            found = find_recursive_key(item, wanted_keys)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_recursive_key(item, wanted_keys)
            if found:
                return found
    return None


def find_session_file_by_id(session_id: str) -> Path | None:
    suffix = f"{session_id}.jsonl"
    matches = [path for path in SESSIONS_DIR.rglob("*.jsonl") if path.name.endswith(suffix)]
    if not matches:
        return None
    matches.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0]


def read_session_meta(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            first_line = handle.readline()
    except OSError:
        return None

    if not first_line:
        return None
    try:
        payload = json.loads(first_line)
    except json.JSONDecodeError:
        return None
    if payload.get("type") != "session_meta":
        return None
    session_payload = payload.get("payload")
    return session_payload if isinstance(session_payload, dict) else None


def find_recent_session_files() -> list[Path]:
    if not SESSIONS_DIR.exists():
        return []
    files = [path for path in SESSIONS_DIR.rglob("*.jsonl") if path.is_file()]
    files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return files[:MAX_RECENT_TRANSCRIPTS]


def resolve_transcript_path(payload: dict[str, Any], cwd: Path) -> Path | None:
    session_id = find_recursive_key(payload, {"session_id", "sessionId", "id"})
    if session_id:
        direct = find_session_file_by_id(session_id)
        if direct:
            return direct

    candidates: list[Path] = []
    cwd_str = str(cwd.resolve())
    for path in find_recent_session_files():
        meta = read_session_meta(path)
        if not meta:
            continue
        if meta.get("cwd") == cwd_str:
            candidates.append(path)

    if not candidates:
        return None

    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[0]


def wait_for_stable_file(path: Path) -> None:
    previous_size = -1
    stable_rounds = 0
    for _ in range(8):
        try:
            current_size = path.stat().st_size
        except OSError:
            return
        if current_size == previous_size:
            stable_rounds += 1
            if stable_rounds >= 2:
                return
        else:
            stable_rounds = 0
        previous_size = current_size
        time.sleep(0.25)


def extract_message_text(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if not isinstance(content, list):
        return ""
    pieces: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            pieces.append(text)
    return "\n".join(pieces).strip()


def detect_repo_root(cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    root = result.stdout.strip()
    return root or None


def chunk_text_by_bytes(text: str, max_bytes: int) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_bytes = 0
    for line in text.splitlines(keepends=True):
        line_bytes = len(line.encode("utf-8"))
        if current and current_bytes + line_bytes > max_bytes:
            chunks.append("".join(current))
            current = []
            current_bytes = 0
        if line_bytes > max_bytes:
            encoded = line.encode("utf-8")
            start = 0
            while start < len(encoded):
                end = min(start + max_bytes, len(encoded))
                chunk = encoded[start:end].decode("utf-8", errors="ignore")
                if chunk:
                    chunks.append(chunk)
                start = end
            continue
        current.append(line)
        current_bytes += line_bytes
    if current:
        chunks.append("".join(current))
    return chunks


def build_snapshot(path: Path, settings: Settings, hook_event: str) -> Snapshot:
    wait_for_stable_file(path)
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    transcript_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    transcript_size = len(raw_text.encode("utf-8"))

    session_meta: dict[str, Any] = {}
    started_at: str | None = None
    last_event_at: str | None = None
    tool_names: set[str] = set()
    user_messages = 0
    assistant_messages = 0
    tool_calls = 0
    failed_tools = 0
    last_user_prompt: str | None = None
    last_assistant_message: str | None = None
    preferred_final_assistant: str | None = None

    for line in raw_text.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = entry.get("timestamp")
        if isinstance(timestamp, str):
            if started_at is None:
                started_at = timestamp
            last_event_at = timestamp

        entry_type = entry.get("type")
        payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}

        if entry_type == "session_meta":
            session_meta = payload
            continue

        if entry_type == "response_item":
            payload_type = payload.get("type")
            if payload_type == "message":
                role = payload.get("role")
                text = extract_message_text(payload)
                if role == "user":
                    user_messages += 1
                    if text:
                        last_user_prompt = text
                elif role == "assistant":
                    assistant_messages += 1
                    if text:
                        last_assistant_message = text
                        if payload.get("phase") == "final":
                            preferred_final_assistant = text
            elif payload_type == "function_call":
                tool_calls += 1
                name = payload.get("name")
                if isinstance(name, str) and name.strip():
                    tool_names.add(name.strip())
            continue

        if entry_type == "event_msg" and payload.get("type") == "exec_command_end":
            if payload.get("exit_code", 0) not in (0, None):
                failed_tools += 1

    session_id = str(session_meta.get("id") or path.stem)
    trace_id = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:32]
    repo_root = detect_repo_root(settings.cwd)
    cli_version = session_meta.get("cli_version") if isinstance(session_meta.get("cli_version"), str) else None
    source = session_meta.get("source") if isinstance(session_meta.get("source"), str) else None

    summary = {
        "session_id": session_id,
        "hook_event": hook_event,
        "cwd": str(settings.cwd),
        "repo_root": repo_root,
        "cli_version": cli_version,
        "source": source,
        "started_at": started_at,
        "last_event_at": last_event_at,
        "counts": {
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "tool_calls": tool_calls,
            "failed_tools": failed_tools,
            "raw_parts": 0,
        },
        "tool_names": sorted(tool_names),
        "last_user_prompt": last_user_prompt,
        "last_assistant_message": preferred_final_assistant or last_assistant_message,
    }
    summary = redact_object(summary, settings.redaction_mode)

    redacted_raw_text = redact_text(raw_text, settings.redaction_mode)
    raw_chunks = chunk_text_by_bytes(redacted_raw_text, settings.raw_chunk_bytes)
    summary["counts"]["raw_parts"] = len(raw_chunks)

    return Snapshot(
        session_id=session_id,
        trace_id=trace_id,
        transcript_path=path,
        transcript_sha256=transcript_sha256,
        transcript_size=transcript_size,
        hook_event=hook_event,
        cwd=settings.cwd,
        repo_root=repo_root,
        cli_version=cli_version,
        source=source,
        started_at=started_at,
        last_event_at=last_event_at,
        summary=summary,
        raw_chunks=raw_chunks,
        tool_names=sorted(tool_names),
    )


def build_snapshot_key(settings: Settings, snapshot: Snapshot) -> str:
    key_source = "|".join(
        [
            settings.public_key or "",
            settings.base_url or "",
            settings.logical_project or "",
            snapshot.session_id,
            snapshot.transcript_sha256,
        ]
    )
    return hashlib.sha256(key_source.encode("utf-8")).hexdigest()


def exported_marker_path(snapshot_key: str) -> Path:
    return EXPORTED_DIR / f"{snapshot_key}.json"


def spool_path(snapshot_key: str) -> Path:
    return SPOOL_DIR / f"{snapshot_key}.json"


def is_exported(snapshot_key: str) -> bool:
    return exported_marker_path(snapshot_key).is_file()


def mark_exported(snapshot_key: str, settings: Settings, snapshot: Snapshot) -> None:
    EXPORTED_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "snapshot_key": snapshot_key,
        "session_id": snapshot.session_id,
        "trace_id": snapshot.trace_id,
        "transcript_sha256": snapshot.transcript_sha256,
        "transcript_path": str(snapshot.transcript_path),
        "base_url": settings.base_url,
        "public_key": settings.public_key,
        "logical_project": settings.logical_project,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    exported_marker_path(snapshot_key).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def write_spool(snapshot_key: str, settings: Settings, snapshot: Snapshot, error: str) -> None:
    SPOOL_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "snapshot_key": snapshot_key,
        "session_id": snapshot.session_id,
        "transcript_path": str(snapshot.transcript_path),
        "cwd": str(snapshot.cwd),
        "override_path": str(settings.override_path) if settings.override_path else None,
        "hook_event": snapshot.hook_event,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "last_error": error,
    }
    spool_path(snapshot_key).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def export_snapshot(settings: Settings, snapshot: Snapshot) -> None:
    client = Langfuse(
        public_key=settings.public_key,
        secret_key=settings.secret_key,
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
        flush_at=1,
        flush_interval=0.25,
        tracing_enabled=True,
    )
    if not client.auth_check():
        raise RuntimeError("Langfuse auth_check returned false")

    span = client.start_span(
        trace_context={"trace_id": snapshot.trace_id},
        name="codex.session.export",
        input={
            "hook_event": snapshot.hook_event,
            "transcript_sha256": snapshot.transcript_sha256,
            "transcript_size": snapshot.transcript_size,
        },
        metadata=redact_object(
            {
                "cwd": str(snapshot.cwd),
                "repo_root": snapshot.repo_root,
                "hostname": socket.gethostname(),
                "transcript_path": str(snapshot.transcript_path),
                "transcript_sha256": snapshot.transcript_sha256,
                "transcript_size": snapshot.transcript_size,
                "raw_parts": len(snapshot.raw_chunks),
                "redaction_mode": settings.redaction_mode,
                "logical_project": settings.logical_project,
                "override_path": str(settings.override_path) if settings.override_path else None,
            },
            settings.redaction_mode,
        ),
    )

    trace_tags = unique_strings(
        settings.tags
        + [f"tool:{tool_name}" for tool_name in snapshot.tool_names]
        + ([f"cwd:{snapshot.cwd.name}"] if snapshot.cwd.name else [])
    )

    span.update_trace(
        name="codex.session",
        session_id=snapshot.session_id,
        user_id=settings.user_id,
        metadata=redact_object(
            {
                "cwd": str(snapshot.cwd),
                "repo_root": snapshot.repo_root,
                "cli_version": snapshot.cli_version,
                "source": snapshot.source,
                "started_at": snapshot.started_at,
                "last_event_at": snapshot.last_event_at,
                "logical_project": settings.logical_project,
                "transcript_path": str(snapshot.transcript_path),
                "transcript_sha256": snapshot.transcript_sha256,
                "hook_event": snapshot.hook_event,
            },
            settings.redaction_mode,
        ),
        tags=trace_tags,
    )

    span.create_event(
        name="codex.session.summary",
        output=snapshot.summary,
        metadata={"content_type": "application/json", "snapshot_sha256": snapshot.transcript_sha256},
    )

    total_parts = len(snapshot.raw_chunks)
    for index, chunk in enumerate(snapshot.raw_chunks, start=1):
        span.create_event(
            name=f"codex.raw_transcript.part_{index}",
            output=chunk,
            metadata={
                "part_index": index,
                "part_total": total_parts,
                "content_type": "application/x-ndjson",
                "snapshot_sha256": snapshot.transcript_sha256,
            },
        )

    span.update(
        output={
            "status": "exported",
            "session_id": snapshot.session_id,
            "snapshot_sha256": snapshot.transcript_sha256,
            "raw_parts": total_parts,
        }
    )
    span.end()
    client.flush()


def drain_spool() -> None:
    if not SPOOL_DIR.exists():
        return

    for path in sorted(SPOOL_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            log(f"spool-read-failed path={path} error={error}")
            continue

        snapshot_key = str(payload.get("snapshot_key") or "")
        if snapshot_key and is_exported(snapshot_key):
            path.unlink(missing_ok=True)
            continue

        transcript_path = Path(str(payload.get("transcript_path") or "")).expanduser()
        cwd = Path(str(payload.get("cwd") or "")).expanduser()
        if not transcript_path.is_file() or not cwd.exists():
            log(f"spool-missing-input path={path}")
            continue

        settings = resolve_settings(cwd)
        if not settings.enabled:
            continue

        try:
            snapshot = build_snapshot(transcript_path, settings, str(payload.get("hook_event") or "Stop"))
            snapshot_key = build_snapshot_key(settings, snapshot)
            if is_exported(snapshot_key):
                path.unlink(missing_ok=True)
                continue
            export_snapshot(settings, snapshot)
            mark_exported(snapshot_key, settings, snapshot)
            path.unlink(missing_ok=True)
            log(f"spool-exported session_id={snapshot.session_id} snapshot={snapshot_key}")
        except Exception as error:  # noqa: BLE001
            log(f"spool-export-failed path={path} error={error}")


def with_lock() -> contextlib.AbstractContextManager[None]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.touch(exist_ok=True)
    handle = LOCK_PATH.open("r+", encoding="utf-8")

    @contextlib.contextmanager
    def manager() -> Any:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    return manager()


def main() -> int:
    args = parse_args()
    raw_payload, hook_payload = read_hook_payload(args.hook_input_file)
    hook_event = infer_hook_event(hook_payload)
    cwd = Path(os.environ.get("PWD") or os.getcwd()).resolve()

    with with_lock():
        drain_spool()

        if hook_event != "Stop":
            log(f"hook-skip event={hook_event} cwd={cwd}")
            return 0

        settings = resolve_settings(cwd)
        if not settings.enabled:
            log(f"hook-disabled event={hook_event} cwd={cwd} override={settings.override_path}")
            return 0

        transcript_path = resolve_transcript_path(hook_payload, cwd)
        if transcript_path is None:
            log(
                "transcript-missing "
                f"event={hook_event} cwd={cwd} payload_keys={sorted(hook_payload.keys())} raw_bytes={len(raw_payload.encode('utf-8'))}"
            )
            return 0

        snapshot = build_snapshot(transcript_path, settings, hook_event)
        snapshot_key = build_snapshot_key(settings, snapshot)
        if is_exported(snapshot_key):
            log(f"snapshot-skip-duplicate session_id={snapshot.session_id} snapshot={snapshot_key}")
            return 0

        try:
            export_snapshot(settings, snapshot)
            mark_exported(snapshot_key, settings, snapshot)
            spool_path(snapshot_key).unlink(missing_ok=True)
            log(
                "snapshot-exported "
                f"session_id={snapshot.session_id} snapshot={snapshot_key} path={snapshot.transcript_path}"
            )
        except Exception as error:  # noqa: BLE001
            write_spool(snapshot_key, settings, snapshot, str(error))
            log(
                "snapshot-spooled "
                f"session_id={snapshot.session_id} snapshot={snapshot_key} path={snapshot.transcript_path} error={error}"
            )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # noqa: BLE001
        log(f"fatal-error error={error}")
        raise SystemExit(0)
