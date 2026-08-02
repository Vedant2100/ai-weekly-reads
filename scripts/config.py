from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_paths import CONFIG
from utils import read_json


@dataclass(frozen=True)
class Settings:
    digest_title: str
    timezone: str
    summary_provider: str
    summary_model: str
    summary_fallback_model: str
    summary_mode: str
    transcription_provider: str
    transcription_model: str
    include_full_transcripts: bool
    kindle_output_format: str
    weekly_resource_limit: int
    publication_window_days: int
    max_items_per_run: int
    youtube_channels: list[dict[str, Any]]
    follow_builders: dict[str, Any]
    kindle: dict[str, Any]
    substack: dict[str, Any]
    email: dict[str, Any]
    google_sheets: dict[str, Any]
    feeds: list[str]


def load_settings(path: Path | None = None) -> Settings:
    explicit = path is not None
    path = path or CONFIG / "settings.json"
    fallback = CONFIG / "settings.example.json"
    if explicit and not path.exists():
        raise FileNotFoundError(f"Settings file not found: {path}")
    raw = read_json(path if path.exists() else fallback, {})
    return Settings(
        digest_title=raw.get("digest_title", "AI Weekly Reads"),
        timezone=raw.get("timezone", "America/Chicago"),
        summary_provider=raw.get("summary_provider", "gemini"),
        summary_model=raw.get("summary_model", "gemini-2.5-pro"),
        summary_fallback_model=raw.get("summary_fallback_model", "gemini-2.5-flash"),
        summary_mode=raw.get("summary_mode", "direct"),
        transcription_provider=raw.get("transcription_provider", "gemini"),
        transcription_model=raw.get("transcription_model", "gemini-2.5-pro"),
        include_full_transcripts=raw.get("include_full_transcripts", False),
        kindle_output_format=raw.get("kindle_output_format", "epub"),
        weekly_resource_limit=int(raw.get("weekly_resource_limit", 25)),
        publication_window_days=int(raw.get("publication_window_days", 7)),
        max_items_per_run=int(raw.get("max_items_per_run", 0)),
        youtube_channels=list(raw.get("youtube_channels", [])),
        follow_builders=_follow_builders_settings(raw.get("follow_builders", {})),
        kindle=_kindle_settings(raw.get("kindle", {})),
        substack=_substack_settings(raw.get("substack", {})),
        email=_email_settings(raw.get("email", {})),
        google_sheets=_google_sheets_settings(raw.get("google_sheets", {})),
        feeds=list(raw.get("feeds", [])),
    )


def _follow_builders_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    defaults = {
        "enabled": False,
        "base_url": "",
        "include_podcasts": False,
    }
    return {**defaults, **dict(raw or {})}


def _kindle_settings(raw: dict[str, Any]) -> dict[str, Any]:
    kindle = dict(raw)
    _set_env_value(kindle, "enabled", "KINDLE_ENABLED", transform=_as_bool)
    _set_env_value(kindle, "delivery_method", "KINDLE_DELIVERY_METHOD")
    _set_env_value(kindle, "kindle_email", "KINDLE_EMAIL")
    _set_env_value(kindle, "sender_email", "KINDLE_SENDER_EMAIL")
    _set_env_value(kindle, "smtp_host", "KINDLE_SMTP_HOST")
    _set_env_value(kindle, "smtp_port", "KINDLE_SMTP_PORT", transform=int)
    _set_env_value(kindle, "smtp_username", "KINDLE_SMTP_USERNAME")
    _set_env_value(kindle, "smtp_password_env", "KINDLE_SMTP_PASSWORD_ENV")
    _set_env_value(kindle, "gmail_credentials_path", "GMAIL_CREDENTIALS_PATH")
    _set_env_value(kindle, "gmail_token_path", "GMAIL_TOKEN_PATH")
    return kindle


