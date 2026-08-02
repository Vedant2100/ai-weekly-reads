from __future__ import annotations

import base64
import os
import mimetypes
import smtplib
import subprocess
from email.message import EmailMessage
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from config import Settings
from project_paths import METADATA, ROOT
from utils import read_json, write_json, write_text

PLACEHOLDER_EMAILS = {"yourname_123@kindle.com", "you@example.com"}
DELIVERY_LEDGER = METADATA / "kindle_delivery.json"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def maybe_send_to_kindle(file_path: Path, settings: Settings, force: bool = False) -> str:
    kindle = settings.kindle
    user_email = os.environ.get("USER_EMAIL") or os.environ.get("GMAIL_RECIPIENT")
    kindle_enabled = kindle.get("enabled") or os.environ.get("KINDLE_ENABLED") == "true" or user_email

    if not kindle_enabled:
        return "Email delivery skipped: Email delivery disabled."

    recipient = _configured_email(kindle, "kindle_email") or os.environ.get("KINDLE_EMAIL", "").strip()
    if not recipient and not user_email:
        return "Email delivery skipped: No recipient (kindle_email or USER_EMAIL) configured."

    delivery_key, file_hash = _delivery_key(file_path, recipient or user_email)
    if not force and _already_sent(delivery_key):
        return f"Email delivery skipped: {file_path.name} was already sent. Use --force to resend."

    delivery_method = str(kindle.get("delivery_method") or os.environ.get("KINDLE_DELIVERY_METHOD", "smtp")).strip().lower()
    if delivery_method in {"apple_mail", "mail", "macos_mail"}:
        message = _send_with_apple_mail(file_path, kindle, recipient)
        _record_delivery_if_sent(message, delivery_key, file_hash, file_path, delivery_method, recipient)
        return message

    if delivery_method in {"gmail_api", "gmail", "google"}:
        message = _send_with_gmail_api(file_path, kindle, recipient)
        _record_delivery_if_sent(message, delivery_key, file_hash, file_path, delivery_method, recipient)
        return message

    message = _send_with_smtp(file_path, kindle, recipient)
    _record_delivery_if_sent(message, delivery_key, file_hash, file_path, delivery_method, recipient or user_email)
    return message


def _send_with_smtp(file_path: Path, kindle: dict, recipient: str) -> str:
    sender = _configured_email(kindle, "sender_email") or os.environ.get("KINDLE_SENDER_EMAIL", "").strip()
    password_env = kindle.get("smtp_password_env", "KINDLE_SMTP_PASSWORD")
    password = os.environ.get(password_env) or os.environ.get("KINDLE_SMTP_PASSWORD")
    smtp_host = kindle.get("smtp_host") or os.environ.get("KINDLE_SMTP_HOST") or "smtp.gmail.com"
    smtp_port = int(kindle.get("smtp_port") or os.environ.get("KINDLE_SMTP_PORT") or 587)
    smtp_username = kindle.get("smtp_username") or os.environ.get("KINDLE_SMTP_USERNAME") or sender

    missing = []
    if not sender:
        missing.append("KINDLE_SENDER_EMAIL")
    if not password:
        missing.append("KINDLE_SMTP_PASSWORD")
    if missing:
        return f"Email delivery skipped: missing {', '.join(missing)}."

    recipients = [r.strip() for r in recipient.split(",") if r.strip()]
    user_email = os.environ.get("USER_EMAIL") or os.environ.get("GMAIL_RECIPIENT")

    sent_to = []
    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_username, password)

        # Send Kindle attachment email (if Kindle recipient configured)
        for target in recipients:
            message = _build_message(file_path, sender, target, is_text_only=False)
            smtp.send_message(message)
            sent_to.append(f"{target} (Kindle attachment)")

        # Send personal Gmail inline article text email (if USER_EMAIL configured)
        if user_email and user_email.strip() not in recipients:
            target_user = user_email.strip()
            message = _build_message(file_path, sender, target_user, is_text_only=True)
            smtp.send_message(message)
            sent_to.append(f"{target_user} (Gmail text in body)")

    return f"Sent {file_path.name} to {', '.join(sent_to)}."


