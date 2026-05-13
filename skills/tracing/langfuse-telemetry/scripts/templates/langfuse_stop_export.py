#!/usr/bin/env python3
"""Claude Code Stop hook: export full session transcript to Langfuse.

Adapted from the Codex langfuse_stop_export.py for Claude Code's session format.
Claude Code stores sessions as JSONL in ~/.claude/projects/<project>/<session-id>.jsonl
with event types: user, assistant, progress, system, file-history-snapshot, queue-operation.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import httpx
import json
import os
import re
import socket
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from langfuse import Langfuse

try:
    from langfuse.api.ingestion.types.create_event_body import CreateEventBody
    from langfuse.api.ingestion.types.create_generation_body import CreateGenerationBody
    from langfuse.api.ingestion.types.ingestion_event import (
        IngestionEvent_EventCreate,
        IngestionEvent_GenerationCreate,
        IngestionEvent_TraceCreate,
    )
    from langfuse.api.ingestion.types.trace_body import TraceBody
except ImportError:
    CreateEventBody = None
    CreateGenerationBody = None
    IngestionEvent_EventCreate = None
    IngestionEvent_GenerationCreate = None
    IngestionEvent_TraceCreate = None
    TraceBody = None


CLAUDE_HOME = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_HOME / "projects"
STATE_DIR = CLAUDE_HOME / "langfuse-export"
SPOOL_DIR = STATE_DIR / "spool"
EXPORTED_DIR = STATE_DIR / "exported"
HEALTH_DIR = STATE_DIR / "health"
LOG_PATH = CLAUDE_HOME / "log" / "langfuse-export.log"
LOCK_PATH = STATE_DIR / "hook.lock"
AGENTS_ENV_PATH = Path.home() / ".agents" / ".env"
OVERRIDE_FILENAMES = (".claude.env", ".env.local", ".env")
CLAUDE_CODE_PUBLIC_KEY_VARS = (
    "CLAUDE_CODE_LANGFUSE_PUBLIC_KEY",
    "CLAUDE_LANGFUSE_PUBLIC_KEY",
    "CC_LANGFUSE_PUBLIC_KEY",
)
CLAUDE_CODE_SECRET_KEY_VARS = (
    "CLAUDE_CODE_LANGFUSE_SECRET_KEY",
    "CLAUDE_LANGFUSE_SECRET_KEY",
    "CC_LANGFUSE_SECRET_KEY",
)
CLAUDE_CODE_BASE_URL_VARS = (
    "CLAUDE_CODE_LANGFUSE_BASE_URL",
    "CLAUDE_LANGFUSE_BASE_URL",
    "CC_LANGFUSE_BASE_URL",
)

DEFAULT_TIMEOUT_SECONDS = 6
DEFAULT_RETRY_BACKOFF_SECONDS = 15
DEFAULT_RAW_CHUNK_BYTES = 180_000
MAX_RECENT_TRANSCRIPTS = 120
MAX_RETRY_BACKOFF_SECONDS = 600
MAX_SPOOL_AGE_DAYS = 7
MAX_EXPORTED_MARKERS = 500

SECRET_VALUE_PATTERNS = (
    re.compile(r"(?im)\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD))\s*=\s*([^\s\"']+|\"[^\"]*\"|'[^']*')"),
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)([A-Za-z0-9._\-+/=]+)"),
    re.compile(r"(?i)\b(sk|pk)-[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
)
RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
RETRYABLE_ERROR_MARKERS = (
    "cannot send a request, as the client has been closed",
    "connection reset", "connection refused", "internal server error",
    "remote protocol error", "server disconnected", "temporarily unavailable",
    "timed out", "timeout",
)

MODEL_PRICING_PER_TOKEN = {
    "claude-opus-4-6": {"input": 15.0 / 1_000_000, "cached_input": 1.50 / 1_000_000, "output": 75.0 / 1_000_000},
    "claude-sonnet-4-6": {"input": 3.0 / 1_000_000, "cached_input": 0.30 / 1_000_000, "output": 15.0 / 1_000_000},
    "claude-haiku-4-5-20251001": {"input": 0.80 / 1_000_000, "cached_input": 0.08 / 1_000_000, "output": 4.0 / 1_000_000},
    "claude-sonnet-4-5-20250514": {"input": 3.0 / 1_000_000, "cached_input": 0.30 / 1_000_000, "output": 15.0 / 1_000_000},
    "claude-opus-4-0-20250514": {"input": 15.0 / 1_000_000, "cached_input": 1.50 / 1_000_000, "output": 75.0 / 1_000_000},
}
MAX_INGESTION_BATCH_BYTES = 3_000_000


@dataclass
class Settings:
    enabled: bool
    public_key: str | None
    secret_key: str | None
    base_url: str | None
    tags: list[str]
    user_id: str | None
    redaction_mode: str
    raw_chunk_bytes: int
    timeout_seconds: int
    retry_backoff_seconds: int
    cwd: Path


@dataclass
class TurnSnapshot:
    turn_index: int
    model: str | None
    started_at: str | None
    ended_at: str | None
    input_text: str | None
    output_text: str | None
    raw_usage: dict[str, int] | None
    tool_names: list[str] = field(default_factory=list)


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
    model: str | None
    started_at: str | None
    last_event_at: str | None
    summary: dict[str, Any]
    raw_chunks: list[str]
    tool_names: list[str]
    turns: list[TurnSnapshot]


@dataclass
class HealthState:
    consecutive_failures: int
    last_error: str | None
    last_failure_at: str | None
    retry_at: str | None
    retry_at_epoch: float


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", nargs="?", choices=["cc"])
    parser.add_argument("--hook-input-file", type=Path, required=True)
    return parser.parse_args()


def parse_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
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


def first_env_value(env: dict[str, str], names: tuple[str, ...]) -> str | None:
    for name in names:
        value = env.get(name)
        if value:
            return value
    return None


def find_nearest_override(cwd: Path) -> Path | None:
    current = cwd.resolve()
    for directory in [current, *current.parents]:
        for filename in OVERRIDE_FILENAMES:
            candidate = directory / filename
            if candidate.is_file():
                return candidate
    return None


def resolve_settings(cwd: Path, profile: str | None = None) -> Settings:
    global_env = load_env_file(AGENTS_ENV_PATH)
    process_env = {key: value for key, value in os.environ.items() if isinstance(value, str)}
    local_env = load_non_empty_env_file(find_nearest_override(cwd))
    merged: dict[str, str] = {}
    merged.update(global_env)
    merged.update(process_env)
    merged.update(local_env)

    if profile == "cc":
        cc_env = {**global_env, **process_env, **local_env}
        public_key = first_env_value(local_env, ("LANGFUSE_PUBLIC_KEY",))
        if public_key:
            merged["LANGFUSE_PUBLIC_KEY"] = public_key
        else:
            public_key = first_env_value(cc_env, CLAUDE_CODE_PUBLIC_KEY_VARS)
            if public_key:
                merged["LANGFUSE_PUBLIC_KEY"] = public_key
            else:
                merged.pop("LANGFUSE_PUBLIC_KEY", None)

        secret_key = first_env_value(local_env, ("LANGFUSE_SECRET_KEY",))
        if secret_key:
            merged["LANGFUSE_SECRET_KEY"] = secret_key
        else:
            secret_key = first_env_value(cc_env, CLAUDE_CODE_SECRET_KEY_VARS)
            if secret_key:
                merged["LANGFUSE_SECRET_KEY"] = secret_key
            else:
                merged.pop("LANGFUSE_SECRET_KEY", None)

        if not first_env_value(local_env, ("LANGFUSE_BASE_URL", "LANGFUSE_HOST")):
            base_url = first_env_value(cc_env, CLAUDE_CODE_BASE_URL_VARS)
            if base_url:
                merged["LANGFUSE_BASE_URL"] = base_url

    enabled = parse_bool(
        merged.get(
            "CLAUDE_CODE_LANGFUSE_ENABLED",
            merged.get("CLAUDE_LANGFUSE_ENABLED", merged.get("CODEX_LANGFUSE_ENABLED")),
        ),
        True,
    )
    public_key = merged.get("LANGFUSE_PUBLIC_KEY")
    secret_key = merged.get("LANGFUSE_SECRET_KEY")
    base_url = merged.get("LANGFUSE_BASE_URL") or merged.get("LANGFUSE_HOST")
    tags = unique_strings(
        ["claude-code", "stop-hook"]
        + merged.get("CLAUDE_LANGFUSE_TAGS", "").split(",")
    )
    user_id = merged.get("CLAUDE_LANGFUSE_USER_ID") or os.environ.get("USER")
    redaction_mode = (merged.get("CLAUDE_LANGFUSE_REDACTION_MODE") or "basic").strip().lower()
    raw_chunk_bytes = parse_int(
        merged.get("CLAUDE_LANGFUSE_RAW_CHUNK_BYTES"),
        default=DEFAULT_RAW_CHUNK_BYTES, minimum=10_000, maximum=800_000,
    )
    timeout_seconds = parse_int(
        merged.get("CLAUDE_LANGFUSE_TIMEOUT_SECONDS"),
        default=DEFAULT_TIMEOUT_SECONDS, minimum=1, maximum=20,
    )
    retry_backoff_seconds = parse_int(
        merged.get("CLAUDE_LANGFUSE_RETRY_BACKOFF_SECONDS"),
        default=DEFAULT_RETRY_BACKOFF_SECONDS, minimum=5, maximum=MAX_RETRY_BACKOFF_SECONDS,
    )

    if not enabled or not public_key or not secret_key or not base_url:
        enabled = False

    return Settings(
        enabled=enabled,
        public_key=public_key,
        secret_key=secret_key,
        base_url=base_url,
        tags=tags,
        user_id=user_id,
        redaction_mode=redaction_mode,
        raw_chunk_bytes=raw_chunk_bytes,
        timeout_seconds=timeout_seconds,
        retry_backoff_seconds=retry_backoff_seconds,
        cwd=cwd.resolve(),
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


def find_session_file(session_id: str) -> Path | None:
    """Find session JSONL by session ID across all project dirs."""
    if not PROJECTS_DIR.exists():
        return None
    target = f"{session_id}.jsonl"
    matches: list[Path] = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        candidate = project_dir / target
        if candidate.is_file():
            matches.append(candidate)
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def find_recent_session_files() -> list[Path]:
    """Find recent session JSONL files across all project dirs."""
    if not PROJECTS_DIR.exists():
        return []
    files: list[Path] = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        for f in project_dir.glob("*.jsonl"):
            if f.is_file() and not f.parent.name == "subagents":
                files.append(f)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:MAX_RECENT_TRANSCRIPTS]


def resolve_transcript_path(payload: dict[str, Any]) -> Path | None:
    """Resolve session transcript path from hook payload."""
    session_id = (
        payload.get("session_id")
        or payload.get("sessionId")
        or payload.get("id")
    )
    if session_id:
        direct = find_session_file(session_id)
        if direct:
            return direct

    # Fallback: most recently modified session file
    recent = find_recent_session_files()
    return recent[0] if recent else None


def extract_content_text(content: Any) -> str:
    """Extract text from Claude Code message content (string or list of blocks)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        pieces: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            block_type = item.get("type", "")
            if block_type == "text":
                text = item.get("text", "")
                if isinstance(text, str) and text.strip():
                    pieces.append(text.strip())
            elif block_type == "tool_use":
                name = item.get("name", "unknown")
                pieces.append(f"[tool_use: {name}]")
            elif block_type == "tool_result":
                pieces.append("[tool_result]")
        return "\n".join(pieces)
    return ""


