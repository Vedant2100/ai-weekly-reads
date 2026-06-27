from __future__ import annotations

import argparse
import sys

from config import load_settings
from pipeline import build_weekly_artifacts, deliver_to_kindle, print_run_summary, update_knowledge_base
from project_paths import ROOT, ensure_dirs
from utils import load_dotenv


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(
        description="Update the knowledge base and build weekly public/local artifacts without distributing them by default."
    )
    parser.add_argument("--send-kindle", action="store_true", help="Send the generated Kindle file after building.")
    parser.add_argument("--force-kindle", action="store_true", help="Resend the generated Kindle file even if it was already sent.")
    args = parser.parse_args()
    ensure_dirs()
    load_dotenv(ROOT / ".env")
    settings = load_settings()
    stats = update_knowledge_base(settings)
    artifacts = build_weekly_artifacts(settings)
    if not artifacts:
        print_run_summary(stats, 0)
        return
    if args.send_kindle:
        print(deliver_to_kindle(artifacts.kindle_path, settings, force=args.force_kindle))
    print_run_summary(stats, artifacts.weekly_resource_count)


if __name__ == "__main__":
    main()
