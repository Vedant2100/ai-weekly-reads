from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from config import load_settings
from project_paths import ROOT
from research_delivery import GMAIL_SEND_SCOPE, GOOGLE_SHEETS_SCOPE
from utils import load_dotenv, write_text


def main() -> None:
    args = _parse_args()
    load_dotenv(ROOT / ".env")
    settings = load_settings()
    email = settings.email
    sheets = settings.google_sheets
    credentials_path = _private_path(
        args.credentials or email.get("gmail_credentials_path") or sheets.get("credentials_path"),
        "config/private/google_credentials.json",
    )
    token_path = _private_path(
        args.token or email.get("gmail_token_path") or sheets.get("token_path"),
        "config/private/google_token.json",
    )
    credentials_path = _resolve_credentials_path(credentials_path, args.credentials)
    if not credentials_path.exists():
        print(f"Missing Google OAuth client file: {credentials_path}")
        print("Download a Desktop app OAuth client JSON from Google Cloud and save it there.")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Missing Google OAuth dependencies. Run: .venv/bin/pip install -r requirements.txt")
        sys.exit(1)

    scopes = [GMAIL_SEND_SCOPE, GOOGLE_SHEETS_SCOPE]
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    write_text(token_path, credentials.to_json(), mode=0o600)
    print(f"Google OAuth token saved: {token_path}")
    print("The token can send the research email and append link rows to Google Sheets.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Authorize Gmail send and Google Sheets access for AI Weekly Reads.")
    parser.add_argument("--credentials", help="path to a downloaded Google OAuth desktop client JSON")
    parser.add_argument("--token", help="path where the local Google OAuth token should be saved")
    return parser.parse_args()


def _private_path(value: object, default: str) -> Path:
    path = Path(str(value or default)).expanduser()
    return path if path.is_absolute() else ROOT / path


def _resolve_credentials_path(configured_path: Path, explicit_path: str | None) -> Path:
    if explicit_path or configured_path.exists():
        return configured_path
    candidates = sorted(ROOT.glob("client_secret_*.json"))
    if len(candidates) != 1:
        return configured_path
    source_path = candidates[0]
    configured_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, configured_path)
    configured_path.chmod(0o600)
    print(f"Copied downloaded OAuth client to {configured_path}")
    return configured_path


if __name__ == "__main__":
    main()
