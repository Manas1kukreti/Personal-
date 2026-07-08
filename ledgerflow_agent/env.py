from __future__ import annotations

import os
from typing import Iterable
from urllib.parse import urlparse, urlunparse

from ledgerflow_agent.guardrails import GuardrailViolation


def _first_env(names: Iterable[str]) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def require_env_alias(*names: str) -> str:
    value = _first_env(names)
    if value is None:
        raise GuardrailViolation(f"Missing required environment variable: {' or '.join(names)}")
    return value


def get_mail_credentials() -> tuple[str, str]:
    email = require_env_alias("LEDGERFLOW_MAIL_USERNAME", "EMAIL_USER")
    password = require_env_alias("LEDGERFLOW_MAIL_PASSWORD", "EMAIL_PASS")
    return email, password


def get_imap_settings() -> tuple[str, int]:
    host = require_env_alias("LEDGERFLOW_IMAP_HOST")
    port = int(require_env_alias("LEDGERFLOW_IMAP_PORT"))
    return host, port


def get_frontend_base_url() -> str:
    raw_url = require_env_alias("LEDGERFLOW_FRONTEND_BASE_URL", "FRONTEND_API_URL", "LEDGERFLOW_FRONTEND_URL")
    parsed = urlparse(raw_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/login"):
        path = path[: -len("/login")]
    normalized = parsed._replace(path=path or "", params="", query="", fragment="")
    return urlunparse(normalized).rstrip("/")


def get_frontend_credentials() -> tuple[str, str]:
    email = require_env_alias("LEDGERFLOW_FRONTEND_EMAIL", "LEDGERFLOW_AGENT_EMAIL")
    password = require_env_alias("LEDGERFLOW_FRONTEND_PASSWORD", "LEDGERFLOW_AGENT_PASSWORD")
    return email, password


def get_manager_email() -> str:
    return require_env_alias("LEDGERFLOW_MANAGER_EMAIL")


def get_smtp_settings() -> tuple[str, int]:
    host = require_env_alias("LEDGERFLOW_SMTP_HOST")
    port = int(require_env_alias("LEDGERFLOW_SMTP_PORT"))
    return host, port
