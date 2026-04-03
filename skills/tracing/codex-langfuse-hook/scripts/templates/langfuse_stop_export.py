#!/usr/bin/env python3
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from langfuse import Langfuse
try:
    from langfuse import propagate_attributes
except ImportError:  # pragma: no cover
    propagate_attributes = None
try:
    from langfuse.api.ingestion.types.create_event_body import CreateEventBody
    from langfuse.api.ingestion.types.create_generation_body import CreateGenerationBody
    from langfuse.api.ingestion.types.ingestion_event import (
        IngestionEvent_EventCreate,
        IngestionEvent_GenerationCreate,
        IngestionEvent_TraceCreate,
    )
    from langfuse.api.ingestion.types.trace_body import TraceBody
except ImportError:  # pragma: no cover
    CreateEventBody = None
    CreateGenerationBody = None
    IngestionEvent_EventCreate = None
    IngestionEvent_GenerationCreate = None
    IngestionEvent_TraceCreate = None
    TraceBody = None


CODEX_HOME = Path.home() / ".codex"
SESSIONS_DIR = CODEX_HOME / "sessions"
STATE_DIR = CODEX_HOME / "langfuse-export"
SPOOL_DIR = STATE_DIR / "spool"
EXPORTED_DIR = STATE_DIR / "exported"
HEALTH_DIR = STATE_DIR / "health"
LOG_PATH = CODEX_HOME / "log" / "langfuse-export.log"
LOCK_PATH = STATE_DIR / "hook.lock"

OVERRIDE_FILENAMES = (".codex.env", ".env.local", ".env")
PROJECT_ENV_PATH_VAR = "CODEX_LANGFUSE_PROJECT_ENV_PATH"
DEFAULT_TIMEOUT_SECONDS = 4
DEFAULT_RETRY_BACKOFF_SECONDS = 15
DEFAULT_RAW_CHUNK_BYTES = 180_000
MAX_RECENT_TRANSCRIPTS = 120
MAX_RETRY_BACKOFF_SECONDS = 300

SECRET_VALUE_PATTERNS = (
    re.compile(r"(?im)\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD))\s*=\s*([^\s\"']+|\"[^\"]*\"|'[^']*')"),
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)([A-Za-z0-9._\-+/=]+)"),
    re.compile(r"(?i)\b(sk|pk)-[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
)
INSECURE_TLS_ENV_VAR = "CODEX_LANGFUSE_INSECURE_TLS"
RETRY_BACKOFF_ENV_VAR = "CODEX_LANGFUSE_RETRY_BACKOFF_SECONDS"
RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
RETRYABLE_ERROR_MARKERS = (
    "cannot send a request, as the client has been closed",
    "connection reset",
    "connection refused",
    "internal server error",
    "remote protocol error",
    "server disconnected",
    "temporarily unavailable",
    "timed out",
    "timeout",
)
MODEL_PRICING_PER_TOKEN = {
    "gpt-5.4": {"input": 2.50 / 1_000_000, "cached_input": 0.25 / 1_000_000, "output": 15.0 / 1_000_000},
    "gpt-5.4-mini": {"input": 0.75 / 1_000_000, "cached_input": 0.075 / 1_000_000, "output": 4.50 / 1_000_000},
    "gpt-5.4-nano": {"input": 0.20 / 1_000_000, "cached_input": 0.02 / 1_000_000, "output": 1.25 / 1_000_000},
    "gpt-5.4-pro": {"input": 30.0 / 1_000_000, "cached_input": None, "output": 180.0 / 1_000_000},
    "gpt-5.3-codex": {"input": 1.75 / 1_000_000, "cached_input": 0.175 / 1_000_000, "output": 14.0 / 1_000_000},
    "gpt-5.2-codex": {"input": 1.75 / 1_000_000, "cached_input": 0.175 / 1_000_000, "output": 14.0 / 1_000_000},
    "gpt-5.1": {"input": 1.25 / 1_000_000, "cached_input": 0.125 / 1_000_000, "output": 10.0 / 1_000_000},
    "gpt-5.1-codex": {"input": 1.25 / 1_000_000, "cached_input": 0.125 / 1_000_000, "output": 10.0 / 1_000_000},
    "gpt-5.1-codex-max": {"input": 1.25 / 1_000_000, "cached_input": 0.125 / 1_000_000, "output": 10.0 / 1_000_000},
    "gpt-5.1-codex-mini": {"input": 0.25 / 1_000_000, "cached_input": 0.025 / 1_000_000, "output": 2.0 / 1_000_000},
    "gpt-5": {"input": 1.25 / 1_000_000, "cached_input": 0.125 / 1_000_000, "output": 10.0 / 1_000_000},
    "gpt-5-mini": {"input": 0.25 / 1_000_000, "cached_input": 0.025 / 1_000_000, "output": 2.0 / 1_000_000},
    "gpt-5-codex": {"input": 1.25 / 1_000_000, "cached_input": 0.125 / 1_000_000, "output": 10.0 / 1_000_000},
    "codex-mini-latest": {"input": 1.50 / 1_000_000, "cached_input": 0.375 / 1_000_000, "output": 6.0 / 1_000_000},
}
MAX_INGESTION_BATCH_BYTES = 3_000_000


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
    retry_backoff_seconds: int
    insecure_tls: bool
    cwd: Path
    override_path: Path | None