def _send_with_gmail_api(file_path: Path, kindle: dict, recipient: str) -> str:
    sender = _configured_email(kindle, "sender_email")
    if not sender:
        return "Kindle delivery skipped: missing KINDLE_SENDER_EMAIL."

    try:
        service = _gmail_service(kindle)
    except ImportError:
        return "Kindle delivery skipped: install Gmail API dependencies with .venv/bin/pip install -r requirements.txt."
    except FileNotFoundError as exc:
        return f"Kindle delivery skipped: {exc}"
    except Exception as exc:
        return f"Kindle delivery skipped: Gmail OAuth failed. {exc}"

    message = _build_message(file_path, sender, recipient, is_text_only=False)
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": encoded_message}).execute()
    return f"Sent {file_path.name} to {recipient} with Gmail API."


def _build_message(file_path: Path, sender: str, recipient: str, is_text_only: bool = False) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = file_path.stem
    message["From"] = sender
    message["To"] = recipient

    if is_text_only:
        md_path = file_path.with_suffix(".md")
        if md_path.exists():
            body_text = md_path.read_text(encoding="utf-8")
        else:
            body_text = "Weekly Digest Content"

        message.set_content(body_text)
        html_body = _markdown_to_html(body_text)
        message.add_alternative(html_body, subtype="html")
    else:
        message.set_content("Attached is your weekly media digest.")
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        maintype, subtype = content_type.split("/", 1)
        message.add_attachment(
            file_path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=file_path.name,
        )
    return message


