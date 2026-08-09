from __future__ import annotations

import base64
import html
import os
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests

from config import Settings
from project_paths import ROOT
from utils import write_text


GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GOOGLE_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def deliver_research_digest_via_apps_script(
    subject: str,
    body: str,
    rows: list[dict[str, Any]],
    settings: Settings,
    html_body: str | None = None,
) -> str:
    """Let the already-authorized Apps Script send mail and append Sheet rows."""
    email_settings = settings.email
    url = str(email_settings.get("apps_script_url") or os.environ.get("RESEARCH_APPS_SCRIPT_URL") or "").strip()
    secret_env = str(email_settings.get("apps_script_secret_env") or "RESEARCH_DIGEST_SECRET")
    secret = os.environ.get(secret_env, "").strip()
    if not url:
        raise RuntimeError("Research delivery is not configured: RESEARCH_APPS_SCRIPT_URL is missing.")
    if not secret:
        raise RuntimeError(f"Research delivery is not configured: {secret_env} is missing.")

    response = requests.post(
        url,
        json={
            "action": "research_digest",
            "secret": secret,
            "subject": subject,
            "body": body,
            "html_body": html_body or _markdown_to_html(body),
            "rows": rows,
        },
        timeout=180,
    )
    response.raise_for_status()
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError("Apps Script returned a non-JSON response.") from exc
    if not result.get("ok"):
        raise RuntimeError(
            f"Apps Script rejected the digest: {result.get('error', 'unknown error')}"
        )
    return f"Sent research digest via Apps Script to {result.get('recipient', 'the configured Google account')}."


def send_research_email(subject: str, body: str, settings: Settings, html_body: str | None = None) -> str:
    email_settings = settings.email
    if not email_settings.get("enabled"):
        return "Research email delivery disabled."

    recipient = str(email_settings.get("recipient_email") or "").strip()
    sender = str(email_settings.get("sender_email") or "").strip()
    if not recipient:
        return "Research email skipped: email.recipient_email is not configured."
    if not sender:
        return "Research email skipped: email.sender_email is not configured."

    method = str(email_settings.get("delivery_method") or "gmail_api").strip().lower()
    if method in {"gmail_api", "gmail", "google"}:
        service = _google_service(email_settings, [GMAIL_SEND_SCOPE])
        message = _build_email(subject, body, sender, recipient, html_body=html_body)
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": encoded}).execute()
    elif method == "smtp":
        message = _build_email(subject, body, sender, recipient, html_body=html_body)
        password_env = str(email_settings.get("smtp_password_env") or "EMAIL_SMTP_PASSWORD")
        password = os.environ.get(password_env) or os.environ.get("EMAIL_SMTP_PASSWORD")
        host = str(email_settings.get("smtp_host") or "smtp.gmail.com")
        port = int(email_settings.get("smtp_port") or 587)
        username = str(email_settings.get("smtp_username") or sender)
        if not password:
            return f"Research email skipped: missing {password_env}."
        with smtplib.SMTP(host, port) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(message)
    else:
        return f"Research email skipped: unsupported delivery method {method!r}."
    return f"Sent research digest email to {recipient}."


def append_link_rows(
    rows: list[dict[str, Any]],
    settings: Settings,
    state: dict[str, Any],
) -> str:
    sheet_settings = settings.google_sheets
    if not sheet_settings.get("enabled"):
        return "Google Sheets indexing disabled."
    if not rows:
        return "Google Sheets: no link rows to append."

    service = _google_service(
        {
            "gmail_credentials_path": sheet_settings.get("credentials_path"),
            "gmail_token_path": sheet_settings.get("token_path"),
        },
        [GOOGLE_SHEETS_SCOPE],
    )
    spreadsheet_id = str(sheet_settings.get("spreadsheet_id") or state.get("spreadsheet_id") or "").strip()
    if not spreadsheet_id:
        spreadsheet = service.spreadsheets().create(
            body={"properties": {"title": str(sheet_settings.get("title") or "AI Research Link Library")}}
        ).execute()
        spreadsheet_id = str(spreadsheet["spreadsheetId"])
        state["spreadsheet_id"] = spreadsheet_id
        state["spreadsheet_url"] = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    worksheet = str(sheet_settings.get("worksheet_name") or "Links")
    range_prefix = _sheet_range(worksheet)
    header = [
        "captured_at",
        "processed_at",
        "type",
        "title",
        "url",
        "source",
        "published",
        "transcript_method",
        "summary_status",
        "digest_date",
    ]
    existing = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{range_prefix}A1:J1",
    ).execute().get("values", [])
    if not existing:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{range_prefix}A1:J1",
            valueInputOption="RAW",
            body={"values": [header]},
        ).execute()

    values = [[
        row.get("captured_at", ""),
        row.get("processed_at", ""),
        row.get("type", ""),
        row.get("title", ""),
        row.get("url", ""),
        row.get("source", ""),
        row.get("published", ""),
        row.get("transcript_method", ""),
        row.get("summary_status", ""),
        row.get("digest_date", ""),
    ] for row in rows]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{range_prefix}A:J",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
    return f"Appended {len(rows)} link rows to Google Sheets: {state.get('spreadsheet_url') or f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit'}"