@dataclass
class TurnSnapshot:
    turn_id: str | None
    model: str | None
    started_at: str | None
    ended_at: str | None
    input_text: str | None
    output_text: str | None
    raw_usage: dict[str, int] | None
    usage_details: dict[str, Any] | None


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
    retry_backoff_seconds = parse_int(
        merged.get(RETRY_BACKOFF_ENV_VAR),
        default=DEFAULT_RETRY_BACKOFF_SECONDS,
        minimum=5,
        maximum=MAX_RETRY_BACKOFF_SECONDS,
    )
    insecure_tls = parse_bool(merged.get(INSECURE_TLS_ENV_VAR), False)

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
        retry_backoff_seconds=retry_backoff_seconds,
        insecure_tls=insecure_tls,
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


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def stable_identifier(*parts: str, length: int = 32) -> str:
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def canonical_model_name(model: str | None) -> str | None:
    if not model:
        return None

    normalized = model.strip().lower()
    if not normalized:
        return None
    if normalized.startswith("openai/"):
        normalized = normalized.split("/", 1)[1]

    for candidate in sorted(MODEL_PRICING_PER_TOKEN, key=len, reverse=True):
        if normalized == candidate:
            return candidate
        if normalized.startswith(f"{candidate}-"):
            suffix = normalized[len(candidate) :]
            if suffix in {"-latest", "-chat-latest", "-spark"}:
                return candidate
            if re.fullmatch(r"-\d{4}-\d{2}-\d{2}", suffix):
                return candidate
    return None


def normalize_usage_details(raw_usage: Any) -> tuple[dict[str, int], dict[str, Any]] | None:
    if not isinstance(raw_usage, dict):
        return None

    normalized = {
        "input_tokens": int(raw_usage.get("input_tokens") or 0),
        "cached_input_tokens": int(raw_usage.get("cached_input_tokens") or 0),
        "output_tokens": int(raw_usage.get("output_tokens") or 0),
        "reasoning_output_tokens": int(raw_usage.get("reasoning_output_tokens") or 0),
        "total_tokens": int(raw_usage.get("total_tokens") or 0),
    }
    if normalized["total_tokens"] <= 0:
        normalized["total_tokens"] = normalized["input_tokens"] + normalized["output_tokens"]

    usage_details: dict[str, Any] = {
        "prompt_tokens": normalized["input_tokens"],
        "completion_tokens": normalized["output_tokens"],
        "total_tokens": normalized["total_tokens"],
    }
    if normalized["cached_input_tokens"] > 0:
        usage_details["prompt_tokens_details"] = {"cached_tokens": normalized["cached_input_tokens"]}
    if normalized["reasoning_output_tokens"] > 0:
        usage_details["completion_tokens_details"] = {"reasoning_tokens": normalized["reasoning_output_tokens"]}

    return normalized, usage_details


