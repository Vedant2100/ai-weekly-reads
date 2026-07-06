from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from process_inbox_batch import process_inbox_batch
from project_paths import INBOX


def add_links_to_inbox(links: list[str], inbox_path: Path = INBOX / "links.txt", run_now: bool = False) -> bool:
    if not inbox_path.exists():
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        inbox_path.write_text("# Add links here (one per line). Run python3 scripts/process_inbox_batch.py to process.\n", encoding="utf-8")

    added = []
    with open(inbox_path, "a", encoding="utf-8") as f:
        for link in links:
            clean = link.strip()
            if clean:
                f.write(f"{clean}\n")
                added.append(clean)

    print(f"✅ Added {len(added)} link(s) to {inbox_path}:")
    for a in added:
        print(f"  - {a}")

    if run_now:
        print("\n⚡ --run specified: Starting batch processor now...")
        return process_inbox_batch(inbox_path)
    else:
        print("\n💡 Run `python3 scripts/process_inbox_batch.py` or start `python3 scripts/watch_inbox.py` to generate your ebook!")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add links to the shared inbox box.")
    parser.add_argument("links", nargs="+", help="One or more URLs to add to inbox")
    parser.add_argument("--inbox", type=Path, default=INBOX / "links.txt", help="Path to inbox file")
    parser.add_argument("-r", "--run", action="store_true", help="Process inbox immediately after adding")
    args = parser.parse_args()
    success = add_links_to_inbox(args.links, args.inbox, args.run)
    sys.exit(0 if success else 1)