def classify_link(source_type: str, url: str) -> str:
    lowered = url.lower()
    if source_type == "youtube" or "youtube.com/" in lowered or "youtu.be/" in lowered:
        return "yt"
    if source_type == "pdf_document" or lowered.split("?", 1)[0].endswith(".pdf") or "arxiv.org/pdf/" in lowered:
        return "pdf"
    if source_type == "podcast" or "spotify.com/" in lowered:
        return "podcast"
    if source_type == "x_post" or "twitter.com/" in lowered or "x.com/" in lowered:
        return "x"
    return "link"


def _build_email(subject: str, body: str, sender: str, recipient: str, html_body: str | None = None) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)
    message.add_alternative(html_body or _markdown_to_html(body), subtype="html")
    return message


def _markdown_to_html(markdown: str) -> str:
    lines: list[str] = []
    for raw_line in markdown.splitlines():
        # Do not escape html yet since we need to match markdown image tags which might contain unescaped characters, 
        # though the original code escaped it first. Wait, if we escape first, the `&` in URLs becomes `&amp;`.
        # Let's keep the original flow but update the regex for images and avoid empty lines.
        line = html.escape(raw_line)
        if line.startswith("### "):
            lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("- "):
            lines.append(f"<li>{line[2:]}</li>")
        elif not line.strip():
            continue
        else:
            line = re.sub(r"!\[([^]]*)\]\((https?://[^)]+)\)", r'<img src="\2" alt="\1" style="max-width:100%; height:auto;">', line)
            line = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', line)
            lines.append(f"<p>{line}</p>")
    return "<html><body style='font-family:Arial,sans-serif;line-height:1.5;max-width:900px'>" + "\n".join(lines) + "</body></html>"


def _sheet_range(worksheet: str) -> str:
    escaped = worksheet.replace("'", "''")
    return f"'{escaped}'!"


def _google_service(settings: dict[str, Any], scopes: list[str]):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError("Install Google API dependencies with pip install -r requirements.txt.") from exc

    credentials_path = _private_path(settings.get("gmail_credentials_path") or settings.get("credentials_path"), "config/private/google_credentials.json")
    token_path = _private_path(settings.get("gmail_token_path") or settings.get("token_path"), "config/private/google_token.json")
    if not credentials_path.exists():
        raise FileNotFoundError(f"{credentials_path} is missing. Run scripts/setup_google_oauth.py first.")
    if not token_path.exists():
        raise FileNotFoundError(f"{token_path} is missing. Run scripts/setup_google_oauth.py first.")

    credentials = Credentials.from_authorized_user_file(str(token_path), scopes)
    granted = set(credentials.scopes or [])
    missing = [scope for scope in scopes if scope not in granted]
    if missing:
        raise RuntimeError("Google OAuth token lacks required scopes. Run scripts/setup_google_oauth.py again.")
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        write_text(token_path, credentials.to_json(), mode=0o600)
    if not credentials.valid:
        raise RuntimeError("Google OAuth token is invalid. Run scripts/setup_google_oauth.py again.")
    api = "gmail" if GMAIL_SEND_SCOPE in scopes else "sheets"
    version = "v1" if api == "gmail" else "v4"
    return build(api, version, credentials=credentials)


def _private_path(value: object, default: str) -> Path:
    path = Path(str(value or default)).expanduser()
    return path if path.is_absolute() else ROOT / path