def infer_cost_details(model: str | None, raw_usage: dict[str, int] | None) -> dict[str, float] | None:
    canonical = canonical_model_name(model)
    if canonical is None or raw_usage is None:
        return None

    pricing = MODEL_PRICING_PER_TOKEN.get(canonical)
    if pricing is None:
        return None

    input_tokens = max(0, raw_usage.get("input_tokens", 0))
    cached_input_tokens = max(0, raw_usage.get("cached_input_tokens", 0))
    output_tokens = max(0, raw_usage.get("output_tokens", 0))
    non_cached_input_tokens = max(0, input_tokens - cached_input_tokens)

    input_cost = 0.0
    if non_cached_input_tokens > 0 and pricing.get("input") is not None:
        input_cost += non_cached_input_tokens * float(pricing["input"])
    if cached_input_tokens > 0 and pricing.get("cached_input") is not None:
        input_cost += cached_input_tokens * float(pricing["cached_input"])

    output_cost = 0.0
    if output_tokens > 0 and pricing.get("output") is not None:
        output_cost = output_tokens * float(pricing["output"])

    total_cost = input_cost + output_cost
    if total_cost <= 0:
        return None

    return {
        "input": input_cost,
        "output": output_cost,
        "total": total_cost,
    }


def append_turn(turns: list[TurnSnapshot], turn: TurnSnapshot | None) -> None:
    if turn is None:
        return
    if any([turn.turn_id, turn.model, turn.input_text, turn.output_text, turn.raw_usage, turn.usage_details]):
        turns.append(turn)


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
    current_turn: TurnSnapshot | None = None
    turns: list[TurnSnapshot] = []
    session_model: str | None = None

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

        if entry_type == "turn_context":
            append_turn(turns, current_turn)
            model = payload.get("model") if isinstance(payload.get("model"), str) else None
            if model:
                session_model = model
            current_turn = TurnSnapshot(
                turn_id=str(payload.get("turn_id")) if payload.get("turn_id") else None,
                model=model,
                started_at=timestamp if isinstance(timestamp, str) else None,
                ended_at=timestamp if isinstance(timestamp, str) else None,
                input_text=None,
                output_text=None,
                raw_usage=None,
                usage_details=None,
            )
            continue

        if entry_type == "response_item":
            if current_turn is not None and isinstance(timestamp, str):
                current_turn.ended_at = timestamp
            payload_type = payload.get("type")
            if payload_type == "message":
                role = payload.get("role")
                text = extract_message_text(payload)
                if role == "user":
                    user_messages += 1
                    if text:
                        last_user_prompt = text
                        if current_turn is not None and not current_turn.input_text:
                            current_turn.input_text = text
                elif role == "assistant":
                    assistant_messages += 1
                    if text:
                        last_assistant_message = text
                        if payload.get("phase") == "final":
                            preferred_final_assistant = text
                            if current_turn is not None:
                                current_turn.output_text = text
                        elif current_turn is not None and not current_turn.output_text:
                            current_turn.output_text = text
            elif payload_type == "function_call":
                tool_calls += 1
                name = payload.get("name")
                if isinstance(name, str) and name.strip():
                    tool_names.add(name.strip())
            continue

        if entry_type == "event_msg" and payload.get("type") == "token_count":
            if current_turn is not None and isinstance(timestamp, str):
                current_turn.ended_at = timestamp
            info = payload.get("info")
            if isinstance(info, dict) and current_turn is not None:
                last_usage = normalize_usage_details(info.get("last_token_usage"))
                if last_usage is not None:
                    current_turn.raw_usage, current_turn.usage_details = last_usage
            continue

        if entry_type == "event_msg" and payload.get("type") == "exec_command_end":
            if current_turn is not None and isinstance(timestamp, str):
                current_turn.ended_at = timestamp
            if payload.get("exit_code", 0) not in (0, None):
                failed_tools += 1

    append_turn(turns, current_turn)

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
            "turns": len(turns),
            "raw_parts": 0,
        },
        "model": session_model,
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
        model=session_model,
        started_at=started_at,
        last_event_at=last_event_at,
        summary=summary,
        raw_chunks=raw_chunks,
        tool_names=sorted(tool_names),
        turns=turns,
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


