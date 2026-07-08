from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|password|token|secret|authorization)\s*[:=]\s*([^\s,}]+)"),
    re.compile(r"(?i)(bearer)\s+[a-z0-9._\-]+"),
)

ALLOWED_ATTACHMENT_EXTENSIONS = {".xlsx", ".xls", ".pdf"}
DEFAULT_MAX_ATTACHMENT_MB = 10
REQUIRED_FINAL_KEYS = {
    "status",
    "validation_result",
    "tools_used",
    "agent_metadata",
    "agent_prompts",
    "metrics",
    "completed_at",
}


class GuardrailViolation(ValueError):
    pass


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact_secrets(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if not isinstance(value, str):
        return value

    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}: [REDACTED]", redacted)
    return redacted


def safe_error_message(exc: Exception) -> str:
    return str(redact_secrets(str(exc)))


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise GuardrailViolation(f"Missing required environment variable: {name}")
    return value


def validate_json_array_output(data: str, source_name: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(data)
    except Exception as exc:
        raise GuardrailViolation(f"{source_name} did not return valid JSON: {exc}") from exc

    if not isinstance(parsed, list):
        raise GuardrailViolation(f"{source_name} must return a JSON array")
    if any(not isinstance(row, dict) for row in parsed):
        raise GuardrailViolation(f"{source_name} JSON array must contain only objects")
    return parsed


def validate_final_output(final_output: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_FINAL_KEYS - set(final_output))
    if missing:
        raise GuardrailViolation(f"Final output missing required keys: {', '.join(missing)}")

    metrics = final_output.get("metrics")
    if not isinstance(metrics, dict):
        raise GuardrailViolation("Final output metrics must be a dictionary")

    tools_used = final_output.get("tools_used")
    if not isinstance(tools_used, list):
        raise GuardrailViolation("Final output tools_used must be a list")

    return redact_secrets(final_output)


def validate_api_base_url(url: str, allowed_hosts: set[str] | None = None) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise GuardrailViolation("Frontend API URL must use https")

    configured_hosts = {
        host.strip()
        for host in os.getenv("LEDGERFLOW_ALLOWED_API_HOSTS", "").split(",")
        if host.strip()
    }

    # Also accept the host from FRONTEND_API_URL / LEDGERFLOW_FRONTEND_URL if set,
    # so a single URL env var is enough without duplicating the hostname separately.
    for env_key in ("FRONTEND_API_URL", "LEDGERFLOW_FRONTEND_URL"):
        env_url = os.getenv(env_key, "")
        if env_url:
            env_host = urlparse(env_url).hostname
            if env_host:
                configured_hosts.add(env_host)

    # Also accept the primary LedgerFlow frontend URL directly so the live
    # dashboard does not need to be duplicated in LEDGERFLOW_ALLOWED_API_HOSTS.
    primary_frontend_url = os.getenv("LEDGERFLOW_FRONTEND_BASE_URL", "")
    if primary_frontend_url:
        frontend_host = urlparse(primary_frontend_url).hostname
        if frontend_host:
            configured_hosts.add(frontend_host)

    allowed = allowed_hosts or configured_hosts or {"localhost", "127.0.0.1"}
    if parsed.hostname not in allowed:
        raise GuardrailViolation(f"Frontend API host is not allowed: {parsed.hostname}")

    return url.rstrip("/")


def validate_attachment_path(filepath: str) -> Path:
    path = Path(filepath)
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise GuardrailViolation(f"Unsupported attachment type: {suffix or 'none'}")

    max_mb = int(os.getenv("LEDGERFLOW_MAX_ATTACHMENT_MB", DEFAULT_MAX_ATTACHMENT_MB))
    if path.exists() and path.stat().st_size > max_mb * 1024 * 1024:
        raise GuardrailViolation(f"Attachment exceeds {max_mb} MB limit: {path.name}")

    return path
