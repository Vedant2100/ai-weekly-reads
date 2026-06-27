from __future__ import annotations

import argparse
import sys

from config import load_settings
from pipeline import build_weekly_artifacts, deliver_to_kindle
from project_paths import ROOT, ensure_dirs
from utils import load_dotenv


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Build the latest weekly digest from the local knowledge base.")
    parser.add_argument("--send-kindle", "--send", dest="send_kindle", action="store_true", help="Send the built digest to Kindle after building.")
    parser.add_argument("--force-kindle", action="store_true", help="Resend the built Kindle file even if it was already sent.")
    args = parser.parse_args()

    ensure_dirs()
    load_dotenv(ROOT / ".env")
    settings = load_settings()
    artifacts = build_weekly_artifacts(settings)
    if not artifacts:
        return
    if args.send_kindle:
        print(deliver_to_kindle(artifacts.kindle_path, settings, force=args.force_kindle))


if __name__ == "__main__":
    main()