def settings_target_fingerprint(settings: Settings) -> str:
    basis = "|".join(
        [
            settings.base_url or "",
            settings.public_key or "",
            "tls:insecure" if settings.insecure_tls else "tls:strict",
        ]
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def health_path(settings: Settings) -> Path:
    return HEALTH_DIR / f"{settings_target_fingerprint(settings)}.json"


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


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_health_state(settings: Settings) -> HealthState | None:
    payload = load_json_file(health_path(settings))
    if not payload:
        return None

    retry_at_epoch_raw = payload.get("retry_at_epoch")
    try:
        retry_at_epoch = float(retry_at_epoch_raw or 0)
    except (TypeError, ValueError):
        retry_at_epoch = 0.0

    return HealthState(
        consecutive_failures=int(payload.get("consecutive_failures") or 0),
        last_error=str(payload.get("last_error") or "") or None,
        last_failure_at=str(payload.get("last_failure_at") or "") or None,
        retry_at=str(payload.get("retry_at") or "") or None,
        retry_at_epoch=retry_at_epoch,
    )


def save_health_state(settings: Settings, state: HealthState) -> None:
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "consecutive_failures": state.consecutive_failures,
        "last_error": state.last_error,
        "last_failure_at": state.last_failure_at,
        "retry_at": state.retry_at,
        "retry_at_epoch": state.retry_at_epoch,
        "base_url": settings.base_url,
        "public_key": settings.public_key,
        "target_fingerprint": settings_target_fingerprint(settings),
    }
    health_path(settings).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def clear_health_state(settings: Settings) -> None:
    health_path(settings).unlink(missing_ok=True)


def should_defer_exports(settings: Settings) -> HealthState | None:
    state = load_health_state(settings)
    if state is None:
        return None
    if state.retry_at_epoch <= time.time():
        return None
    return state


def mark_server_unhealthy(settings: Settings, error: BaseException | str) -> HealthState:
    now = datetime.now(timezone.utc)
    current = load_health_state(settings)
    failures = (current.consecutive_failures if current is not None else 0) + 1
    retry_at_epoch = time.time() + settings.retry_backoff_seconds
    state = HealthState(
        consecutive_failures=failures,
        last_error=str(error),
        last_failure_at=now.isoformat(),
        retry_at=datetime.fromtimestamp(retry_at_epoch, tz=timezone.utc).isoformat(),
        retry_at_epoch=retry_at_epoch,
    )
    save_health_state(settings, state)
    return state


def extract_status_code(error: BaseException) -> int | None:
    for candidate in (
        getattr(error, "status_code", None),
        getattr(getattr(error, "response", None), "status_code", None),
    ):
        if isinstance(candidate, int):
            return candidate

    match = re.search(r"status_code:\s*(\d{3})", str(error))
    if match:
        return int(match.group(1))
    return None


def is_retryable_export_error(error: BaseException) -> bool:
    if isinstance(
        error,
        (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.NetworkError,
            httpx.ProxyError,
            httpx.ReadTimeout,
            httpx.RemoteProtocolError,
            httpx.TimeoutException,
            httpx.TransportError,
            httpx.WriteTimeout,
        ),
    ):
        return True

    status_code = extract_status_code(error)
    if status_code is not None and (status_code in RETRYABLE_STATUS_CODES or status_code >= 500):
        return True

    message = str(error).lower()
    return any(marker in message for marker in RETRYABLE_ERROR_MARKERS)


def write_spool(snapshot_key: str, settings: Settings, snapshot: Snapshot, error: str) -> None:
    SPOOL_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    existing = load_json_file(spool_path(snapshot_key))
    attempt_count = int(existing.get("attempt_count") or 0) + 1
    payload = {
        "snapshot_key": snapshot_key,
        "session_id": snapshot.session_id,
        "transcript_path": str(snapshot.transcript_path),
        "cwd": str(snapshot.cwd),
        "override_path": str(settings.override_path) if settings.override_path else None,
        "hook_event": snapshot.hook_event,
        "queued_at": existing.get("queued_at") or now,
        "last_attempt_at": now,
        "attempt_count": attempt_count,
        "last_error": error,
        "target_fingerprint": settings_target_fingerprint(settings),
        "base_url": settings.base_url,
    }
    spool_path(snapshot_key).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def serialize_ingestion_event(event: Any) -> str:
    model_dump_json = getattr(event, "model_dump_json", None)
    if callable(model_dump_json):
        return model_dump_json(exclude_none=True)
    json_method = getattr(event, "json", None)
    if callable(json_method):
        try:
            return json_method(exclude_none=True)
        except TypeError:
            return json_method()
    return json.dumps(event, default=str, sort_keys=True)