def _substack_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    substack = {
        "enabled": False,
        "publication_url": "",
        "delivery_method": "browser_draft",
        "auto_publish": False,
        "intro": "",
        "browser_user_data_dir": "config/private/substack/browser",
        "compose_url": "",
        **dict(raw or {}),
    }
    _set_env_value(substack, "enabled", "SUBSTACK_ENABLED", transform=_as_bool)
    _set_env_value(substack, "publication_url", "SUBSTACK_PUBLICATION_URL")
    _set_env_value(substack, "delivery_method", "SUBSTACK_DELIVERY_METHOD")
    _set_env_value(substack, "auto_publish", "SUBSTACK_AUTO_PUBLISH", transform=_as_bool)
    _set_env_value(substack, "intro", "SUBSTACK_INTRO")
    _set_env_value(substack, "browser_user_data_dir", "SUBSTACK_BROWSER_USER_DATA_DIR")
    _set_env_value(substack, "compose_url", "SUBSTACK_COMPOSE_URL")
    return substack


def _email_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    email = {
        "enabled": False,
        "delivery_method": "apps_script",
        "recipient_email": "",
        "sender_email": "",
        "subject_prefix": "AI Research Reorientation",
        "apps_script_url": "",
        "apps_script_secret_env": "RESEARCH_DIGEST_SECRET",
        "gmail_credentials_path": "config/private/google_credentials.json",
        "gmail_token_path": "config/private/google_token.json",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_password_env": "EMAIL_SMTP_PASSWORD",
        **dict(raw or {}),
    }
    _set_env_value(email, "enabled", "EMAIL_ENABLED", transform=_as_bool)
    _set_env_value(email, "delivery_method", "EMAIL_DELIVERY_METHOD")
    _set_env_value(email, "recipient_email", "EMAIL_RECIPIENT")
    _set_env_value(email, "recipient_email", "RESEARCH_EMAIL_TO")
    _set_env_value(email, "sender_email", "EMAIL_SENDER")
    _set_env_value(email, "sender_email", "RESEARCH_EMAIL_FROM")
    _set_env_value(email, "subject_prefix", "EMAIL_SUBJECT_PREFIX")
    _set_env_value(email, "apps_script_url", "RESEARCH_APPS_SCRIPT_URL")
    _set_env_value(email, "apps_script_secret_env", "RESEARCH_DIGEST_SECRET_ENV")
    _set_env_value(email, "gmail_credentials_path", "GOOGLE_CREDENTIALS_PATH")
    _set_env_value(email, "gmail_token_path", "GOOGLE_TOKEN_PATH")
    _set_env_value(email, "smtp_host", "EMAIL_SMTP_HOST")
    _set_env_value(email, "smtp_port", "EMAIL_SMTP_PORT", transform=int)
    _set_env_value(email, "smtp_username", "EMAIL_SMTP_USERNAME")
    _set_env_value(email, "smtp_password_env", "EMAIL_SMTP_PASSWORD_ENV")
    return email


def _google_sheets_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    sheets = {
        "enabled": False,
        "spreadsheet_id": "",
        "worksheet_name": "Links",
        "title": "AI Research Link Library",
        "share_with_email": "",
        "credentials_path": "config/private/google_credentials.json",
        "token_path": "config/private/google_token.json",
        **dict(raw or {}),
    }
    _set_env_value(sheets, "enabled", "GOOGLE_SHEETS_ENABLED", transform=_as_bool)
    _set_env_value(sheets, "spreadsheet_id", "GOOGLE_SHEETS_SPREADSHEET_ID")
    _set_env_value(sheets, "worksheet_name", "GOOGLE_SHEETS_WORKSHEET")
    _set_env_value(sheets, "title", "GOOGLE_SHEETS_TITLE")
    _set_env_value(sheets, "share_with_email", "GOOGLE_SHEETS_SHARE_WITH")
    _set_env_value(sheets, "credentials_path", "GOOGLE_CREDENTIALS_PATH")
    _set_env_value(sheets, "token_path", "GOOGLE_TOKEN_PATH")
    return sheets


def _set_env_value(kindle: dict[str, Any], key: str, env_name: str, transform=None) -> None:
    value = os.environ.get(env_name)
    if value is None or value == "":
        return
    if transform:
        try:
            value = transform(value)
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"Invalid value for {env_name}: {value!r}") from exc
    kindle[key] = value


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}