def detect_repo_root(cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True, capture_output=True, text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


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


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def stable_identifier(*parts: str, length: int = 32) -> str:
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def canonical_model_name(model: str | None) -> str | None:
    if not model:
        return None
    normalized = model.strip().lower()
    for candidate in sorted(MODEL_PRICING_PER_TOKEN, key=len, reverse=True):
        if normalized == candidate or normalized.startswith(f"{candidate}-") or normalized.startswith(f"{candidate}["):
            return candidate
    return None


def normalize_usage(raw_usage: dict[str, Any]) -> tuple[dict[str, int], dict[str, Any]]:
    input_tokens = int(raw_usage.get("input_tokens") or 0)
    cache_creation = int(raw_usage.get("cache_creation_input_tokens") or 0)
    cache_read = int(raw_usage.get("cache_read_input_tokens") or 0)
    output_tokens = int(raw_usage.get("output_tokens") or 0)
    total = input_tokens + output_tokens

    normalized = {
        "input_tokens": input_tokens,
        "cached_input_tokens": cache_creation + cache_read,
        "output_tokens": output_tokens,
        "total_tokens": total,
    }
    usage_details: dict[str, Any] = {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": total,
    }
    if cache_creation + cache_read > 0:
        usage_details["prompt_tokens_details"] = {
            "cached_tokens": cache_creation + cache_read,
            "cache_creation_tokens": cache_creation,
            "cache_read_tokens": cache_read,
        }
    return normalized, usage_details


def infer_cost(model: str | None, raw_usage: dict[str, int] | None) -> dict[str, float] | None:
    canonical = canonical_model_name(model)
    if canonical is None or raw_usage is None:
        return None
    pricing = MODEL_PRICING_PER_TOKEN.get(canonical)
    if pricing is None:
        return None

    input_tokens = max(0, raw_usage.get("input_tokens", 0))
    cached_input = max(0, raw_usage.get("cached_input_tokens", 0))
    non_cached = max(0, input_tokens - cached_input)
    output_tokens = max(0, raw_usage.get("output_tokens", 0))

    input_cost = 0.0
    if non_cached > 0 and pricing.get("input") is not None:
        input_cost += non_cached * float(pricing["input"])
    if cached_input > 0 and pricing.get("cached_input") is not None:
        input_cost += cached_input * float(pricing["cached_input"])

    output_cost = output_tokens * float(pricing.get("output", 0)) if output_tokens > 0 else 0.0
    total_cost = input_cost + output_cost
    return {"input": input_cost, "output": output_cost, "total": total_cost} if total_cost > 0 else None


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


def build_snapshot(path: Path, settings: Settings, hook_event: str) -> Snapshot:
    """Parse a Claude Code session JSONL file into a Snapshot."""
    wait_for_stable_file(path)
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    transcript_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    transcript_size = len(raw_text.encode("utf-8"))

    session_id = path.stem
    started_at: str | None = None
    last_event_at: str | None = None
    all_tool_names: set[str] = set()
    user_messages = 0
    assistant_messages = 0
    tool_calls = 0
    last_user_prompt: str | None = None
    last_assistant_text: str | None = None
    session_model: str | None = None
    cli_version: str | None = None
    cwd_from_session: str | None = None
    turns: list[TurnSnapshot] = []

    # A "turn" in Claude Code = one user message + following assistant messages
    current_turn_input: str | None = None
    current_turn_output: str | None = None
    current_turn_model: str | None = None
    current_turn_start: str | None = None
    current_turn_end: str | None = None
    current_turn_usage: dict[str, int] | None = None
    current_turn_tools: list[str] = []
    turn_index = 0

    def flush_turn() -> None:
        nonlocal current_turn_input, current_turn_output, current_turn_model
        nonlocal current_turn_start, current_turn_end, current_turn_usage, current_turn_tools
        nonlocal turn_index
        if current_turn_input or current_turn_output:
            turns.append(TurnSnapshot(
                turn_index=turn_index,
                model=current_turn_model,
                started_at=current_turn_start,
                ended_at=current_turn_end,
                input_text=current_turn_input,
                output_text=current_turn_output,
                raw_usage=current_turn_usage,
                tool_names=list(current_turn_tools),
            ))
            turn_index += 1
        current_turn_input = None
        current_turn_output = None
        current_turn_model = None
        current_turn_start = None
        current_turn_end = None
        current_turn_usage = None
        current_turn_tools = []

    for line in raw_text.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        entry_type = entry.get("type")
        timestamp = entry.get("timestamp")
        if isinstance(timestamp, str):
            if started_at is None:
                started_at = timestamp
            last_event_at = timestamp

        if entry_type == "user":
            # New user message = start of new turn
            flush_turn()
            msg = entry.get("message", {})
            content = msg.get("content", "")
            text = extract_content_text(content)
            if text:
                user_messages += 1
                last_user_prompt = text
                current_turn_input = text
                current_turn_start = timestamp

            # Extract session metadata from user entries
            if not cli_version:
                cli_version = entry.get("version")
            if not cwd_from_session:
                cwd_from_session = entry.get("cwd")
            sid = entry.get("sessionId")
            if sid:
                session_id = sid

        elif entry_type == "assistant":
            msg = entry.get("message", {})
            content = msg.get("content", [])
            model = msg.get("model")
            usage = msg.get("usage")

            if model:
                session_model = model
                current_turn_model = model

            text = extract_content_text(content)
            if text:
                assistant_messages += 1
                last_assistant_text = text
                current_turn_output = text
                current_turn_end = timestamp

            # Extract tool_use from content blocks
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "")
                        if name:
                            all_tool_names.add(name)
                            current_turn_tools.append(name)
                            tool_calls += 1

            # Accumulate usage from this assistant response
            if isinstance(usage, dict):
                if current_turn_usage is None:
                    current_turn_usage = {}
                for uk in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
                    current_turn_usage[uk] = current_turn_usage.get(uk, 0) + int(usage.get(uk) or 0)

        elif entry_type == "progress":
            # Tool use progress events
            if isinstance(timestamp, str):
                current_turn_end = timestamp

    # Flush last turn
    flush_turn()

    trace_id = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:32]
    repo_root = detect_repo_root(settings.cwd)

    summary = {
        "session_id": session_id,
        "hook_event": hook_event,
        "cwd": cwd_from_session or str(settings.cwd),
        "repo_root": repo_root,
        "cli_version": cli_version,
        "started_at": started_at,
        "last_event_at": last_event_at,
        "counts": {
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "tool_calls": tool_calls,
            "turns": len(turns),
            "raw_parts": 0,
        },
        "model": session_model,
        "tool_names": sorted(all_tool_names),
        "last_user_prompt": last_user_prompt,
        "last_assistant_message": last_assistant_text,
    }
    summary = redact_object(summary, settings.redaction_mode)

    redacted_raw = redact_text(raw_text, settings.redaction_mode)
    raw_chunks = chunk_text_by_bytes(redacted_raw, settings.raw_chunk_bytes)
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
        model=session_model,
        started_at=started_at,
        last_event_at=last_event_at,
        summary=summary,
        raw_chunks=raw_chunks,
        tool_names=sorted(all_tool_names),
        turns=turns,
    )