def build_ingestion_batches(events: list[Any], max_batch_bytes: int = MAX_INGESTION_BATCH_BYTES) -> list[list[Any]]:
    batches: list[list[Any]] = []
    current_batch: list[Any] = []
    current_size = 0

    for event in events:
        event_size = len(serialize_ingestion_event(event).encode("utf-8"))
        if current_batch and current_size + event_size > max_batch_bytes:
            batches.append(current_batch)
            current_batch = []
            current_size = 0

        current_batch.append(event)
        current_size += event_size

    if current_batch:
        batches.append(current_batch)
    return batches


def supports_ingestion_api(client: Langfuse) -> bool:
    if any(
        symbol is None
        for symbol in (
            CreateEventBody,
            CreateGenerationBody,
            IngestionEvent_EventCreate,
            IngestionEvent_GenerationCreate,
            IngestionEvent_TraceCreate,
            TraceBody,
        )
    ):
        return False

    ingestion = getattr(getattr(client, "api", None), "ingestion", None)
    return callable(getattr(ingestion, "batch", None))


def export_snapshot_with_ingestion(client: Langfuse, settings: Settings, snapshot: Snapshot) -> None:
    trace_tags = unique_strings(
        settings.tags
        + [f"tool:{tool_name}" for tool_name in snapshot.tool_names]
        + ([f"cwd:{snapshot.cwd.name}"] if snapshot.cwd.name else [])
        + (["tls:insecure"] if settings.insecure_tls else [])
    )
    trace_timestamp = parse_timestamp(snapshot.started_at) or datetime.now(timezone.utc)
    summary_timestamp = parse_timestamp(snapshot.last_event_at) or trace_timestamp
    trace_metadata = redact_object(
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
            "hostname": socket.gethostname(),
            "transcript_size": snapshot.transcript_size,
            "raw_parts": len(snapshot.raw_chunks),
            "redaction_mode": settings.redaction_mode,
            "hook_event": snapshot.hook_event,
            "model": snapshot.model,
            "stop_hook_active": True,
            "override_path": str(settings.override_path) if settings.override_path else None,
            "insecure_tls": settings.insecure_tls,
        },
        settings.redaction_mode,
    )

    events: list[Any] = [
        IngestionEvent_TraceCreate(
            id=stable_identifier(snapshot.trace_id, "trace-event"),
            timestamp=trace_timestamp.isoformat(),
            body=TraceBody(
                id=snapshot.trace_id,
                timestamp=trace_timestamp,
                name="codex.session",
                session_id=snapshot.session_id,
                user_id=settings.user_id,
                input={
                    "hook_event": snapshot.hook_event,
                    "transcript_sha256": snapshot.transcript_sha256,
                    "transcript_size": snapshot.transcript_size,
                },
                metadata=trace_metadata,
                tags=trace_tags,
                environment="default",
            ),
        )
    ]

    for index, turn in enumerate(snapshot.turns, start=1):
        if not any([turn.input_text, turn.output_text, turn.raw_usage, turn.usage_details]):
            continue

        model = canonical_model_name(turn.model or snapshot.model) or turn.model or snapshot.model
        turn_start = parse_timestamp(turn.started_at) or trace_timestamp
        turn_end = parse_timestamp(turn.ended_at) or turn_start

        generation_kwargs: dict[str, Any] = {
            "id": stable_identifier(snapshot.trace_id, "generation-body", str(index), turn.turn_id or ""),
            "trace_id": snapshot.trace_id,
            "name": "codex.exec.turn",
            "start_time": turn_start,
            "end_time": turn_end,
            "input": redact_object(turn.input_text, settings.redaction_mode),
            "output": redact_object(turn.output_text, settings.redaction_mode),
            "metadata": redact_object(
                {
                    "source": "codex.stop-hook",
                    "turn_id": turn.turn_id,
                    "started_at": turn.started_at,
                    "ended_at": turn.ended_at,
                    "raw_usage": turn.raw_usage,
                },
                settings.redaction_mode,
            ),
            "environment": "default",
        }
        if model:
            generation_kwargs["model"] = model
        if turn.usage_details:
            generation_kwargs["usage"] = {
                "promptTokens": int(turn.usage_details.get("prompt_tokens") or 0),
                "completionTokens": int(turn.usage_details.get("completion_tokens") or 0),
                "totalTokens": int(turn.usage_details.get("total_tokens") or 0),
            }
            generation_kwargs["usage_details"] = turn.usage_details
        cost_details = infer_cost_details(model, turn.raw_usage)
        if cost_details is not None:
            generation_kwargs["cost_details"] = cost_details

        events.append(
            IngestionEvent_GenerationCreate(
                id=stable_identifier(snapshot.trace_id, "generation-event", str(index), turn.turn_id or ""),
                timestamp=turn_end.isoformat(),
                body=CreateGenerationBody(**generation_kwargs),
            )
        )

    events.append(
        IngestionEvent_EventCreate(
            id=stable_identifier(snapshot.trace_id, "summary-event"),
            timestamp=summary_timestamp.isoformat(),
            body=CreateEventBody(
                id=stable_identifier(snapshot.trace_id, "summary-body"),
                trace_id=snapshot.trace_id,
                name="codex.session.summary",
                start_time=summary_timestamp,
                output=snapshot.summary,
                metadata={
                    "content_type": "application/json",
                    "snapshot_sha256": snapshot.transcript_sha256,
                },
                environment="default",
            ),
        )
    )

    total_parts = len(snapshot.raw_chunks)
    for index, chunk in enumerate(snapshot.raw_chunks, start=1):
        events.append(
            IngestionEvent_EventCreate(
                id=stable_identifier(snapshot.trace_id, "raw-part-event", str(index)),
                timestamp=summary_timestamp.isoformat(),
                body=CreateEventBody(
                    id=stable_identifier(snapshot.trace_id, "raw-part-body", str(index)),
                    trace_id=snapshot.trace_id,
                    name=f"codex.raw_transcript.part_{index}",
                    start_time=summary_timestamp,
                    output=chunk,
                    metadata={
                        "part_index": index,
                        "part_total": total_parts,
                        "content_type": "application/x-ndjson",
                        "snapshot_sha256": snapshot.transcript_sha256,
                    },
                    environment="default",
                ),
            )
        )

    for batch in build_ingestion_batches(events):
        response = client.api.ingestion.batch(
            batch=batch,
            metadata={
                "sdk": "codex-stop-hook",
                "snapshot_sha256": snapshot.transcript_sha256,
            },
        )
        if getattr(response, "errors", None):
            raise RuntimeError(f"Langfuse ingestion errors: {response.errors}")


