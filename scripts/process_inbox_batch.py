from __future__ import annotations

import argparse
from pathlib import Path

from project_paths import INBOX
from research_digest import run_research_digest


def process_inbox_batch(inbox_path: Path = INBOX / "links.txt") -> bool:
    """Compatibility entry point for the old command.

    Link processing is now a research email digest. The old Kindle/ebook path
    is intentionally no longer called from this command.
    """
    if inbox_path != INBOX / "links.txt":
        raise ValueError("The research digest uses the canonical inbox/links.txt queue.")
    return run_research_digest(force=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send queued research links as an email digest.")
    parser.add_argument("--inbox", type=Path, default=INBOX / "links.txt", help="Canonical research inbox path")
    args = parser.parse_args()
    raise SystemExit(0 if process_inbox_batch(args.inbox) else 1)