# ── Langfuse export ──────────────────────────────────────────────────────────

def snapshot_key(settings: Settings, snapshot: Snapshot) -> str:
    basis = "|".join([
        settings.public_key or "", settings.base_url or "",
        snapshot.session_id, snapshot.transcript_sha256,
    ])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def exported_marker_path(key: str) -> Path:
    return EXPORTED_DIR / f"{key}.json"


def spool_path_for(key: str) -> Path:
    return SPOOL_DIR / f"{key}.json"


def is_exported(key: str) -> bool:
    return exported_marker_path(key).is_file()


def mark_exported(key: str, settings: Settings, snapshot: Snapshot) -> None:
    EXPORTED_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "snapshot_key": key,
        "session_id": snapshot.session_id,
        "trace_id": snapshot.trace_id,
        "transcript_sha256": snapshot.transcript_sha256,
        "base_url": settings.base_url,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    exported_marker_path(key).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def target_fingerprint(settings: Settings) -> str:
    basis = "|".join([settings.base_url or "", settings.public_key or ""])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def health_path(settings: Settings) -> Path:
    return HEALTH_DIR / f"{target_fingerprint(settings)}.json"


def load_health_state(settings: Settings) -> HealthState | None:
    path = health_path(settings)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    try:
        epoch = float(data.get("retry_at_epoch") or 0)
    except (TypeError, ValueError):
        epoch = 0.0
    return HealthState(
        consecutive_failures=int(data.get("consecutive_failures") or 0),
        last_error=str(data.get("last_error") or "") or None,
        last_failure_at=str(data.get("last_failure_at") or "") or None,
        retry_at=str(data.get("retry_at") or "") or None,
        retry_at_epoch=epoch,
    )