def export_snapshot_with_legacy_tracing(client: Langfuse, settings: Settings, snapshot: Snapshot) -> None:
    trace_tags = unique_strings(
        settings.tags
        + [f"tool:{tool_name}" for tool_name in snapshot.tool_names]
        + ([f"cwd:{snapshot.cwd.name}"] if snapshot.cwd.name else [])
        + (["tls:insecure"] if settings.insecure_tls else [])
    )

    observation_metadata = redact_object(
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
            "model": snapshot.model,
            "turns": len(snapshot.turns),
            "insecure_tls": settings.insecure_tls,
        },
        settings.redaction_mode,
    )
    trace_metadata = redact_object(
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
            "model": snapshot.model,
            "turns": len(snapshot.turns),
        },
        settings.redaction_mode,
    )
    trace_context_manager = contextlib.nullcontext()
    if not hasattr(client, "start_span") and propagate_attributes is not None:
        trace_context_manager = propagate_attributes(
            trace_name="codex.session",
            session_id=snapshot.session_id,
            user_id=settings.user_id,
            metadata=trace_metadata,
            tags=trace_tags,
        )

    with trace_context_manager:
        if hasattr(client, "start_span"):
            span = client.start_span(
                trace_context={"trace_id": snapshot.trace_id},
                name="codex.session.export",
                input={
                    "hook_event": snapshot.hook_event,
                    "transcript_sha256": snapshot.transcript_sha256,
                    "transcript_size": snapshot.transcript_size,
                },
                metadata=observation_metadata,
            )
            span.update_trace(
                name="codex.session",
                session_id=snapshot.session_id,
                user_id=settings.user_id,
                metadata=trace_metadata,
                tags=trace_tags,
            )
        else:
            span = client.start_observation(
                trace_context={"trace_id": snapshot.trace_id},
                name="codex.session.export",
                as_type="span",
                input={
                    "hook_event": snapshot.hook_event,
                    "transcript_sha256": snapshot.transcript_sha256,
                    "transcript_size": snapshot.transcript_size,
                },
                metadata=observation_metadata,
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


def export_snapshot(settings: Settings, snapshot: Snapshot) -> None:
    httpx_client: httpx.Client | None = None
    client_kwargs: dict[str, Any] = {
        "public_key": settings.public_key,
        "secret_key": settings.secret_key,
        "base_url": settings.base_url,
        "timeout": settings.timeout_seconds,
        "flush_at": 1,
        "flush_interval": 0.25,
        "tracing_enabled": True,
    }
    if settings.insecure_tls:
        httpx_client = httpx.Client(verify=False, timeout=settings.timeout_seconds)
        client_kwargs["httpx_client"] = httpx_client

    client: Langfuse | None = None
    try:
        client = Langfuse(**client_kwargs)
        if not client.auth_check():
            raise RuntimeError("Langfuse auth_check returned false")
        if supports_ingestion_api(client):
            export_snapshot_with_ingestion(client, settings, snapshot)
        else:
            export_snapshot_with_legacy_tracing(client, settings, snapshot)
    finally:
        if client is not None:
            with contextlib.suppress(Exception):
                client.shutdown()
        if httpx_client is not None:
            httpx_client.close()


def drain_spool() -> None:
    if not SPOOL_DIR.exists():
        return

    deferred_targets: set[str] = set()
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
        target_fingerprint = settings_target_fingerprint(settings)
        if target_fingerprint in deferred_targets:
            continue

        deferred_state = should_defer_exports(settings)
        if deferred_state is not None:
            deferred_targets.add(target_fingerprint)
            log(
                "spool-deferred "
                f"path={path} retry_at={deferred_state.retry_at} "
                f"failures={deferred_state.consecutive_failures}"
            )
            continue

        try:
            snapshot = build_snapshot(transcript_path, settings, str(payload.get("hook_event") or "Stop"))
            snapshot_key = build_snapshot_key(settings, snapshot)
            if is_exported(snapshot_key):
                path.unlink(missing_ok=True)
                continue
        except Exception as error:  # noqa: BLE001
            log(f"spool-build-failed path={path} error={error}")
            continue

        try:
            export_snapshot(settings, snapshot)
            clear_health_state(settings)
            mark_exported(snapshot_key, settings, snapshot)
            path.unlink(missing_ok=True)
            log(f"spool-exported session_id={snapshot.session_id} snapshot={snapshot_key}")
        except Exception as error:  # noqa: BLE001
            write_spool(snapshot_key, settings, snapshot, str(error))
            if is_retryable_export_error(error):
                state = mark_server_unhealthy(settings, error)
                deferred_targets.add(target_fingerprint)
                log(
                    "spool-buffered "
                    f"path={path} retry_at={state.retry_at} "
                    f"failures={state.consecutive_failures} error={error}"
                )
                continue
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

        deferred_state = should_defer_exports(settings)
        if deferred_state is not None:
            write_spool(snapshot_key, settings, snapshot, f"Deferred until {deferred_state.retry_at}")
            log(
                "snapshot-buffered "
                f"session_id={snapshot.session_id} snapshot={snapshot_key} path={snapshot.transcript_path} "
                f"retry_at={deferred_state.retry_at} failures={deferred_state.consecutive_failures}"
            )
            return 0

        try:
            export_snapshot(settings, snapshot)
            clear_health_state(settings)
            mark_exported(snapshot_key, settings, snapshot)
            spool_path(snapshot_key).unlink(missing_ok=True)
            log(
                "snapshot-exported "
                f"session_id={snapshot.session_id} snapshot={snapshot_key} path={snapshot.transcript_path}"
            )
        except Exception as error:  # noqa: BLE001
            write_spool(snapshot_key, settings, snapshot, str(error))
            if is_retryable_export_error(error):
                state = mark_server_unhealthy(settings, error)
                log(
                    "snapshot-buffered "
                    f"session_id={snapshot.session_id} snapshot={snapshot_key} path={snapshot.transcript_path} "
                    f"retry_at={state.retry_at} failures={state.consecutive_failures} error={error}"
                )
                return 0
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