def _markdown_to_html(md_text: str) -> str:
    import re
    html = md_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = re.sub(r"^# (.*?)$", r'<h1 style="color:#111827;font-family:sans-serif;">\1</h1>', html, flags=re.M)
    html = re.sub(r"^## (.*?)$", r'<h2 style="color:#1f2937;font-family:sans-serif;margin-top:20px;">\1</h2>', html, flags=re.M)
    html = re.sub(r"^### (.*?)$", r'<h3 style="color:#374151;font-family:sans-serif;">\1</h3>', html, flags=re.M)
    html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\[(.*?)\]\((https?://.*?)\)", r'<a href="\2" style="color:#2563eb;">\1</a>', html)
    html = re.sub(r"^> (.*?)$", r'<blockquote style="border-left:4px solid #cbd5e1;padding-left:12px;color:#475569;">\1</blockquote>', html, flags=re.M)
    html = re.sub(r"^- (.*?)$", r'<li style="margin-bottom:4px;">\1</li>', html, flags=re.M)
    paragraphs = html.split("\n\n")
    formatted = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith("<h") or p.startswith("<blockquote") or p.startswith("<li"):
            formatted.append(p)
        else:
            formatted.append(f'<p style="font-family:sans-serif;font-size:15px;line-height:1.6;color:#334155;">{p.replace(chr(10), "<br>")}</p>')
    return "\n".join(formatted)


def _gmail_service(kindle: dict):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        raise

    token_path = private_path(kindle.get("gmail_token_path"), "config/private/gmail_token.json")
    credentials_path = private_path(
        kindle.get("gmail_credentials_path"),
        "config/private/gmail_credentials.json",
    )
    if not credentials_path.exists():
        raise FileNotFoundError(f"{credentials_path} is missing. Run scripts/setup_gmail_oauth.py after downloading OAuth credentials.")
    if not token_path.exists():
        raise FileNotFoundError(f"{token_path} is missing. Run scripts/setup_gmail_oauth.py first.")

    creds = Credentials.from_authorized_user_file(str(token_path), [GMAIL_SEND_SCOPE])
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        write_private_file(token_path, creds.to_json())
    if not creds or not creds.valid:
        raise RuntimeError("Gmail token is invalid. Run scripts/setup_gmail_oauth.py again.")
    return build("gmail", "v1", credentials=creds)


def private_path(value: object, default: str) -> Path:
    path = Path(str(value or default)).expanduser()
    if path.is_absolute():
        return path
    return ROOT / path


def write_private_file(path: Path, content: str) -> None:
    # OAuth tokens grant live send access; keep them out of reach of other
    # local users, and never leave a truncated token behind.
    write_text(path, content, mode=0o600)


def _send_with_apple_mail(file_path: Path, kindle: dict, recipient: str) -> str:
    account_count, account_error = _apple_mail_account_count()
    if account_count < 1:
        details = f" {account_error}" if account_error else ""
        return f"Kindle delivery skipped: Apple Mail has no configured mail accounts.{details}"

    sender = _configured_email(kindle, "sender_email")
    subject = kindle.get("subject") or file_path.stem
    body = kindle.get("body") or "Attached is your weekly media digest."
    script = """
on run argv
  set attachmentPath to POSIX file (item 1 of argv)
  set recipientAddress to item 2 of argv
  set subjectLine to item 3 of argv
  set bodyText to item 4 of argv
  set senderAddress to item 5 of argv

  tell application "Mail"
    set newMessage to make new outgoing message with properties {subject:subjectLine, content:bodyText & return & return, visible:false}
    tell newMessage
      make new to recipient at end of to recipients with properties {address:recipientAddress}
      if senderAddress is not "" then set sender to senderAddress
      tell content
        make new attachment with properties {file name:attachmentPath} at after last paragraph
      end tell
      send
    end tell
  end tell
end run
"""
    result = subprocess.run(
        ["osascript", "-e", script, str(file_path), recipient, str(subject), str(body), sender],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        return f"Kindle delivery skipped: Apple Mail send failed. {details}"
    return f"Sent {file_path.name} to {recipient} with Apple Mail."


def _apple_mail_account_count() -> tuple[int, str]:
    result = subprocess.run(
        ["osascript", "-e", 'tell application "Mail" to return count of accounts'],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return 0, (result.stderr or result.stdout).strip()
    try:
        return int(result.stdout.strip()), ""
    except ValueError:
        return 0, f"Could not read Mail account count: {result.stdout.strip()}"


def _configured_email(kindle: dict, key: str) -> str:
    value = str(kindle.get(key) or "").strip()
    if value in PLACEHOLDER_EMAILS:
        return ""
    return value


def _delivery_key(file_path: Path, recipient: str) -> tuple[str, str]:
    file_hash = _file_sha256(file_path)
    recipient_hash = sha256(recipient.strip().lower().encode("utf-8")).hexdigest()
    key = sha256(f"{recipient_hash}\0{file_hash}".encode("utf-8")).hexdigest()
    return key, file_hash


def _file_sha256(file_path: Path) -> str:
    digest = sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _already_sent(delivery_key: str) -> bool:
    ledger = read_json(DELIVERY_LEDGER, {"sent": []})
    sent = ledger.get("sent", []) if isinstance(ledger, dict) else []
    return any(isinstance(row, dict) and row.get("key") == delivery_key for row in sent)


def _record_delivery_if_sent(
    message: str,
    delivery_key: str,
    file_hash: str,
    file_path: Path,
    delivery_method: str,
    recipient: str,
) -> None:
    if not message.startswith("Sent "):
        return

    ledger = read_json(DELIVERY_LEDGER, {"sent": []})
    if not isinstance(ledger, dict):
        ledger = {"sent": []}
    sent = ledger.setdefault("sent", [])
    if not isinstance(sent, list):
        ledger["sent"] = sent = []
    if any(isinstance(row, dict) and row.get("key") == delivery_key for row in sent):
        return

    sent.append(
        {
            "key": delivery_key,
            "file": file_path.name,
            "sha256": file_hash,
            "recipient_hash": sha256(recipient.strip().lower().encode("utf-8")).hexdigest(),
            "delivery_method": delivery_method,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    write_json(DELIVERY_LEDGER, ledger)