def save_health_state(settings: Settings, state: HealthState) -> None:
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "consecutive_failures": state.consecutive_failures,
        "last_error": state.last_error,
        "last_failure_at": state.last_failure_at,
        "retry_at": state.retry_at,
        "retry_at_epoch": state.retry_at_epoch,
    }
    health_path(settings).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def clear_health_state(settings: Settings) -> None:
    health_path(settings).unlink(missing_ok=True)


def should_defer(settings: Settings) -> HealthState | None:
    state = load_health_state(settings)
    if state is None or state.retry_at_epoch <= time.time():
        return None
    return state


def mark_unhealthy(settings: Settings, error: BaseException | str) -> HealthState:
    now = datetime.now(timezone.utc)
    current = load_health_state(settings)
    failures = (current.consecutive_failures if current else 0) + 1
    # Exponential backoff: base * 2^(failures-1), capped at MAX
    backoff = min(settings.retry_backoff_seconds * (2 ** (failures - 1)), MAX_RETRY_BACKOFF_SECONDS)
    retry_epoch = time.time() + backoff
    state = HealthState(
        consecutive_failures=failures,
        last_error=str(error),
        last_failure_at=now.isoformat(),
        retry_at=datetime.fromtimestamp(retry_epoch, tz=timezone.utc).isoformat(),
        retry_at_epoch=retry_epoch,
    )
    save_health_state(settings, state)
    return state


def is_retryable(error: BaseException) -> bool:
    if isinstance(error, (
        httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError,
        httpx.ReadTimeout, httpx.TimeoutException, httpx.TransportError,
    )):
        return True
    status = getattr(error, "status_code", None) or getattr(
        getattr(error, "response", None), "status_code", None
    )
    if isinstance(status, int) and (status in RETRYABLE_STATUS_CODES or status >= 500):
        return True
    msg = str(error).lower()
    return any(m in msg for m in RETRYABLE_ERROR_MARKERS)


def write_spool(key: str, settings: Settings, snapshot: Snapshot, error: str) -> None:
    SPOOL_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    existing: dict[str, Any] = {}
    sp = spool_path_for(key)
    if sp.is_file():
        try:
            existing = json.loads(sp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    attempt = int(existing.get("attempt_count") or 0) + 1
    payload = {
        "snapshot_key": key, "session_id": snapshot.session_id,
        "transcript_path": str(snapshot.transcript_path),
        "cwd": str(snapshot.cwd), "hook_event": snapshot.hook_event,
        "queued_at": existing.get("queued_at") or now,
        "last_attempt_at": now, "attempt_count": attempt,
        "last_error": error, "base_url": settings.base_url,
    }
    # Atomic write: write to temp file then rename
    tmp = sp.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    tmp.rename(sp)


def serialize_event(event: Any) -> str:
    dump = getattr(event, "model_dump_json", None)
    if callable(dump):
        return dump(exclude_none=True)
    j = getattr(event, "json", None)
    if callable(j):
        try:
            return j(exclude_none=True)
        except TypeError:
            return j()
    return json.dumps(event, default=str, sort_keys=True)


def build_batches(events: list[Any], max_bytes: int = MAX_INGESTION_BATCH_BYTES) -> list[list[Any]]:
    batches: list[list[Any]] = []
    current: list[Any] = []
    current_size = 0
    for event in events:
        size = len(serialize_event(event).encode("utf-8"))
        if current and current_size + size > max_bytes:
            batches.append(current)
            current = []
            current_size = 0
        current.append(event)
        current_size += size
    if current:
        batches.append(current)
    return batches


def supports_ingestion_api(client: Langfuse) -> bool:
    if any(s is None for s in (
        CreateEventBody, CreateGenerationBody, IngestionEvent_EventCreate,
        IngestionEvent_GenerationCreate, IngestionEvent_TraceCreate, TraceBody,
    )):
        return False
    ingestion = getattr(getattr(client, "api", None), "ingestion", None)
    return callable(getattr(ingestion, "batch", None))


def export_with_ingestion(client: Langfuse, settings: Settings, snapshot: Snapshot) -> None:
    trace_tags = unique_strings(
        settings.tags
        + [f"tool:{t}" for t in snapshot.tool_names]
        + ([f"cwd:{snapshot.cwd.name}"] if snapshot.cwd.name else [])
    )
    trace_ts = parse_timestamp(snapshot.started_at) or datetime.now(timezone.utc)
    summary_ts = parse_timestamp(snapshot.last_event_at) or trace_ts
    trace_meta = redact_object({
        "cwd": str(snapshot.cwd),
        "repo_root": snapshot.repo_root,
        "cli_version": snapshot.cli_version,
        "started_at": snapshot.started_at,
        "last_event_at": snapshot.last_event_at,
        "transcript_path": str(snapshot.transcript_path),
        "transcript_sha256": snapshot.transcript_sha256,
        "hostname": socket.gethostname(),
        "transcript_size": snapshot.transcript_size,
        "raw_parts": len(snapshot.raw_chunks),
        "redaction_mode": settings.redaction_mode,
        "hook_event": snapshot.hook_event,
        "model": snapshot.model,
    }, settings.redaction_mode)

    events: list[Any] = [
        IngestionEvent_TraceCreate(
            id=stable_identifier(snapshot.trace_id, "trace-event"),
            timestamp=trace_ts.isoformat(),
            body=TraceBody(
                id=snapshot.trace_id,
                timestamp=trace_ts,
                name="claude-code.session",
                session_id=snapshot.session_id,
                user_id=settings.user_id,
                input={
                    "hook_event": snapshot.hook_event,
                    "transcript_sha256": snapshot.transcript_sha256,
                    "transcript_size": snapshot.transcript_size,
                },
                metadata=trace_meta,
                tags=trace_tags,
                environment="default",
            ),
        )
    ]

    for turn in snapshot.turns:
        if not any([turn.input_text, turn.output_text, turn.raw_usage]):
            continue

        model = turn.model or snapshot.model
        turn_start = parse_timestamp(turn.started_at) or trace_ts
        turn_end = parse_timestamp(turn.ended_at) or turn_start

        gen_kwargs: dict[str, Any] = {
            "id": stable_identifier(snapshot.trace_id, "generation-body", str(turn.turn_index)),
            "trace_id": snapshot.trace_id,
            "name": "claude-code.turn",
            "start_time": turn_start,
            "end_time": turn_end,
            "input": redact_object(turn.input_text, settings.redaction_mode),
            "output": redact_object(turn.output_text, settings.redaction_mode),
            "metadata": redact_object({
                "source": "claude-code.stop-hook",
                "turn_index": turn.turn_index,
                "tool_names": turn.tool_names,
                "raw_usage": turn.raw_usage,
            }, settings.redaction_mode),
            "environment": "default",
        }
        if model:
            gen_kwargs["model"] = model
        if turn.raw_usage:
            norm, details = normalize_usage(turn.raw_usage)
            gen_kwargs["usage"] = {
                "promptTokens": details.get("prompt_tokens", 0),
                "completionTokens": details.get("completion_tokens", 0),
                "totalTokens": details.get("total_tokens", 0),
            }
            gen_kwargs["usage_details"] = details
            cost = infer_cost(model, norm)
            if cost:
                gen_kwargs["cost_details"] = cost

        events.append(
            IngestionEvent_GenerationCreate(
                id=stable_identifier(snapshot.trace_id, "generation-event", str(turn.turn_index)),
                timestamp=turn_end.isoformat(),
                body=CreateGenerationBody(**gen_kwargs),
            )
        )

    # Summary event
    events.append(
        IngestionEvent_EventCreate(
            id=stable_identifier(snapshot.trace_id, "summary-event"),
            timestamp=summary_ts.isoformat(),
            body=CreateEventBody(
                id=stable_identifier(snapshot.trace_id, "summary-body"),
                trace_id=snapshot.trace_id,
                name="claude-code.session.summary",
                start_time=summary_ts,
                output=snapshot.summary,
                metadata={"content_type": "application/json"},
                environment="default",
            ),
        )
    )

    # Raw transcript chunks
    total_parts = len(snapshot.raw_chunks)
    for idx, chunk in enumerate(snapshot.raw_chunks, start=1):
        events.append(
            IngestionEvent_EventCreate(
                id=stable_identifier(snapshot.trace_id, "raw-part-event", str(idx)),
                timestamp=summary_ts.isoformat(),
                body=CreateEventBody(
                    id=stable_identifier(snapshot.trace_id, "raw-part-body", str(idx)),
                    trace_id=snapshot.trace_id,
                    name=f"claude-code.raw_transcript.part_{idx}",
                    start_time=summary_ts,
                    output=chunk,
                    metadata={
                        "part_index": idx, "part_total": total_parts,
                        "content_type": "application/x-ndjson",
                    },
                    environment="default",
                ),
            )
        )

    for batch in build_batches(events):
        response = client.api.ingestion.batch(
            batch=batch,
            metadata={"sdk": "claude-code-stop-hook", "snapshot_sha256": snapshot.transcript_sha256},
        )
        if getattr(response, "errors", None):
            raise RuntimeError(f"Langfuse ingestion errors: {response.errors}")


def export_with_legacy(client: Langfuse, settings: Settings, snapshot: Snapshot) -> None:
    """Fallback using legacy tracing API."""
    trace_tags = unique_strings(
        settings.tags
        + [f"tool:{t}" for t in snapshot.tool_names]
        + ([f"cwd:{snapshot.cwd.name}"] if snapshot.cwd.name else [])
    )
    meta = redact_object({
        "cwd": str(snapshot.cwd), "repo_root": snapshot.repo_root,
        "hostname": socket.gethostname(), "transcript_path": str(snapshot.transcript_path),
        "transcript_sha256": snapshot.transcript_sha256, "model": snapshot.model,
    }, settings.redaction_mode)

    trace = client.trace(
        id=snapshot.trace_id,
        name="claude-code.session",
        session_id=snapshot.session_id,
        user_id=settings.user_id,
        metadata=meta,
        tags=trace_tags,
        input={"hook_event": snapshot.hook_event, "transcript_size": snapshot.transcript_size},
    )

    trace.event(name="claude-code.session.summary", output=snapshot.summary)

    for idx, chunk in enumerate(snapshot.raw_chunks, start=1):
        trace.event(
            name=f"claude-code.raw_transcript.part_{idx}",
            output=chunk,
            metadata={"part_index": idx, "part_total": len(snapshot.raw_chunks)},
        )

    for turn in snapshot.turns:
        if not any([turn.input_text, turn.output_text]):
            continue
        gen_kwargs: dict[str, Any] = {
            "name": "claude-code.turn",
            "input": redact_object(turn.input_text, settings.redaction_mode),
            "output": redact_object(turn.output_text, settings.redaction_mode),
        }
        if turn.model:
            gen_kwargs["model"] = turn.model
        if turn.raw_usage:
            norm, details = normalize_usage(turn.raw_usage)
            gen_kwargs["usage"] = details
        trace.generation(**gen_kwargs)

    client.flush()


def export_snapshot(settings: Settings, snapshot: Snapshot) -> None:
    client_kwargs: dict[str, Any] = {
        "public_key": settings.public_key,
        "secret_key": settings.secret_key,
        "host": settings.base_url,
        "timeout": settings.timeout_seconds,
        "flush_at": 1,
        "flush_interval": 0.25,
    }
    client: Langfuse | None = None
    try:
        client = Langfuse(**client_kwargs)
        if not client.auth_check():
            raise RuntimeError("Langfuse auth_check failed")
        if supports_ingestion_api(client):
            export_with_ingestion(client, settings, snapshot)
        else:
            export_with_legacy(client, settings, snapshot)
    finally:
        if client is not None:
            with contextlib.suppress(Exception):
                client.shutdown()


def prune_old_spool_entries() -> None:
    """Remove spool entries older than MAX_SPOOL_AGE_DAYS."""
    if not SPOOL_DIR.exists():
        return
    cutoff = time.time() - (MAX_SPOOL_AGE_DAYS * 86400)
    for path in SPOOL_DIR.glob("*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                log(f"spool-pruned-stale path={path.name}")
                path.unlink(missing_ok=True)
        except OSError:
            pass


def prune_exported_markers() -> None:
    """Keep only the most recent MAX_EXPORTED_MARKERS to prevent unbounded growth."""
    if not EXPORTED_DIR.exists():
        return
    markers = sorted(EXPORTED_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    excess = len(markers) - MAX_EXPORTED_MARKERS
    if excess > 0:
        for path in markers[:excess]:
            path.unlink(missing_ok=True)


def drain_spool(settings: Settings) -> None:
    prune_old_spool_entries()
    prune_exported_markers()
    if not SPOOL_DIR.exists():
        return
    for path in sorted(SPOOL_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sk = str(data.get("snapshot_key") or "")
        if sk and is_exported(sk):
            path.unlink(missing_ok=True)
            continue
        transcript = Path(str(data.get("transcript_path") or ""))
        if not transcript.is_file():
            continue
        deferred = should_defer(settings)
        if deferred is not None:
            continue
        try:
            snap = build_snapshot(transcript, settings, str(data.get("hook_event") or "Stop"))
            sk = snapshot_key(settings, snap)
            if is_exported(sk):
                path.unlink(missing_ok=True)
                continue
            export_snapshot(settings, snap)
            clear_health_state(settings)
            mark_exported(sk, settings, snap)
            path.unlink(missing_ok=True)
            log(f"spool-exported session_id={snap.session_id}")
        except Exception as e:
            if is_retryable(e):
                mark_unhealthy(settings, e)
            log(f"spool-retry-failed error={e}")


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
    cwd = Path(os.environ.get("PWD") or os.getcwd()).resolve()

    with with_lock():
        settings = resolve_settings(cwd, args.profile)
        if not settings.enabled:
            log(f"hook-disabled cwd={cwd}")
            return 0

        drain_spool(settings)

        transcript_path = resolve_transcript_path(hook_payload)
        if transcript_path is None:
            # Fallback: find by most recent file
            recent = find_recent_session_files()
            if recent:
                transcript_path = recent[0]

        if transcript_path is None:
            log(f"transcript-missing cwd={cwd} keys={sorted(hook_payload.keys())}")
            return 0

        snapshot = build_snapshot(transcript_path, settings, "Stop")
        sk = snapshot_key(settings, snapshot)
        if is_exported(sk):
            log(f"skip-duplicate session_id={snapshot.session_id}")
            return 0

        deferred = should_defer(settings)
        if deferred is not None:
            write_spool(sk, settings, snapshot, f"Deferred until {deferred.retry_at}")
            log(f"snapshot-buffered session_id={snapshot.session_id}")
            return 0

        try:
            export_snapshot(settings, snapshot)
            clear_health_state(settings)
            mark_exported(sk, settings, snapshot)
            spool_path_for(sk).unlink(missing_ok=True)
            log(f"snapshot-exported session_id={snapshot.session_id} path={snapshot.transcript_path}")
        except Exception as error:
            write_spool(sk, settings, snapshot, str(error))
            if is_retryable(error):
                state = mark_unhealthy(settings, error)
                log(f"snapshot-buffered session_id={snapshot.session_id} retry_at={state.retry_at} error={error}")
            else:
                log(f"snapshot-spooled session_id={snapshot.session_id} error={error}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        log(f"fatal-error error={error}")
        raise SystemExit(0)
